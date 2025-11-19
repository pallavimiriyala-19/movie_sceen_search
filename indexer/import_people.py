import os
import psycopg2
from insightface.app import FaceAnalysis
from PIL import Image
import numpy as np

DB_URL = os.environ.get("DATABASE_URL", "postgresql://msuser:mssecret@postgres/moviesearch")
PEOPLE_PATH = "/data/People"
FACES_DIR = "/data/faces"

# Connect to DB
conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

os.makedirs(FACES_DIR, exist_ok=True)

# Initialize face model
print("Loading InsightFace model...")
app = FaceAnalysis(name='buffalo_l', allowed_modules=['detection', 'recognition'])
app.prepare(ctx_id=-1)
print("Model loaded successfully!")

def insert_actor(name):
    cur.execute("INSERT INTO actors (name) VALUES (%s) ON CONFLICT DO NOTHING RETURNING actor_id;", (name,))
    res = cur.fetchone()
    if not res:
        cur.execute("SELECT actor_id FROM actors WHERE name = %s;", (name,))
        res = cur.fetchone()
    conn.commit()
    return res[0]

def process_actor_image(actor_id, img_path):
    try:
        img = np.array(Image.open(img_path).convert("RGB"))
        faces = app.get(img)
        if len(faces) == 0:
            print(f"No face detected for {img_path}")
            return
        embedding = faces[0].embedding.tolist()
        target_path = os.path.join(FACES_DIR, f"{actor_id}.jpg")
        Image.fromarray(img).save(target_path)
        cur.execute(
            "INSERT INTO actor_faces (actor_id, file_path, embedding, quality) VALUES (%s, %s, %s, %s)",
            (actor_id, target_path, embedding, 1.0)
        )
        conn.commit()
        print(f" Saved face for {actor_id}")
    except Exception as e:
        print(f"Error processing {img_path}: {e}")

# Traverse People folders
for letter in sorted(os.listdir(PEOPLE_PATH)):
    letter_path = os.path.join(PEOPLE_PATH, letter)
    if os.path.isdir(letter_path):
        for actor_name in os.listdir(letter_path):
            actor_path = os.path.join(letter_path, actor_name)
            if not os.path.isdir(actor_path):
                continue
            # Pick one image (folder.jpg or primary.jpg)
            img_file = None
            for file in os.listdir(actor_path):
                if file.lower() in ["folder.jpg", "primary.jpg", "poster.jpg"]:
                    img_file = os.path.join(actor_path, file)
                    break
            if not img_file:
                continue
            actor_id = insert_actor(actor_name)
            process_actor_image(actor_id, img_file)

cur.close()
conn.close()
print("🎉 All actors processed successfully!")
