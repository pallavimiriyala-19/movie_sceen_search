"""Centralized configuration for indexer and backend.

All modules should import values from here instead of hardcoding paths/URLs.
This file reads from environment variables and supplies sensible defaults used
throughout the project.
"""
import os

# Database
DB_URL = os.environ.get("DATABASE_URL", "postgresql://msuser:mssecret@postgres/moviesearch")

# Directories
FRAMES_DIR = os.environ.get("FRAMES_DIR", "/data/frames")
FAISS_DIR = os.environ.get("FAISS_DIR", "/data/faiss")
FACES_DIR = os.environ.get("FACES_DIR", "/data/faces")
PEOPLE_PATH = os.environ.get("PEOPLE_PATH", "/data/People")
MOVIE_DIR = os.environ.get("MOVIE_DIR", "/data/movies")
SCENES_OUTPUT_DIR = os.environ.get("SCENES_DIR", "/data/scenes")

# FAISS paths (can be individually overridden)
ACTOR_INDEX_PATH = os.environ.get("ACTOR_FAISS_PATH", os.path.join(FAISS_DIR, "actor_gallery.index"))
ACTOR_META_PATH = os.environ.get("ACTOR_META_PATH", os.path.join(FAISS_DIR, "actor_metadata.pkl"))
SCENE_INDEX_PATH = os.environ.get("SCENE_FAISS_PATH", os.path.join(FAISS_DIR, "scene_index.faiss"))
SCENE_META_PATH = os.environ.get("SCENE_META_PATH", os.path.join(FAISS_DIR, "scene_meta.pkl"))

# Thresholds
MIN_MATCH_CONFIDENCE = float(os.environ.get("MIN_MATCH_CONFIDENCE", "0.25"))


# Ensure common directories exist when running in scripts
for d in (FAISS_DIR, FRAMES_DIR, FACES_DIR, SCENES_OUTPUT_DIR):
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        # Best-effort: if creation fails (permissions), let calling code handle the error
        pass
