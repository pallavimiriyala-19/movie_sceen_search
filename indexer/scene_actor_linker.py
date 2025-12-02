import os
import re
import sys
import logging
import pickle
import numpy as np
import psycopg2
import faiss
from PIL import Image
from insightface.app import FaceAnalysis


# =======================
# CONFIG (centralized)
# =======================
from config import (
    DB_URL,
    FRAMES_DIR,
    ACTOR_INDEX_PATH as FAISS_PATH,
    ACTOR_META_PATH as META_PATH,
    MIN_MATCH_CONFIDENCE as MIN_CONFIDENCE,
)
from utils import extract_scene_id


# =======================
# Logging
# =======================
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("scene_actor_linker")


# =======================
# HELPERS
# =======================
def connect_db():
    return psycopg2.connect(DB_URL)


def load_faiss_index():
    logger.info("Loading FAISS index & metadata from %s and %s", FAISS_PATH, META_PATH)

    if not os.path.exists(FAISS_PATH):
        logger.error("FAISS index not found at %s", FAISS_PATH)
        raise FileNotFoundError(FAISS_PATH)
    if not os.path.exists(META_PATH):
        logger.error("FAISS metadata not found at %s", META_PATH)
        raise FileNotFoundError(META_PATH)

    try:
        index = faiss.read_index(FAISS_PATH)
    except Exception as e:
        logger.exception("Failed to read FAISS index: %s", e)
        raise

    try:
        with open(META_PATH, "rb") as f:
            actor_ids = pickle.load(f)
    except Exception as e:
        logger.exception("Failed to load actor metadata: %s", e)
        raise

    # Basic validation
    try:
        ntotal = index.ntotal
    except Exception:
        ntotal = None

    if ntotal is not None and len(actor_ids) != ntotal:
        logger.warning("actor_ids length (%d) != FAISS index ntotal (%s)", len(actor_ids), ntotal)

    logger.info("Loaded %d actor embeddings (FAISS ntotal=%s)", len(actor_ids), ntotal)
    return index, actor_ids


def init_face_model():
    logger.info("Initializing InsightFace model (buffalo_l) in CPU mode")
    app = FaceAnalysis(name="buffalo_l", allowed_modules=["detection", "recognition"])
    app.prepare(ctx_id=-1)  # CPU mode
    return app


def process_frame(frame_path, index, actor_ids, app):
    """Detect faces, match embeddings; returns list of (actor_id, confidence)."""
    try:
        img = np.array(Image.open(frame_path).convert("RGB"))
    except Exception:
        logger.exception("Failed to open frame: %s", frame_path)
        return []

    faces = []
    try:
        faces = app.get(img)
    except Exception:
        logger.exception("Face detection failed for %s", frame_path)
        return []

    if not faces:
        return []

    results = []

    # Guard: ensure index has vectors
    if getattr(index, "ntotal", 0) == 0:
        logger.error("FAISS index is empty (ntotal=0)")
        return []

    for face in faces:
        if not hasattr(face, "embedding") or face.embedding is None:
            logger.debug("Skipping face without embedding in %s", frame_path)
            continue

        emb = face.embedding.astype("float32").reshape(1, -1)

        # Validate embedding dim vs index
        try:
            d = index.d
            if emb.shape[1] != d:
                logger.warning("Embedding dim (%d) != FAISS dim (%d). Skipping.", emb.shape[1], d)
                continue
        except Exception:
            # If index doesn't expose d, continue and let faiss handle shape mismatch
            pass

        try:
            distances, indices = index.search(emb, 1)
        except Exception:
            logger.exception("FAISS search failed for frame %s", frame_path)
            continue

        # indices may contain -1 if no result
        best_idx = int(indices[0][0])
        if best_idx < 0 or best_idx >= len(actor_ids):
            logger.debug("FAISS returned invalid index %s for %s", best_idx, frame_path)
            continue

        best_actor_id = actor_ids[best_idx]
        distance = float(distances[0][0])
        # simple confidence transform
        confidence = round(1 / (1 + distance), 4) if distance is not None else 0.0

        results.append((best_actor_id, confidence))

    return results


# =======================
# MAIN PIPELINE FUNCTION
# =======================
def run():
    logger.info("Starting Scene-Actor Linker")

    # Load FAISS and model ONCE
    index, actor_ids = load_faiss_index()
    app = init_face_model()

    # Connect to DB using context manager
    try:
        with connect_db() as conn:
            cur = conn.cursor()

            # Process frames
            if not os.path.isdir(FRAMES_DIR):
                logger.error("Frames directory does not exist: %s", FRAMES_DIR)
                return

            for file in sorted(os.listdir(FRAMES_DIR)):
                if not file.lower().endswith(".jpg"):
                    continue

                frame_path = os.path.join(FRAMES_DIR, file)

                # Extract scene_id using helper (dependency-free, unit-tested)
                scene_id = extract_scene_id(file)
                if scene_id is None:
                    logger.warning("Could not parse scene ID from filename: %s", file)
                    continue

                matches = process_frame(frame_path, index, actor_ids, app)

                if not matches:
                    logger.info("No faces detected in %s", file)
                    continue

                for actor_id, confidence in matches:
                    if confidence < MIN_CONFIDENCE:
                        logger.debug("Skipping low-confidence match for actor %s in scene %s: %.3f", actor_id, scene_id, confidence)
                        continue

                    # Insert only if not exists (avoid depending on a unique constraint)
                    print("FOund match:", scene_id, actor_id, confidence)
                    try:
                       cur.execute(
                                """
                                INSERT INTO scene_actor_presence (scene_id, actor_id, face_conf)
                                SELECT %s, %s, %s
                                WHERE NOT EXISTS (
                                    SELECT 1 FROM scene_actor_presence
                                    WHERE scene_id=%s AND actor_id=%s
                                )
                                """,
                                (scene_id, actor_id, confidence, scene_id, actor_id),
                            )
                       logger.info("Scene %s: actor=%s, conf=%.4f", scene_id, actor_id, confidence)
                    except Exception:
                        logger.exception("DB insert failed for scene %s actor %s", scene_id, actor_id)

            conn.commit()
            cur.close()
    except Exception:
        logger.exception("Database connection failed or pipeline interrupted")

    logger.info("Scene–Actor Linking Complete")



# Allow standalone execution
if __name__ == "__main__":
    run()