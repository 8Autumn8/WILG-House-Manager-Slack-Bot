import sqlite3
import os
from pathlib import Path
from dotenv import load_dotenv
from database.init_db import init_db

# Load environment variables
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

# Use Render persistent storage
db_dir = os.getenv("RENDER_DATA_DIR", ".")
os.makedirs(db_dir, exist_ok=True)  # ensure folder exists
DB_PATH = os.path.join(db_dir, "house_manager.db")

# Initialize DB if it doesn't exist
if not os.path.exists(DB_PATH):
    print(f"Initializing DB at {DB_PATH}")
    init_db(DB_PATH)
else:
    print(f"DB already exists at {DB_PATH}")

# Get SQLite connection
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")  # allow concurrent reads/writes
    return conn
