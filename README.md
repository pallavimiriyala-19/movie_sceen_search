✅ 1. Requirements
Install:
sudo apt update
sudo apt install -y docker.io docker-compose git

Ensure Docker is running:
sudo systemctl start docker


✅ 2. Clone the Repository
git clone https://github.com/pallavimiriyala-19/movie_sceen_search.git
cd movie_sceen_search


✅ 3. Prepare Required Folders
The following folders must exist before running the pipeline:
✔ Copy manually:


data/People → contains your actor/people images


data/movies → put at least one .mp4, .mkv, .avi, or .mov


Everything else (frames, faiss, scenes, db, exports) will be auto-created.
Fix permissions (important):
sudo chown -R $USER:$USER data


✅ 4. Start All Services
Run:
docker compose up -d --build

This starts:


highlevel_postgres (database)


highlevel_backend (API server)


highlevel_indexer (pipeline engine)


Wait ~5 seconds.

✅ 5. Initialize Database Schema
Run ONLY ONCE:
docker exec -it highlevel_indexer python3 /indexer/db_init.py

Expected output:
pgvector supported=True
created/verified tables
finished successfully

This ensures correct tables + columns matching the code.

✅ 6. Run the Full Pipeline ⭐ (One Command)
This processes everything:
docker exec -it highlevel_indexer python3 /indexer/run_all.py

Pipeline performs:


Import People


Build Actor Embeddings


Extract Movie Frames


Scene Detection (PySceneDetect)


Scene Attribute Extraction (YOLO, BLIP, embeddings)


Build FAISS Actor Index


Link Actors to Scenes


✅ 7. Resume From Any Step (Optional)
If something fails, resume from a specific stage:
Resume from scene detection:
docker exec -it highlevel_indexer python3 /indexer/run_all.py --from scenes

Resume from FAISS:
docker exec -it highlevel_indexer python3 /indexer/run_all.py --from faiss

Resume from actor linking:
docker exec -it highlevel_indexer python3 /indexer/run_all.py --from actor_linker


**if you want to run them manually fallow this** 
mkdir -p data/movies
mkdir -p data/frames
mkdir -p data/scenes
mkdir -p data/faiss
mkdir -p data/thumbs
mkdir -p data/exports
mkdir -p data/db
mkdir -p data/People
mkdir -p data/faces

sudo chown -R $USER:$USER data

1.  docker exec -it highlevel_indexer python3 /indexer/import_people.py
2.  docker exec -it highlevel_indexer python3 /indexer/extract_frames.py
3.  docker exec -it highlevel_indexer python3 /indexer/scene_detector.py
4.  docker exec -it highlevel_indexer python3 /indexer/scene_detector.py
5.  docker exec -it highlevel_indexer python3 /indexer/scene_attributes.py
6.  docker exec -it highlevel_indexer python3 /indexer/build_faiss_index.py
7.  docker exec -it highlevel_indexer python3 /indexer/scene_actor_linker.py



✅ 8. Using the Web Interface
Open:
http://localhost:8000

You can:


Search actors


Search scenes


Preview thumbnails


Query semantic embeddings


✅ 9 Run frontend

cd frontend
python3 -m http.server 8080




📁 Project Structure
movie_sceen_search/
 ├── backend/           → FastAPI backend
 ├── frontend/          → Simple HTML/JS UI
 ├── indexer/           → All pipeline scripts
 │   ├── run_all.py     → MAIN ENTRY POINT
 │   ├── db_init.py     → Creates DB schema safely
 ├── data/
 │   ├── People/        → Actor folders (👈 copy manually)
 │   ├── movies/        → Movie files (👈 copy manually)
 │   ├── frames/        → Auto-generated
 │   ├── scenes/        → Auto-generated
 │   ├── faiss/         → Auto-generated
 │   ├── db/            → Auto-generated
 └── docker-compose.yml


🧪 Testing Works Correctly
After pipeline finishes:
Check scenes table:
docker exec -it highlevel_postgres \
psql -U msuser -d moviesearch -c "SELECT COUNT(*) FROM scenes;"

Check actor embeddings:
docker exec -it highlevel_postgres \
psql -U msuser -d moviesearch -c "SELECT COUNT(*) FROM actor_faces;"


🎉 You’re Ready!
This setup guide ensures:


Database is always correct


No missing columns


No schema mismatches


No need to manually modify SQL


Entire pipeline runs using ONE command



If you want, I can generate:
✅ A company-ready PDF
✅ A diagram of the pipeline
✅ Architecture documentation
✅ API docs
Just tell me “Generate documentation pack”.
