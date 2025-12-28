import sqlite3
import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request, Response, jsonify
from slackeventsapi import SlackEventAdapter
from database.db import get_db

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)


def init_db():
    conn = get_db()
    with open("schema.sql") as f:
        conn.executescript(f.read())
    conn.close()
    print("✅ Local database created")

if __name__ == "__main__":
    init_db()