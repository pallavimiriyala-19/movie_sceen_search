import os
import numpy as np
import psycopg2
import faiss
import pickle
from PIL import Image
from insightface.app import FaceAnalysis

from config import DB_URL, FRAMES_DIR, ACTOR_INDEX_PATH as FAISS_PATH, ACTOR_META_PATH as META_PATH

# -----------------------------
# DB connection
# -----------------------------
conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

# Build mapping: thumbnail filename -> scene_id
print("📚 Loading scene metadata from DB...")
cur.execute("SELECT scene_id, thumbnail_path FROM scenes")
rows = cur.fetchall()

thumb_to_scene_id = {}
for scene_id, thumb_path in rows:
    if thumb_path is None:
        continue
    filename = os.path.basename(thumb_path)
    thumb_to_scene_id[filename] = scene_id

print(f"✅ Loaded {len(thumb_to_scene_id)} scene thumbnails from DB")

# -----------------------------
# Load FAISS index + actor ids
# -----------------------------
index = faiss.read_index(FAISS_PATH)
with open(META_PATH, "rb") as f:
    actor_ids = pickle.load(f)

# -----------------------------
# Face model
# -----------------------------
app = FaceAnalysis(name='buffalo_l', allowed_modules=['detection', 'recognition'])
app.prepare(ctx_id=-1)

print("🎬 Starting scene analysis...")

# -----------------------------
# Iterate over frames
# -----------------------------
for file in sorted(os.listdir(FRAMES_DIR)):
    if not file.lower().endswith(".jpg"):
        continue

    # Find matching scene_id using filename
    scene_id = thumb_to_scene_id.get(file)
    if scene_id is None:
        print(f"⚠ No scene row found for frame {file} . skipping")
        continue

    path = os.path.join(FRAMES_DIR, file)
    img = np.array(Image.open(path).convert("RGB"))
    faces = app.get(img)

    if not faces:
        print(f"🚫 No faces in {file}")
        continue

    inserted = 0
    for face in faces:
        emb = face.embedding.astype("float32").reshape(1, -1)
        distances, indices = index.search(emb, 1)

        best_actor_id = actor_ids[indices[0][0]]
        d = float(distances[0][0])
        confidence = float(1 / (1 + d))

        cur.execute(
            """
            INSERT INTO scene_actor_presence (scene_id, actor_id, face_conf)
            VALUES (%s, %s, %s)
            """,
            (scene_id, best_actor_id, confidence),
        )
        inserted += 1

    print(f"✅ {file}: inserted {inserted} faces for scene_id={scene_id}")

conn.commit()
cur.close()
conn.close()
print("🎉 Scene-actor detection completed!")
