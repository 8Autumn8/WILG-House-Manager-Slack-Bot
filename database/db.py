import sqlite3
import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
DB_URL = os.getenv("DB_URL")

def get_db():
    conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
    #conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn