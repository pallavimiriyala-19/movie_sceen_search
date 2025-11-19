import os
import psycopg2
import numpy as np
import faiss
import pickle

DB_URL = os.getenv("DATABASE_URL", "postgresql://msuser:mssecret@highlevel_postgres/moviesearch")
FAISS_DIR = "/data/faiss"

os.makedirs(FAISS_DIR, exist_ok=True)


def connect_db():
    return psycopg2.connect(DB_URL)


def load_scene_embeddings():
    """Load all scene embeddings from DB and return (ids, vectors)."""
    conn = connect_db()
    cur = conn.cursor()

    print(" Loading scene embeddings from database...")

    cur.execute("SELECT scene_id, embedding FROM scene_embeddings ORDER BY scene_id;")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    if not rows:
        print(" No scene embeddings found!")
        return None, None

    ids = []
    vectors = []

    for scene_id, emb in rows:
        if emb is None or len(emb) == 0:
            continue

        ids.append(scene_id)
        vectors.append(np.asarray(emb, dtype=np.float32))

    if not vectors:
        return None, None

    return ids, np.vstack(vectors)


def save_faiss_index(vectors, ids, output_path, meta_path):
    """Create and save a FAISS index + metadata."""
    dim = vectors.shape[1]

    print(f" Embedding dimension = {dim}")
    print(f" Total scenes = {len(ids)}")

    index = faiss.IndexFlatL2(dim)
    index.add(vectors)

    # Save FAISS index
    faiss.write_index(index, output_path)
    print(f" Saved FAISS index → {output_path}")

    # Save metadata
    with open(meta_path, "wb") as f:
        pickle.dump(ids, f)

    print(f" Saved scene metadata → {meta_path}")


# --------------------------------------------------------
#          MAIN PIPELINE FUNCTION (called by run_all)
# --------------------------------------------------------
def run():
    print("\n Building Scene FAISS Index...")

    ids, vectors = load_scene_embeddings()

    if ids is None:
        print(" Nothing to index. Skipping.")
        return

    index_path = os.path.join(FAISS_DIR, "scene_index.faiss")
    meta_path = os.path.join(FAISS_DIR, "scene_meta.pkl")

    save_faiss_index(vectors, ids, index_path, meta_path)

    print("🎉 Scene FAISS index built successfully!")


# Allow standalone execution
if __name__ == "__main__":
    run()










'''import psycopg2
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
'''