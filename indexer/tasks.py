import subprocess
import sys
import os

def process_movie(movie_path):
    print(f"🎬 Starting processing for: {movie_path}")
    try:
        subprocess.run(["python", "scene_detector.py"], check=True)
        subprocess.run(["python", "scene_actor_linker.py"], check=True)
        print("✅ Processing complete.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error while processing movie: {e}")
        sys.exit(1)

if __name__ == "__main__":
    movie = "/data/movies/Chiru_Test_h264.mp4"
    process_movie(movie)
