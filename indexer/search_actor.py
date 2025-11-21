import os
import faiss
import numpy as np
import psycopg2
import pickle
from PIL import Image
from insightface.app import FaceAnalysis

from indexer.config import DB_URL, ACTOR_INDEX_PATH as index_path, ACTOR_META_PATH as meta_path

# Load FAISS index and metadata
index = faiss.read_index(index_path)
with open(meta_path, "rb") as f:
    actor_ids = pickle.load(f)

# Connect to DB
conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

# Load model
app = FaceAnalysis(name='buffalo_l', allowed_modules=['detection','recognition'])
app.prepare(ctx_id=-1)

# Test with one face image
test_img_path = "/data/faces/10.jpg"  # you can pick any actor’s image here
img = np.array(Image.open(test_img_path).convert("RGB"))
faces = app.get(img)
if len(faces) == 0:
    print("❌ No face found in image!")
    exit()

embedding = faces[0].embedding.astype('float32').reshape(1, -1)

# Search FAISS
distances, indices = index.search(embedding, 3)
best_actor_id = actor_ids[indices[0][0]]

cur.execute("SELECT name FROM actors WHERE actor_id = %s", (best_actor_id,))
actor_name = cur.fetchone()[0]
print(f"Closest match: {actor_name} (distance: {distances[0][0]:.4f})")

cur.close()
conn.close()
