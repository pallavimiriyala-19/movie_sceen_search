print("🚀 Starting Full Movie Indexing Pipeline...")


# Import each module’s run() function

from scene_detector import run as run_scene_detector
from extract_frames import run as run_extract_frames
from scene_actor_linker import run as run_actor_linker
from build_faiss_index import run as run_actor_faiss
from build_scenes_faiss import run as run_scene_faiss
from scene_attributes import run as run_scene_attributes
    


# MASTER PIPELINE
def main():

    print(" 1 Running Scene Detector")
    run_scene_detector()

    print(" 2 Extracting Frames")
    run_extract_frames()

    print(" 3 Linking Actors to Scenes")
    run_actor_linker()

    print(" 4  Extracting Scene Attributes")
    run_scene_attributes()
 

    print(" 5 Building Actor FAISS Index")
    run_actor_faiss()

   
    print(" 6  Building Scene FAISS Index")
  
    run_scene_faiss()

    print("\n🎉 ALL STEPS COMPLETED SUCCESSFULLY!")
   



# Standalone execution

if __name__ == "__main__":
    main()



#command to run this script inside docker
#docker exec -it highlevel_indexer python3 /indexer/run_all.py
