import os
import json
import psycopg2

DB_URL = os.getenv("DATABASE_URL", "postgresql://msuser:mssecret@postgres/moviesearch")
PEOPLE_DIR = "/data/People"

def get_conn():
    return psycopg2.connect(DB_URL)

def restore_actors():
    conn = get_conn()
    cur = conn.cursor()

    total_inserted = 0
    total_skipped = 0

    # Loop A, B, C... folders
    for letter in sorted(os.listdir(PEOPLE_DIR)):
        letter_path = os.path.join(PEOPLE_DIR, letter)
        if not os.path.isdir(letter_path):
            continue

        # Loop Actor folders
        for actor_folder in sorted(os.listdir(letter_path)):
            actor_path = os.path.join(letter_path, actor_folder)
            if not os.path.isdir(actor_path):
                continue

            # Find JSON file inside actor folder
            json_files = [f for f in os.listdir(actor_path) if f.lower().endswith(".json")]
            if not json_files:
                continue

            json_path = os.path.join(actor_path, json_files[0])

            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"❌ Failed reading {json_path}: {e}")
                continue

            name = data.get("Name") or data.get("name") or actor_folder
            jellyfin_id = data.get("Id") or data.get("id")
            aliases = data.get("Aliases") or data.get("aliases") or []

            if not name:
                continue

            # Check if already exists
            if jellyfin_id:
                cur.execute("SELECT actor_id FROM actors WHERE jellyfin_person_id = %s LIMIT 1;", (jellyfin_id,))
                found = cur.fetchone()
            else:
                cur.execute("SELECT actor_id FROM actors WHERE name = %s LIMIT 1;", (name,))
                found = cur.fetchone()

            if found:
                total_skipped += 1
                continue

            # Insert actor
            try:
                cur.execute(
                    """
                    INSERT INTO actors (name, aliases, jellyfin_person_id)
                    VALUES (%s, %s, %s)
                    RETURNING actor_id;
                    """,
                    (name, aliases, jellyfin_id),
                )
                new_id = cur.fetchone()[0]
                conn.commit()
                print(f"✅ Inserted: {name} (id={new_id})")
                total_inserted += 1

            except Exception as e:
                conn.rollback()
                print(f"❌ Failed inserting {name}: {e}")

    conn.close()
    print(f"\n🎉 Completed! Inserted={total_inserted}, Skipped={total_skipped}")

if __name__ == "__main__":
    restore_actors()
