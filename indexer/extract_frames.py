import os
import subprocess
from scenedetect import VideoManager, SceneManager
from scenedetect.detectors import ContentDetector

MOVIE_DIR = "/data/movies"
OUTPUT_DIR = "/data/frames"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def extract_frames_from_movie(movie_path, sensitivity=30.0):
    """Detect scenes in a movie and extract one keyframe per scene."""
    
    print(f"\n Extracting frames from: {os.path.basename(movie_path)}")

    video_manager = VideoManager([movie_path])
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=sensitivity))

    video_manager.set_downscale_factor()
    video_manager.start()
    
    scene_manager.detect_scenes(frame_source=video_manager)
    scene_list = scene_manager.get_scene_list()
    
    print(f"Detected {len(scene_list)} scenes.")

    # Extract a key frame from the start of each detected scene
    for i, scene in enumerate(scene_list):
        start_time = scene[0].get_timecode()
        output_file = f"{os.path.basename(movie_path)}_scene_{i+1}.jpg"
        output_path = os.path.join(OUTPUT_DIR, output_file)

        cmd = [
            "ffmpeg", "-y",
            "-ss", start_time,
            "-i", movie_path,
            "-frames:v", "1",
            output_path
        ]

        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"   ✓ Saved {output_path}")

    print("🎉 Frame extraction finished!")



# ----------------------------------------------------------
#        MAIN PIPELINE FUNCTION (called from run_all)
# ----------------------------------------------------------
def run():
    print("\nRunning Frame Extraction...")

    # Process all video files in /data/movies
    for movie_file in os.listdir(MOVIE_DIR):

        if not movie_file.lower().endswith((".mp4", ".mkv", ".avi", ".mov")):
            continue
        
        movie_path = os.path.join(MOVIE_DIR, movie_file)
        extract_frames_from_movie(movie_path)

    print("\n✅ All frames extracted for all movies.")



# Allow standalone execution
if __name__ == "__main__":
    run()


















'''import os
import subprocess
from scenedetect import VideoManager, SceneManager
from scenedetect.detectors import ContentDetector

# ✅ Path to the movie
MOVIE_PATH = "/data/movies/Chiru_Test_fixed.mp4"
# ✅ Output folder for frames
OUTPUT_DIR = "/data/frames"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 🔹 Set up scene detection
video_manager = VideoManager([MOVIE_PATH])
scene_manager = SceneManager()
scene_manager.add_detector(ContentDetector(threshold=30.0))  # adjust threshold for sensitivity

video_manager.set_downscale_factor()
video_manager.start()
scene_manager.detect_scenes(frame_source=video_manager)
scene_list = scene_manager.get_scene_list()

print(f"🎬 Detected {len(scene_list)} scenes. Extracting 1 key frame per scene...")

# 🔹 Extract 1 frame from the start of each scene
for i, scene in enumerate(scene_list):
    start_time = scene[0].get_timecode()
    output_path = os.path.join(OUTPUT_DIR, f"scene_{i+1}.jpg")
    cmd = [
        "ffmpeg", "-y", "-ss", start_time, "-i", MOVIE_PATH,
        "-frames:v", "1", output_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"✅ Saved {output_path}")

print("🎉 Frame extraction complete!")'''
