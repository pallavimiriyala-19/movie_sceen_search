CREATE TABLE IF NOT EXISTS scenes (
    scene_id SERIAL PRIMARY KEY,
    movie_name TEXT,
    start_time FLOAT,
    end_time FLOAT,
    duration FLOAT,
    thumbnail_path TEXT
);
