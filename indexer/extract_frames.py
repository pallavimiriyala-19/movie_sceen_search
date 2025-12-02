import os
import subprocess
from scenedetect import VideoManager, SceneManager
from scenedetect.detectors import ContentDetector

from config import MOVIE_DIR, FRAMES_DIR

OUTPUT_DIR = FRAMES_DIR
os.makedirs(OUTPUT_DIR, exist_ok=True)


def extract_frames_from_movie(movie_path, sensitivity=30.0):
    print(f"\nProcessing movie: {os.path.basename(movie_path)}")
    video_manager = VideoManager([movie_path])
    scene_manager = SceneManager()
    print(f" Setting up scene detector with sensitivity={sensitivity}...")
    scene_manager.add_detector(ContentDetector(threshold=sensitivity))
    print(" Detecting scenes1...")
    video_manager.set_downscale_factor()
    video_manager.start()
    print(" Detecting scenes...")
    scene_manager.detect_scenes(frame_source=video_manager)
    print("🎬 Detected scenes. Extracting 1 key frame per scene...")
    scene_list = scene_manager.get_scene_list()

    for i, scene in enumerate(scene_list):
        print(f"   Extracting frame for scene {i+1} at {scene[0].get_timecode()}")
        start_time = scene[0].get_timecode()
        output_path = os.path.join(OUTPUT_DIR, f"{os.path.basename(movie_path)}_scene_{i+1}.jpg")
        cmd = ["ffmpeg", "-y", "-ss", start_time, "-i", movie_path, "-frames:v", "1", output_path]
        print(f"      Running command: {' '.join(cmd)}")
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run():
    for movie_file in os.listdir(MOVIE_DIR):
        if not movie_file.lower().endswith((".mp4", ".mkv", ".avi", ".mov")):
            continue
        movie_path = os.path.join(MOVIE_DIR, movie_file)
        extract_frames_from_movie(movie_path)


# if __name__ == "__main__":
#     run()
#     subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
#     print(f"   ✓ Saved {output_path}")

#     print("🎉 Frame extraction finished!")


# ----------------------------------------------------------
#        MAIN PIPELINE FUNCTION (called from run_all)
# ----------------------------------------------------------
def run():
    print("\nRunning Frame Extraction...")

    # Process all video files in MOVIE_DIR
    for movie_file in os.listdir(MOVIE_DIR):

        if not movie_file.lower().endswith((".mp4", ".mkv", ".avi", ".mov")):
            print(f" Skipping non-video file: {movie_file}")
            continue

        movie_path = os.path.join(MOVIE_DIR, movie_file)
        extract_frames_from_movie(movie_path)

    print("\n✅ All frames extracted for all movies.")


# Allow standalone execution
if __name__ == "__main__":
    print("🚀 Starting Frame Extraction Pipeline...")
    run()
# video_manager.start()
# scene_manager.detect_scenes(frame_source=video_manager)
# scene_list = scene_manager.get_scene_list()

# print(f"🎬 Detected {len(scene_list)} scenes. Extracting 1 key frame per scene...")

# # 🔹 Extract 1 frame from the start of each scene
# for i, scene in enumerate(scene_list):
#     start_time = scene[0].get_timecode()
#     output_path = os.path.join(OUTPUT_DIR, f"scene_{i+1}.jpg")
#     cmd = [
#         "ffmpeg", "-y", "-ss", start_time, "-i", MOVIE_PATH,
#         "-frames:v", "1", output_path
#     ]
#     subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
#     print(f"✅ Saved {output_path}")

# print("🎉 Frame extraction complete!")
