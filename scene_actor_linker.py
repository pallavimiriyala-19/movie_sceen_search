import os
import numpy as np
import psycopg2
import faiss
import pickle
from PIL import Image
from insightface.app import FaceAnalysis

DB_URL = os.environ.get("DATABASE_URL", "postgresql://msuser:mssecret@postgres/moviesearch")
FRAMES_DIR = "/data/frames"
FAISS_PATH = "/data/faiss/actor_gallery.index"
META_PATH = "/data/faiss/actor_metadata.pkl"

# Load FAISS index
index = faiss.read_index(FAISS_PATH)
with open(META_PATH, "rb") as f:
    actor_ids = pickle.load(f)

# DB connection
conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

# Face model
app = FaceAnalysis(name='buffalo_l', allowed_modules=['detection','recognition'])
app.prepare(ctx_id=-1)

print("🎬 Starting scene analysis...")

for file in sorted(os.listdir(FRAMES_DIR)):
    if not file.endswith(".jpg"):
        continue
    path = os.path.join(FRAMES_DIR, file)
    img = np.array(Image.open(path).convert("RGB"))
    faces = app.get(img)
    if not faces:
        print(f"🚫 No faces in {file}")
        continue
    for face in faces:
        emb = face.embedding.astype('float32').reshape(1, -1)
        distances, indices = index.search(emb, 1)
        best_actor_id = actor_ids[indices[0][0]]
        confidence = 1 / (1 + distances[0][0])
        cur.execute(
            "INSERT INTO scene_actor_presence (scene_id, actor_id, confidence, frame_path) VALUES (%s, %s, %s, %s)",
            (file.split('_')[1].split('.')[0], best_actor_id, confidence, path)
        )
        print(f"✅ {file}: Matched actor {best_actor_id} (conf={confidence:.3f})")

conn.commit()
cur.close()
conn.close()
print("🎉 Scene-actor detection completed!")
