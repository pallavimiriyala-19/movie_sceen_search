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
DB_URL = os.environ.get("DATABASE_URL", "postgresql://msuser:mssecret@highlevel_postgres/moviesearch")
FRAMES_DIR = "/data/frames"
FAISS_PATH = "/data/faiss/actor_gallery.index"
META_PATH = "/data/faiss/actor_metadata.pkl"


# =======================
# HELPERS
# =======================
def connect_db():
    return psycopg2.connect(DB_URL)


def load_faiss_index():
    print("Loading FAISS index & metadata...")
    index = faiss.read_index(FAISS_PATH)

    with open(META_PATH, "rb") as f:
        actor_ids = pickle.load(f)

    print(f"Loaded {len(actor_ids)} actor embeddings.")
    return index, actor_ids


def init_face_model():
    print("Initializing InsightFace model...")
    app = FaceAnalysis(name='buffalo_l', allowed_modules=['detection', 'recognition'])
    app.prepare(ctx_id=-1)  # CPU mode
    return app


def process_frame(frame_path, index, actor_ids, app):
    """Detect faces, match embeddings, return results."""
    img = np.array(Image.open(frame_path).convert("RGB"))
    faces = app.get(img)

    if not faces:
        return []

    results = []

    for face in faces:
        emb = face.embedding.astype("float32").reshape(1, -1)
        distances, indices = index.search(emb, 1)

        best_idx = indices[0][0]
        best_actor_id = actor_ids[best_idx]

        distance = float(distances[0][0])
        confidence = round(1 / (1 + distance), 4)

        results.append((best_actor_id, confidence))

    return results


# =======================
# MAIN PIPELINE FUNCTION
# =======================
def run():
    print("\n Running Scene-Actor Linker...")

    # Load FAISS and model ONCE
    index, actor_ids = load_faiss_index()
    app = init_face_model()

    # Connect to DB
    conn = connect_db()
    cur = conn.cursor()

    # Process frames
    for file in sorted(os.listdir(FRAMES_DIR)):
        if not file.endswith(".jpg"):
            continue

        frame_path = os.path.join(FRAMES_DIR, file)

        # Extract scene_id from filename
        # Expected format: <movie>_scene_XX.jpg
        try:
            scene_id = int(file.split("_scene_")[1].split(".")[0])
        except:
            print(f" Could not parse scene ID from: {file}")
            continue

        matches = process_frame(frame_path, index, actor_ids, app)

        if not matches:
            print(f"No faces detected in {file}")
            continue

        for actor_id, confidence in matches:
            cur.execute(
                """
                INSERT INTO scene_actor_presence (scene_id, actor_id, confidence, frame_path)
                VALUES (%s, %s, %s, %s)
                """,
                (scene_id, actor_id, confidence, frame_path)
            )

            print(f"  Scene {scene_id}: actor={actor_id}, conf={confidence}")

    conn.commit()
    cur.close()
    conn.close()

    print("\n🎉 Scene–Actor Linking Complete!")


# Allow standalone execution
if __name__ == "__main__":
    run()




"""import os
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
            '''
            INSERT INTO scene_actor_presence (scene_id, actor_id, confidence, frame_path)
            VALUES (%s, %s, %s, %s)
            ''',
            (scene_id, best_actor_id, confidence, frame_path)
        )

        print(f"✅ Scene {scene_id}: matched actor_id={best_actor_id}, conf={confidence}")

conn.commit()
cur.close()
conn.close()
print("🎉 Scene–actor linking complete!")
"""