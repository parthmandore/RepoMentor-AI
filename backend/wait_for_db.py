import time
import sys
import psycopg2
from app.core.config import settings

def wait_for_db():
    print("Waiting for Postgres database to accept connections...", flush=True)
    max_retries = 60
    retries = 0
    while retries < max_retries:
        try:
            # Connect directly using the DATABASE_URL connection URI
            conn = psycopg2.connect(settings.DATABASE_URL, connect_timeout=2)
            conn.close()
            print("Postgres database is ready!", flush=True)
            sys.exit(0)
        except psycopg2.OperationalError as e:
            retries += 1
            print(f"Database not ready yet (attempt {retries}/{max_retries}). Error: {e}", flush=True)
            time.sleep(1)
            
    print("Postgres database failed to start in time. Exiting.", flush=True)
    sys.exit(1)

if __name__ == "__main__":
    wait_for_db()
