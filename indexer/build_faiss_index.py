import os
import psycopg2
import numpy as np
import faiss
import pickle

from config import DB_URL, FAISS_DIR, ACTOR_INDEX_PATH as INDEX_PATH, ACTOR_META_PATH as META_PATH

os.makedirs(FAISS_DIR, exist_ok=True)


# =============================
# HELPERS
# =============================
def connect_db():
    return psycopg2.connect(DB_URL)


def load_actor_embeddings():
    """Load all actor embeddings from DB."""
    print(" Connecting to database...")
    conn = connect_db()
    cur = conn.cursor()

    print(" Loading actor embeddings from database...")
    cur.execute("SELECT actor_id, embedding FROM actor_faces ORDER BY actor_id;")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    if not rows:
        print(" No actor embeddings found!")
        return None, None

    actor_ids = []
    embeddings = []

    for actor_id, emb in rows:
        if emb is None:
            continue
        actor_ids.append(actor_id)
        embeddings.append(np.asarray(emb, dtype=np.float32))

    if not embeddings:
        return None, None

    return actor_ids, np.vstack(embeddings)


def save_actor_faiss_index(embeddings, actor_ids):
    """Build & save FAISS index + metadata."""
    dim = embeddings.shape[1]

    print(f" Embedding dimension = {dim}")
    print(f" Total actor embeddings = {len(actor_ids)}")

    # Build FAISS index
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    # Save FAISS index
    faiss.write_index(index, INDEX_PATH)
    print(f"Saved FAISS index → {INDEX_PATH}")

    # Save metadata
    with open(META_PATH, "wb") as f:
        pickle.dump(actor_ids, f)
    print(f" Saved actor metadata → {META_PATH}")


# =============================
# MAIN PIPELINE FUNCTION
# =============================
def run():
    print("\n Building Actor FAISS Index...")

    actor_ids, embeddings = load_actor_embeddings()

    if actor_ids is None:
        print("Nothing to index. Skipping.")
        return

    save_actor_faiss_index(embeddings, actor_ids)

    print("🎉 Actor FAISS index built successfully!")


# Allow standalone usage
if __name__ == "__main__":
    run()
# if __name__ == "__main__":
#     run()