"""Lightweight smoke checks for the indexing pipeline.

Performs non-invasive checks:
- FAISS index and metadata file existence and basic validation
- DB connection sanity check (open/close)
- Frames directory existence

This script intentionally avoids initializing heavy dependencies like the face
model or running the full pipeline. It returns non-zero on failures so it can
be used in CI or startup checks.
"""
import logging
import sys
import pickle

import importlib.util
import os

# Import config by path to avoid package-level side-effects (some modules under
# `indexer` perform heavy imports at import-time which we want to avoid here).
config_path = os.path.join(os.path.dirname(__file__), "config.py")
spec = importlib.util.spec_from_file_location("indexer.config", config_path)
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

FAISS_PATH = config.ACTOR_INDEX_PATH
META_PATH = config.ACTOR_META_PATH
DB_URL = config.DB_URL
FRAMES_DIR = config.FRAMES_DIR

utils_path = os.path.join(os.path.dirname(__file__), "utils.py")
spec_u = importlib.util.spec_from_file_location("indexer.utils", utils_path)
utils = importlib.util.module_from_spec(spec_u)
spec_u.loader.exec_module(utils)
validate_paths = utils.validate_paths

logger = logging.getLogger("smoke_check")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")


def check_files():
    ok = True
    if not validate_paths(FAISS_PATH):
        logger.error("FAISS index file not found: %s", FAISS_PATH)
        ok = False
    else:
        logger.info("Found FAISS index file: %s", FAISS_PATH)

    if not validate_paths(META_PATH):
        logger.error("FAISS metadata file not found: %s", META_PATH)
        ok = False
    else:
        logger.info("Found FAISS metadata file: %s", META_PATH)

    if not validate_paths(FRAMES_DIR):
        logger.error("Frames directory not found: %s", FRAMES_DIR)
        ok = False
    else:
        logger.info("Found frames directory: %s", FRAMES_DIR)

    return ok


def check_metadata():
    try:
        with open(META_PATH, "rb") as f:
            actor_ids = pickle.load(f)
    except Exception as e:
        logger.exception("Failed to load actor metadata: %s", e)
        return False

    if not isinstance(actor_ids, (list, tuple)):
        logger.error("Actor metadata is not a list/tuple: %s", type(actor_ids))
        return False

    logger.info("Actor metadata appears valid (length=%d)", len(actor_ids))
    return True


def check_faiss_read():
    try:
        import faiss  # local import to avoid hard dependency for test discovery
    except Exception as e:
        logger.error("faiss import failed: %s", e)
        return False

    try:
        idx = faiss.read_index(FAISS_PATH)
    except Exception as e:
        logger.exception("faiss.read_index failed: %s", e)
        return False

    try:
        ntotal = idx.ntotal
        logger.info("FAISS index ntotal=%s", ntotal)
    except Exception:
        logger.warning("FAISS index does not expose ntotal")

    return True


def check_db_connect():
    try:
        import psycopg2
    except Exception as e:
        logger.error("psycopg2 import failed: %s", e)
        return False

    try:
        # use small timeout if possible
        conn = psycopg2.connect(DB_URL, connect_timeout=5)
        conn.close()
    except Exception as e:
        logger.exception("Database connection failed: %s", e)
        return False

    logger.info("Database connection successful (closed immediately)")
    return True


def main():
    ok = True

    logger.info("Starting smoke checks")

    files_ok = check_files()
    ok = ok and files_ok

    if files_ok:
        meta_ok = check_metadata()
        ok = ok and meta_ok

        faiss_ok = check_faiss_read()
        ok = ok and faiss_ok

    db_ok = check_db_connect()
    ok = ok and db_ok

    if ok:
        logger.info("Smoke checks passed")
        return 0
    else:
        logger.error("Smoke checks failed")
        return 2


if __name__ == "__main__":
    sys.exit(main())
