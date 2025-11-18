import os
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

print("🎉 Frame extraction complete!")
