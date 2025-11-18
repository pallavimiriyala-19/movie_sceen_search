import os
import numpy as np
import psycopg2
import faiss
import pickle
from PIL import Image
from insightface.app import FaceAnalysis

# =======================
# CONFIG
# =======================
DB_URL = os.environ.get("DATABASE_URL", "postgresql://msuser:mssecret@postgres/moviesearch")
FRAMES_DIR = "/data/frames"
FAISS_PATH = "/data/faiss/actor_gallery.index"
META_PATH = "/data/faiss/actor_metadata.pkl"

# =======================
# LOAD FAISS INDEX & METADATA
# =======================
print("📦 Loading FAISS index and metadata...")
index = faiss.read_index(FAISS_PATH)
with open(META_PATH, "rb") as f:
    actor_ids = pickle.load(f)
print(f"✅ Loaded {len(actor_ids)} actor embeddings")

# =======================
# CONNECT TO DATABASE
# =======================
print("🗃️ Connecting to database...")
conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

# =======================
# INITIALIZE FACE MODEL
# =======================
app = FaceAnalysis(name='buffalo_l', allowed_modules=['detection','recognition'])
app.prepare(ctx_id=-1)  # CPU mode

print("🎬 Starting scene analysis...")

# =======================
# PROCESS EACH SCENE FRAME
# =======================
for file in sorted(os.listdir(FRAMES_DIR)):
    if not file.endswith(".jpg"):
        continue

    frame_path = os.path.join(FRAMES_DIR, file)
    scene_id = int(file.split('_')[1].split('.')[0])

    img = np.array(Image.open(frame_path).convert("RGB"))
    faces = app.get(img)

    if not faces:
        print(f"🚫 No faces detected in {file}")
        continue

    for face in faces:
        emb = face.embedding.astype('float32').reshape(1, -1)
        distances, indices = index.search(emb, 1)
        best_idx = indices[0][0]
        best_actor_id = actor_ids[best_idx]
        distance = float(distances[0][0])
        confidence = round(1 / (1 + distance), 4)

        cur.execute(
            """
            INSERT INTO scene_actor_presence (scene_id, actor_id, confidence, frame_path)
            VALUES (%s, %s, %s, %s)
            """,
            (scene_id, best_actor_id, confidence, frame_path)
        )

        print(f"✅ Scene {scene_id}: matched actor_id={best_actor_id}, conf={confidence}")

conn.commit()
cur.close()
conn.close()
print("🎉 Scene–actor linking complete!")
