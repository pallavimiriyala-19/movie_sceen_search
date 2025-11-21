import os
import cv2
import psycopg2
from scenedetect import SceneManager, ContentDetector, open_video

from indexer.config import DB_URL, MOVIE_DIR, SCENES_OUTPUT_DIR as OUTPUT_DIR

import os
import cv2
import psycopg2
from scenedetect import SceneManager, ContentDetector, open_video

from indexer.config import DB_URL, MOVIE_DIR, SCENES_OUTPUT_DIR as OUTPUT_DIR

os.makedirs(OUTPUT_DIR, exist_ok=True)


def connect_db():
    return psycopg2.connect(DB_URL)


def detect_scenes(video_path):
    """Detect scenes using PySceneDetect and return (start, end, duration)."""
    video = open_video(video_path)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=27.0))

    scene_manager.detect_scenes(video, show_progress=True)
    scene_list = scene_manager.get_scene_list()

    scenes = []
    for (start, end) in scene_list:
        start_time = start.get_seconds()
        end_time = end.get_seconds()
        duration = end_time - start_time
        scenes.append((start_time, end_time, duration))

    return scenes


def extract_thumbnail(video_path, timestamp, output_path):
    """Extract a single thumbnail at the given timestamp."""
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
    ret, frame = cap.read()

    if ret:
        cv2.imwrite(output_path, frame)

    cap.release()


def save_to_db(movie_name, scenes):
    """Save scene metadata + thumbnail path to DB."""
    conn = connect_db()
    cur = conn.cursor()

    for (start, end, duration, thumb_path) in scenes:
        cur.execute(
            """
            INSERT INTO scenes (movie_name, start_time, end_time, duration, thumbnail_path)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (movie_name, start, end, duration, thumb_path)
        )

    conn.commit()
    conn.close()


# -----------------------------------------------------------
#   MAIN PIPELINE FUNCTION (This is what run_all.py will call)
# -----------------------------------------------------------
def run():
    """Run scene detection on all movies."""
    print("🎬 Running Scene Detector...")

    for movie_file in os.listdir(MOVIE_DIR):

        # skip non-video formats
        if not movie_file.lower().endswith((".mp4", ".mkv", ".avi", ".mov")):
            continue

        movie_path = os.path.join(MOVIE_DIR, movie_file)
        print(f"\n� Processing: {movie_file}")

        detected_scenes = detect_scenes(movie_path)
        if not detected_scenes:
            print(f"⚠ No scenes found in {movie_file}")
            continue

        scenes_to_save = []

        for i, (start, end, duration) in enumerate(detected_scenes):
            midpoint = start + (duration / 2)
            thumb_path = os.path.join(OUTPUT_DIR, f"{movie_file}_scene_{i+1}.jpg")

            extract_thumbnail(movie_path, midpoint, thumb_path)
            scenes_to_save.append((start, end, duration, thumb_path))

        save_to_db(movie_file, scenes_to_save)

        print(f"✓ {len(scenes_to_save)} scenes indexed for {movie_file}")


# Allow standalone execution too
if __name__ == "__main__":
    run()

