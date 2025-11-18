# backend/app.py
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import dotenv

dotenv.load_dotenv()

app = FastAPI(title="Movie Scene Search API 🎬")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_conn():
    return psycopg2.connect(os.getenv("DATABASE_URL", "postgresql://msuser:mssecret@postgres/moviesearch"))

# Actors (keeps previous working query)
@app.get("/actors")
def get_actors():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT actor_id, name AS actor_name FROM actors ORDER BY name;")
    data = cur.fetchall()
    conn.close()
    return data

# Scenes endpoint (actor filter)
@app.get("/scenes")
def get_scenes(actor_id: int = None):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    if actor_id:
        cur.execute("""
            SELECT s.scene_id, s.movie_name, s.start_time, s.end_time,
                   array_agg(a.name) AS actors
            FROM scenes s
            JOIN scene_actor_presence sap ON s.scene_id = sap.scene_id
            JOIN actors a ON a.actor_id = sap.actor_id
            WHERE a.actor_id = %s
            GROUP BY s.scene_id;
        """, (actor_id,))
    else:
        cur.execute("""
            SELECT s.scene_id, s.movie_name, s.start_time, s.end_time,
                   array_agg(a.name) AS actors
            FROM scenes s
            LEFT JOIN scene_actor_presence sap ON s.scene_id = sap.scene_id
            LEFT JOIN actors a ON a.actor_id = sap.actor_id
            GROUP BY s.scene_id;
        """)
    data = cur.fetchall()
    conn.close()
    return data

# Scene attributes
@app.get("/scene_attributes/{scene_id}")
def get_scene_attributes(scene_id: int):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT objects, caption, tags, updated_at FROM scene_attributes WHERE scene_id = %s;", (scene_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return row
    return {"error": "Not found"}

# Simple tag search
@app.get("/search_by_tag")
def search_by_tag(tag: str = Query(..., min_length=1)):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT s.scene_id, s.movie_name, s.start_time, s.end_time, sa.objects, sa.caption, sa.tags
        FROM scenes s
        JOIN scene_attributes sa ON s.scene_id = sa.scene_id
        WHERE %s = ANY(sa.tags)
        ORDER BY s.scene_id LIMIT 200;
    """, (tag,))
    rows = cur.fetchall()
    conn.close()
    return rows

# frame file endpoint (unchanged)
@app.get("/frame/{scene_id}")
def get_frame(scene_id: int):
    frame_path = f"/data/frames/scene_{scene_id}.jpg"
    if os.path.exists(frame_path):
        return FileResponse(frame_path)
    return {"error": "Frame not found"}

@app.get("/")
def root():
    return {"message": "🎬 Movie Scene Search API is running!"}


# ---------------------------
# SEMANTIC SEARCH + OBJECT SEARCH
# ---------------------------
from fastapi import Query
import numpy as np
import pickle

FAISS_DIR = "/data/faiss"
LOCAL_MODEL_PATH = "/models/sentence-transformers/all-MiniLM-L6-v2"

# Load sentence transformer model
try:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(LOCAL_MODEL_PATH)
    print("🔍 Loaded local SentenceTransformer model:", LOCAL_MODEL_PATH)
except Exception as e:
    print("⚠️ Failed to load semantic model:", e)
    model = None

# Load FAISS index + metadata
try:
    import faiss
    scene_index = faiss.read_index(f"{FAISS_DIR}/scene_index.faiss")
    with open(f"{FAISS_DIR}/scene_meta.pkl", "rb") as f:
        scene_meta = pickle.load(f)
    print("📁 FAISS scene index loaded.")
except Exception as e:
    print("⚠️ Failed loading scene FAISS index:", e)
    scene_index = None
    scene_meta = []


def embed_text(q: str):
    if model is None:
        raise RuntimeError("Semantic model not loaded.")
    v = model.encode([q], normalize_embeddings=True)
    return v.astype(np.float32)


@app.get("/search")
def search(
    q: str = Query(None),
    actor_id: int = Query(None),
    object: str = Query(None),
    top_k: int = 10
):
    if not q and not actor_id and not object:
        return {"results": []}

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Semantic FAISS search
    scene_candidates = None
    if q and scene_index is not None:
        try:
            vec = embed_text(q)
            D, I = scene_index.search(vec, 50)
            idxs = I[0].tolist()
            scene_candidates = [scene_meta[i] for i in idxs if i < len(scene_meta)]
        except Exception as e:
            print("Semantic search error:", e)

    # Build SQL filters
    clauses = []
    params = []

    if actor_id:
        clauses.append("EXISTS (SELECT 1 FROM scene_actor_presence sap WHERE sap.scene_id = s.scene_id AND sap.actor_id = %s)")
        params.append(actor_id)

    if object:
        clauses.append("%s = ANY(COALESCE(sa.objects, '{}'))")
        params.append(object)

    if scene_candidates:
        clauses.append("s.scene_id = ANY(%s)")
        params.append(scene_candidates)

    sql = """
        SELECT s.scene_id, s.movie_name, s.start_time, s.end_time, s.thumbnail_path,
               sa.objects, sa.tags,
               array_remove(array_agg(DISTINCT a.name), NULL) AS actors
        FROM scenes s
        LEFT JOIN scene_attributes sa ON sa.scene_id = s.scene_id
        LEFT JOIN scene_actor_presence sap ON sap.scene_id = s.scene_id
        LEFT JOIN actors a ON a.actor_id = sap.actor_id
    """

    if clauses:
        sql += " WHERE " + " AND ".join(clauses)

    sql += """
        GROUP BY s.scene_id, sa.objects, sa.tags
        ORDER BY s.start_time
        LIMIT 100;
    """

    try:
        cur.execute(sql, params)
        rows = cur.fetchall()
    except Exception as e:
        print("SQL error in /search:", e)
        conn.close()
        return {"detail": "Error fetching scenes"}

    conn.close()

    # reorder according to FAISS ranking
    if scene_candidates:
        order = {sid: i for i, sid in enumerate(scene_candidates)}
        rows.sort(key=lambda r: order.get(r["scene_id"], 999999))

    for r in rows:
        r["objects"] = r["objects"] or []
        r["tags"] = r["tags"] or []
        r["actors"] = r["actors"] or []

    return {"query": q, "results": rows[:top_k]}
