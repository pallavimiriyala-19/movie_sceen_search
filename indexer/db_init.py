#!/usr/bin/env python3

"""
Final idempotent DB initializer for movie_sceen_search (original/code-compatible schema).

Creates the original tables you provided (actors, actor_faces, scenes, scene_actor_presence,
scene_attributes, scene_embeddings) with the exact column names and types your code expects.

Behavior:
 - Attempts to CREATE EXTENSION vector (pgvector) if available and falls back to FLOAT8[].
 - Uses CREATE TABLE IF NOT EXISTS to be safe on repeated runs.
 - Runs ALTER TABLE ... ADD COLUMN IF NOT EXISTS for a small set of safe migrations
   (e.g. adding confidence, frame_path) so older DBs get updated automatically.
 - Safe to run multiple times.

Run inside the indexer container:
    docker exec -it highlevel_indexer python3 /indexer/db_init.py
"""
import os
import sys
import psycopg2
from psycopg2.extras import register_default_json
from psycopg2 import sql

DB_URL = os.environ.get("DATABASE_URL", "postgresql://msuser:mssecret@postgres/moviesearch")


def get_conn():
    return psycopg2.connect(DB_URL)


def extension_exists(cur, ext_name: str) -> bool:
    cur.execute("SELECT 1 FROM pg_extension WHERE extname = %s;", (ext_name,))
    return cur.fetchone() is not None


def try_create_extension(cur, ext_name: str):
    try:
        cur.execute(sql.SQL("CREATE EXTENSION IF NOT EXISTS {}").format(sql.Identifier(ext_name)))
    except Exception as e:
        # Not fatal — extension may not be present in image
        print(f"[db_init] could not create extension {ext_name}: {e}")


def run():
    conn = get_conn()
    conn.autocommit = False
    cur = conn.cursor()
    register_default_json(cur)

    print("[db_init] checking/creating pgvector extension...")
    try_create_extension(cur, "vector")
    vector_supported = False
    try:
        vector_supported = extension_exists(cur, "vector")
    except Exception:
        vector_supported = False
    print(f"[db_init] pgvector supported={vector_supported}")

    # Choose column types depending on vector availability
    actor_emb_col = "VECTOR(512)" if vector_supported else "FLOAT8[]"
    scene_emb_col = "VECTOR(384)" if vector_supported else "FLOAT8[]"

    # Create tables exactly matching your original schema
    statements = [
        # pgcrypto extension for gen_random_uuid (if not present)
        "CREATE EXTENSION IF NOT EXISTS pgcrypto;",

        # actors
        """
        CREATE TABLE IF NOT EXISTS actors (
          actor_id SERIAL PRIMARY KEY,
          name TEXT NOT NULL UNIQUE,
          aliases TEXT[] DEFAULT '{}',
          jellyfin_person_id TEXT,
          created_at TIMESTAMP DEFAULT now()
        );
        """,

        # actor_faces (face embeddings) — using file_path and FLOAT8[] (or pgvector)
        f"""
        CREATE TABLE IF NOT EXISTS actor_faces (
          face_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          actor_id INT REFERENCES actors(actor_id) ON DELETE CASCADE,
          file_path TEXT NOT NULL,
          embedding {actor_emb_col},
          quality FLOAT8,
          source_item_id TEXT,
          created_at TIMESTAMP DEFAULT now()
        );
        """,

        # scenes (original code expectation)
        """
        CREATE TABLE IF NOT EXISTS scenes (
          scene_id SERIAL PRIMARY KEY,
          movie_name TEXT,
          start_time DOUBLE PRECISION,
          end_time DOUBLE PRECISION,
          duration DOUBLE PRECISION,
          thumbnail_path TEXT
        );
        """,

        # scene_actor_presence (original schema plus allowance for later 'confidence' and 'frame_path')
        """
        CREATE TABLE IF NOT EXISTS scene_actor_presence (
          id SERIAL PRIMARY KEY,
          scene_id INT REFERENCES scenes(scene_id) ON DELETE CASCADE,
          actor_id INT REFERENCES actors(actor_id),
          face_conf FLOAT8,
          visible_ms INT,
          first_seen_ms INT,
          last_seen_ms INT
        );
        """,

        # scene_attributes
        """
        CREATE TABLE IF NOT EXISTS scene_attributes (
          scene_id INT PRIMARY KEY REFERENCES scenes(scene_id) ON DELETE CASCADE,
          objects TEXT[] DEFAULT '{}',
          caption TEXT,
          tags TEXT[] DEFAULT '{}',
          updated_at TIMESTAMP DEFAULT now()
        );
        """,

        # scene_embeddings
        f"""
        CREATE TABLE IF NOT EXISTS scene_embeddings (
          scene_id INT PRIMARY KEY REFERENCES scenes(scene_id) ON DELETE CASCADE,
          embedding {scene_emb_col} DEFAULT '{{}}',
          updated_at TIMESTAMP DEFAULT now()
        );
        """,
    ]

    try:
        for s in statements:
            cur.execute(s)
        conn.commit()
        print("[db_init] created/verified tables (original schema).")
    except Exception as e:
        conn.rollback()
        print("[db_init] ERROR creating tables:", e)
        cur.close()
        conn.close()
        sys.exit(1)

    # Safe idempotent migrations to add columns that your current code uses but original schema might not have
    migrations = [
    "ALTER TABLE scene_actor_presence ADD COLUMN IF NOT EXISTS confidence DOUBLE PRECISION;",
    "ALTER TABLE scene_actor_presence ADD COLUMN IF NOT EXISTS frame_path TEXT;",

    # actor_faces from original schema
    "ALTER TABLE actor_faces ADD COLUMN IF NOT EXISTS file_path TEXT;",
    "ALTER TABLE actor_faces ADD COLUMN IF NOT EXISTS embedding FLOAT8[];",
    "ALTER TABLE actor_faces ADD COLUMN IF NOT EXISTS quality FLOAT8;",
    "ALTER TABLE actor_faces ADD COLUMN IF NOT EXISTS source_item_id TEXT;"
]

    try:
        for m in migrations:
            cur.execute(m)
        conn.commit()
        print("[db_init] applied safe migrations (added any missing columns).")
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
