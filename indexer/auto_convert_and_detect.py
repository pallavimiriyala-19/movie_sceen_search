import os
import subprocess

MOVIE_DIR = "/data/movies"

for filename in os.listdir(MOVIE_DIR):
    if not filename.lower().endswith(".mp4"):
        continue

    path = os.path.join(MOVIE_DIR, filename)
    print(f"🎞 Checking: {filename}")

    # Probe codec
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
           "-show_entries", "stream=codec_name", "-of", "default=nw=1:nk=1", path]
    codec = subprocess.check_output(cmd).decode().strip()

    if codec == "av1":
        new_name = filename.replace(".mp4", "_fixed.mp4")
        new_path = os.path.join(MOVIE_DIR, new_name)
        print(f"⚙️ Converting {filename} (AV1) → {new_name} (H.264)...")
        subprocess.run([
            "ffmpeg", "-y", "-i", path,
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "18", "-preset", "medium", new_path
        ])
        print(f"✅ Converted: {new_name}")

print("\n🎬 Now running scene detection...")
subprocess.run(["python", "/indexer/scene_detector.py"])
