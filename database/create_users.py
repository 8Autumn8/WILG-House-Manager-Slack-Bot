from db import get_db
import sqlite3

def add_user(user_id, user_name):
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO users (slack_user_id, username) VALUES (?, ?)", (user_id, user_name))
        conn.commit()
        print(f"User '{user_name}' added successfully.")
    except sqlite3.IntegrityError:
        # user_name already exists
        print(f"User '{user_name}' already exists, skipping.")

    conn.close()

add_user(user_id="U0A4V8PLXFC", user_name="v.belinda.k")