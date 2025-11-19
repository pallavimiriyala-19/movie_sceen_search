import os
import psycopg2
import numpy as np
import faiss
import pickle


# =============================
# CONFIG
# =============================
DB_URL = os.getenv("DATABASE_URL", "postgresql://msuser:mssecret@highlevel_postgres/moviesearch")
FAISS_DIR = "/data/faiss"
INDEX_PATH = f"{FAISS_DIR}/actor_gallery.index"
META_PATH = f"{FAISS_DIR}/actor_metadata.pkl"

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



"""import os
import psycopg2
import numpy as np
import faiss
import pickle

DB_URL = os.environ.get("DATABASE_URL", "postgresql://msuser:mssecret@postgres/moviesearch")
INDEX_PATH = "/data/faiss/actor_gallery.index"
META_PATH = "/data/faiss/actor_metadata.pkl"

os.makedirs("/data/faiss", exist_ok=True)

print("📦 Connecting to database...")
conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

# Load all embeddings
print("📥 Loading actor embeddings from database...")
cur.execute("SELECT actor_id, embedding FROM actor_faces")
rows = cur.fetchall()

if len(rows) == 0:
    print("❌ No embeddings found in database!")
    exit(0)

actor_ids = []
embeddings = []

for actor_id, emb in rows:
    if emb is None:
        continue
    actor_ids.append(actor_id)
    embeddings.append(np.array(emb, dtype='float32'))

embeddings = np.stack(embeddings)
print(f"✅ Loaded {len(embeddings)} embeddings from DB")

# Build FAISS index
dim = embeddings.shape[1]
index = faiss.IndexFlatL2(dim)
index.add(embeddings)

# Save index
faiss.write_index(index, INDEX_PATH)
with open(META_PATH, "wb") as f:
    pickle.dump(actor_ids, f)

print(f"🎉 FAISS index saved at {INDEX_PATH}")
print(f"🧾 Metadata saved at {META_PATH}")

cur.close()
conn.close()

"""