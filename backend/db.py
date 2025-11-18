import os
import psycopg2
import psycopg2.extras

DB_URL = os.getenv("DATABASE_URL", "postgresql://msuser:mssecret@postgres/moviesearch")

def get_conn():
    return psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
