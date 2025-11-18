import psycopg2
import os
import numpy as np
import faiss
import pickle

DB_URL = os.getenv("DATABASE_URL", "postgresql://msuser:mssecret@postgres/moviesearch")
FAISS_DIR = "/data/faiss"

os.makedirs(FAISS_DIR, exist_ok=True)

def get_conn():
    return psycopg2.connect(DB_URL)

def build_scene_faiss():
    conn = get_conn()
    cur = conn.cursor()

    print("📥 Loading scene embeddings...")

    cur.execute("SELECT scene_id, embedding FROM scene_embeddings ORDER BY scene_id;")
    rows = cur.fetchall()

    if not rows:
        print("❌ No scene embeddings found!")
        return

    ids = []
    vectors = []

    for scene_id, emb in rows:
        if emb is None or len(emb) == 0:
            continue
        ids.append(scene_id)
        vectors.append(np.array(emb, dtype=np.float32))

    vectors = np.vstack(vectors)
    dim = vectors.shape[1]

    print(f"📐 Embedding dimension = {dim}")
    print(f"🧠 Total scenes = {len(ids)}")

    index = faiss.IndexFlatL2(dim)
    index.add(vectors)

    # Save FAISS index
    faiss.write_index(index, f"{FAISS_DIR}/scene_index.faiss")
    print("💾 Saved FAISS index to scene_index.faiss")

    # Save mapping metadata
    with open(f"{FAISS_DIR}/scene_meta.pkl", "wb") as f:
        pickle.dump(ids, f)
    print("📝 Saved metadata (scene_id list)")

    print("🎉 Scene FAISS index built successfully!")

if __name__ == "__main__":
    build_scene_faiss()
