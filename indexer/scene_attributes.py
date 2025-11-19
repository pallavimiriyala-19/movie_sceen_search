import os
import psycopg2
from psycopg2.extras import RealDictCursor
from ultralytics import YOLO
from PIL import Image
from sentence_transformers import SentenceTransformer
from transformers import BlipForConditionalGeneration, BlipProcessor
import numpy as np


# =============================
# CONFIG
# =============================
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://msuser:mssecret@highlevel_postgres/moviesearch")
FRAME_DIR = "/data/frames"

MODEL_YOLO = "yolov8n.pt"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # 384-dim


# =============================
# LOAD MODELS (ONCE)
# =============================
print("⚙️ Loading scene attribute models... (heavy step)")

yolo = YOLO(MODEL_YOLO)

caption_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
caption_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

embed_model = SentenceTransformer(EMBEDDING_MODEL)

print("✅ Models loaded successfully.")


# =============================
# DB CONNECTION HELPER
# =============================
def connect_db():
    return psycopg2.connect(DATABASE_URL)


# =============================
# ATTRIBUTE EXTRACTORS
# =============================
def detect_objects(image_path):
    """Detect objects using YOLO and return unique labels."""
    results = yolo(image_path)
    labels = []

    for r in results:
        for box in getattr(r, "boxes", []):
            cls_idx = int(box.cls)
            lbl = r.names.get(cls_idx, str(cls_idx))
            labels.append(lbl)

    # Deduplicate while preserving order
    seen = set()
    unique = []

    for l in labels:
        if l not in seen:
            seen.add(l)
            unique.append(l)

    return unique


def generate_caption(image_path):
    """Generate caption for an image using BLIP."""
    img = Image.open(image_path).convert("RGB")
    inputs = caption_processor(images=img, return_tensors="pt")
    out = caption_model.generate(**inputs)
    return caption_processor.decode(out[0], skip_special_tokens=True)


def embed_text(text):
    """Text embedding using SentenceTransformer."""
    return embed_model.encode(text, normalize_embeddings=True)


# =============================
# PROCESS A SINGLE SCENE
# =============================
def process_scene(scene_id, frame_path):
    """Extract objects, caption, tags, and embeddings for a scene and save to DB."""

    # ---- STEP 1: Object detection ----
    objects = detect_objects(frame_path)

    # ---- STEP 2: Caption ----
    caption = generate_caption(frame_path)

    # ---- STEP 3: Tags (keywords + detected) ----
    tags = list(objects)
    keywords = [
        "fight", "kiss", "hug", "car", "gun", "rain",
        "temple", "dance", "song", "cry", "explosion",
        "battle", "romance"
    ]
    caption_lower = caption.lower()

    for k in keywords:
        if k in caption_lower and k not in tags:
            tags.append(k)

    # ---- STEP 4: Embedding ----
    embedding = embed_text(caption)

    # ---- STEP 5: Save in DB ----
    conn = connect_db()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO scene_attributes (scene_id, objects, caption, tags, updated_at)
        VALUES (%s, %s, %s, %s, now())
        ON CONFLICT (scene_id) DO UPDATE
            SET objects = EXCLUDED.objects,
                caption = EXCLUDED.caption,
                tags = EXCLUDED.tags,
                updated_at = now();
        """,
        (scene_id, objects, caption, tags)
    )

    cur.execute(
        """
        INSERT INTO scene_embeddings (scene_id, embedding, updated_at)
        VALUES (%s, %s, now())
        ON CONFLICT (scene_id) DO UPDATE
            SET embedding = EXCLUDED.embedding,
                updated_at = now();
        """,
        (scene_id, list(map(float, embedding))),
    )

    conn.commit()
    cur.close()
    conn.close()

    print(f"Indexed scene {scene_id}: objects={objects} tags={tags}")


# =============================
# MAIN PIPELINE FUNCTION
# =============================
def run():
    print("\n Running Scene Attributes Extractor...")

    conn = connect_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT scene_id, thumbnail_path FROM scenes ORDER BY scene_id;")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    for row in rows:
        scene_id = row["scene_id"]
        thumb = row["thumbnail_path"]

        # If DB thumbnail not available, fallback to standard path
        frame_path = thumb if thumb and os.path.exists(thumb) \
            else os.path.join(FRAME_DIR, f"scene_{scene_id}.jpg")

        if not os.path.exists(frame_path):
            print(f" Skipping scene {scene_id}, missing frame: {frame_path}")
            continue

        try:
            process_scene(scene_id, frame_path)
        except Exception as e:
            print(f"Error processing scene {scene_id}: {e}")

    print("\n🎉 Scene attribute extraction complete!")


# Allow standalone execution
if __name__ == "__main__":
    run()



































'''# indexer/scene_attributes.py
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from ultralytics import YOLO
from PIL import Image
from sentence_transformers import SentenceTransformer
from transformers import BlipForConditionalGeneration, BlipProcessor
import numpy as np

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://msuser:mssecret@postgres/moviesearch")
MODEL_YOLO = "yolov8n.pt"  # small model for testing
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # 384-dim

# load models once
print("Loading models (this may take a while on first run)...")
yolo = YOLO(MODEL_YOLO)
caption_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
caption_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
embed_model = SentenceTransformer(EMBEDDING_MODEL)
print("Models loaded.")

def get_conn():
    return psycopg2.connect(DATABASE_URL)

def detect_objects(image_path):
    results = yolo(image_path)
    labels = []
    for r in results:
        for box in getattr(r, "boxes", []):
            cls_index = int(box.cls)
            lbl = r.names.get(cls_index, str(cls_index))
            labels.append(lbl)
    # dedupe keeping order
    seen = set()
    out = []
    for l in labels:
        if l not in seen:
            seen.add(l)
            out.append(l)
    return out

def caption_image(image_path):
    img = Image.open(image_path).convert("RGB")
    inputs = caption_processor(images=img, return_tensors="pt")
    out = caption_model.generate(**inputs)
    caption = caption_processor.decode(out[0], skip_special_tokens=True)
    return caption

def embed_text(text):
    vec = embed_model.encode(text, normalize_embeddings=True)
    return vec

def process_scene(scene_id, frame_path):
    objects = detect_objects(frame_path)
    caption = caption_image(frame_path)
    tags = list(objects)
    # simple keyword tags from caption (naive)
    keywords = ["fight","kiss","hug","car","gun","rain","temple","dance","song","cry","explosion","battle","romance"]
    for k in keywords:
        if k in caption.lower() and k not in tags:
            tags.append(k)
    embedding = embed_text(caption)

    conn = get_conn()
    cur = conn.cursor()
    # upsert attributes
    cur.execute("""
        INSERT INTO scene_attributes (scene_id, objects, caption, tags, updated_at)
        VALUES (%s, %s, %s, %s, now())
        ON CONFLICT (scene_id) DO UPDATE
          SET objects=EXCLUDED.objects, caption=EXCLUDED.caption, tags=EXCLUDED.tags, updated_at=now();
    """, (scene_id, objects, caption, tags))
    # upsert embedding
    cur.execute("""
        INSERT INTO scene_embeddings (scene_id, embedding, updated_at)
        VALUES (%s, %s, now())
        ON CONFLICT (scene_id) DO UPDATE
          SET embedding=EXCLUDED.embedding, updated_at=now();
    """, (scene_id, list(map(float, embedding))))
    conn.commit()
    cur.close()
    conn.close()
    print(f"Indexed scene {scene_id}: objects={objects} tags={tags}")

if __name__ == "__main__":
    # process all scenes that have frames
    FRAME_DIR = "/data/frames"
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT scene_id, thumbnail_path FROM scenes;")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    for row in rows:
        sid = row["scene_id"]
        thumb = row["thumbnail_path"]
        frame_path = thumb if thumb and os.path.exists(thumb) else os.path.join(FRAME_DIR, f"scene_{sid}.jpg")
        if not os.path.exists(frame_path):
            print(f"Skipping scene {sid}, frame missing: {frame_path}")
            continue
        try:
            process_scene(sid, frame_path)
        except Exception as e:
            print(f"Error processing scene {sid}: {e}")
'''