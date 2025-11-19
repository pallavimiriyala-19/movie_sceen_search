#  --- command to make it exccutable
#run inside the indexer container (one-time)
#      docker exec -it highlevel_indexer python3 /indexer/db_init.py



#!/usr/bin/env python3
"""
idempotent DB initializer for movie_scene_search.

Run this once (or at container start) to ensure:
 - pgvector extension installed if possible
 - required tables exist (CREATE IF NOT EXISTS)
 - required columns exist (ALTER TABLE ADD COLUMN IF NOT EXISTS)
This script is safe to run multiple times.
"""

import os
import sys
import psycopg2
from psycopg2 import sql
from psycopg2.extras import register_default_json

DB_URL = os.environ.get("DATABASE_URL", "postgresql://msuser:mssecret@postgres/moviesearch")


def get_conn():
    return psycopg2.connect(DB_URL)


def extension_exists(cur, ext_name: str) -> bool:
    cur.execute("SELECT 1 FROM pg_extension WHERE extname = %s;", (ext_name,))
    return cur.fetchone() is not None


def try_create_extension(cur, ext_name: str):
    try:
        cur.execute(sql.SQL("CREATE EXTENSION IF NOT EXISTS {}").format(sql.Identifier(ext_name)))
        return True
    except Exception as e:
        # Can't install extension (maybe not available in this image) — bail silently
        print(f"[db_init] cannot CREATE EXTENSION {ext_name}: {e}")
        return False


def run():
    conn = get_conn()
    conn.autocommit = False
    cur = conn.cursor()
    register_default_json(cur)

    # Try to install pgvector if available in the Postgres image
    vector_supported = False
    try:
        print("[db_init] checking/creating pgvector extension...")
        try_create_extension(cur, "vector")
        vector_supported = extension_exists(cur, "vector")
        print(f"[db_init] pgvector supported={vector_supported}")
    except Exception as e:
        print(f"[db_init] pgvector check/create failed: {e}")
        vector_supported = False

    # Choose column types depending on vector availability
    actor_emb_col = "VECTOR(512)" if vector_supported else "double precision[]"
    scene_emb_col = "VECTOR(384)" if vector_supported else "double precision[]"

    # Use SQL strings with IF NOT EXISTS (Postgres supports "CREATE TABLE IF NOT EXISTS")
    # Create main tables
    statements = [

        # actors
        f"""
        CREATE TABLE IF NOT EXISTS actors (
            actor_id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            folder_path TEXT,
            thumbnail_path TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """,

        # actor_faces
        f"""
        CREATE TABLE IF NOT EXISTS actor_faces (
            id SERIAL PRIMARY KEY,
            actor_id INT REFERENCES actors(actor_id) ON DELETE CASCADE,
            image_path TEXT NOT NULL,
            embedding {actor_emb_col},
            created_at TIMESTAMP DEFAULT NOW()
        );
        """,

        # movies
        """
        CREATE TABLE IF NOT EXISTS movies (
            movie_id SERIAL PRIMARY KEY,
            filename TEXT NOT NULL,
            duration_ms INT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """,

        # scenes
        """
        CREATE TABLE IF NOT EXISTS scenes (
            scene_id SERIAL PRIMARY KEY,
            movie_id INT REFERENCES movies(movie_id) ON DELETE CASCADE,
            start_ms INT NOT NULL,
            end_ms INT NOT NULL,
            thumbnail_path TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """,

        # scene_actor_presence
        """
        CREATE TABLE IF NOT EXISTS scene_actor_presence (
            id SERIAL PRIMARY KEY,
            scene_id INT REFERENCES scenes(scene_id) ON DELETE CASCADE,
            actor_id INT REFERENCES actors(actor_id) ON DELETE CASCADE,
            confidence DOUBLE PRECISION,
            face_conf DOUBLE PRECISION,
            frame_path TEXT,
            visible_ms INT DEFAULT 0,
            first_seen_ms INT,
            last_seen_ms INT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """,

        # scene_attributes
        """
        CREATE TABLE IF NOT EXISTS scene_attributes (
            scene_id INT PRIMARY KEY REFERENCES scenes(scene_id) ON DELETE CASCADE,
            objects TEXT[],
            caption TEXT,
            tags TEXT[],
            updated_at TIMESTAMP DEFAULT NOW()
        );
        """,

        # scene_embeddings
        f"""
        CREATE TABLE IF NOT EXISTS scene_embeddings (
            scene_id INT PRIMARY KEY REFERENCES scenes(scene_id) ON DELETE CASCADE,
            embedding {scene_emb_col},
            updated_at TIMESTAMP DEFAULT NOW()
        );
        """,

        # meta tables
        """
        CREATE TABLE IF NOT EXISTS scene_faiss_meta (
            id SERIAL PRIMARY KEY,
            scene_id INT UNIQUE REFERENCES scenes(scene_id) ON DELETE CASCADE,
            index_offset INT
        );
        """,

        """
        CREATE TABLE IF NOT EXISTS actor_faiss_meta (
            id SERIAL PRIMARY KEY,
            actor_id INT UNIQUE REFERENCES actors(actor_id) ON DELETE CASCADE,
            index_offset INT
        );
        """,
    ]

    # Run create statements
    try:
        for s in statements:
            cur.execute(s)
        conn.commit()
        print("[db_init] created/verified tables.")
    except Exception as e:
        conn.rollback()
        print("[db_init] ERROR creating tables:", e)
        cur.close()
        conn.close()
        sys.exit(1)

    # Now run idempotent ALTER TABLE ADD COLUMN IF NOT EXISTS for known missing columns issues (e.g. confidence)
    migrations = [
        "ALTER TABLE scene_actor_presence ADD COLUMN IF NOT EXISTS confidence DOUBLE PRECISION;",
        "ALTER TABLE scene_actor_presence ADD COLUMN IF NOT EXISTS face_conf DOUBLE PRECISION;",
        "ALTER TABLE scene_actor_presence ADD COLUMN IF NOT EXISTS frame_path TEXT;",
        # Any future safe migrations can be appended here
    ]
    try:
        for m in migrations:
            cur.execute(m)
        conn.commit()
        print("[db_init] applied safe migrations (if any).")
    except Exception as e:
        conn.rollback()
        print("[db_init] ERROR applying migrations:", e)
        cur.close()
        conn.close()
        sys.exit(1)

    cur.close()
    conn.close()
    print("[db_init] finished successfully.")


if __name__ == "__main__":
    run()
