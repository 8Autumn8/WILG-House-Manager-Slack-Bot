import sqlite3
import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request, Response, jsonify
from slackeventsapi import SlackEventAdapter


#env_path = Path('.') / '.env'
load_dotenv()

schema_path = os.path.join(os.path.dirname(__file__), "..", "schema.sql")
schema_path = os.path.abspath(schema_path)

def init_db(db_path="data/house_manager.db"):
    conn = sqlite3.connect(db_path)
    with open(schema_path, "r") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print("✅ Local database created")

if __name__ == "__main__":
    init_db()