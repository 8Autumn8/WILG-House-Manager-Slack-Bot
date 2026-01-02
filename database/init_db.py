import sqlite3
import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request, Response, jsonify
from slackeventsapi import SlackEventAdapter


env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)


def init_db(db_path="house_manager.db"):
    conn = sqlite3.connect(db_path)
    with open("schema.sql", "r") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print("✅ Local database created")

if __name__ == "__main__":
    init_db()