CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS actors (
  actor_id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  aliases TEXT[] DEFAULT '{}',
  jellyfin_person_id TEXT,
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS actor_faces (
  face_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_id INT REFERENCES actors(actor_id) ON DELETE CASCADE,
  file_path TEXT NOT NULL,
  embedding FLOAT8[],
  quality FLOAT8,
  source_item_id TEXT,
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS scene_actor_presence (
  id SERIAL PRIMARY KEY,
  scene_id INT,
  actor_id INT REFERENCES actors(actor_id),
  face_conf FLOAT8,
  visible_ms INT,
  first_seen_ms INT,
  last_seen_ms INT
);
