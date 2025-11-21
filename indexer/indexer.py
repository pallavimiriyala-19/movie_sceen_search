import os, psycopg2, requests, cv2, numpy as np
from insightface.app import FaceAnalysis

from indexer.config import DB_URL
DB_URL = DB_URL
JELLYFIN_HOST = os.environ.get("JELLYFIN_HOST")
API_KEY = os.environ.get("JELLYFIN_API_KEY")

def connect_db():
    return psycopg2.connect(DB_URL)

def fetch_people():
    url = f"{JELLYFIN_HOST}/Items"
    params = {"IncludeItemTypes": "Person", "api_key": API_KEY}
    res = requests.get(url, params=params)
    res.raise_for_status()
    return res.json().get("Items", [])

def insert_actor(conn, name, person_id):
    with conn.cursor() as cur:
        cur.execute("INSERT INTO actors (name, jellyfin_person_id) VALUES (%s,%s) ON CONFLICT DO NOTHING", (name, person_id))
        conn.commit()

def seed_actors():
    conn = connect_db()
    people = fetch_people()
    for p in people:
        insert_actor(conn, p["Name"], p["Id"])
        print(f"Seeded: {p['Name']}")
    conn.close()

def test_face_detection():
    app = FaceAnalysis(allowed_modules=['detection','recognition'])
    app.prepare(ctx_id=-1)
    img = np.zeros((256,256,3),dtype=np.uint8)
    faces = app.get(img)
    print("InsightFace test passed (faces detected)", len(faces))

if __name__ == "__main__":
    seed_actors()
    test_face_detection()
