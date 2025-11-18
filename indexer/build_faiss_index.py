import os
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
