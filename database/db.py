import sqlite3
import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

def get_db():
    conn = sqlite3.connect(os.getenv("DB_PATH"))
    conn.row_factory = sqlite3.Row 
    return conn