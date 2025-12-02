import os
import os
import psycopg2
import numpy as np
import faiss
import pickle

from config import DB_URL, FAISS_DIR, SCENE_INDEX_PATH, SCENE_META_PATH

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

    index_path = SCENE_INDEX_PATH
    meta_path = SCENE_META_PATH

    save_faiss_index(vectors, ids, index_path, meta_path)

    print("🎉 Scene FAISS index built successfully!")


# Allow standalone execution
if __name__ == "__main__":
    run()