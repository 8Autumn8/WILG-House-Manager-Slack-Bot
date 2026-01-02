from db import get_db
import sqlite3

def add_user(slack_user_id, username):
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO users (slack_user_id, username)
            VALUES (?, ?)
            """,
            (slack_user_id, username)
        )
        conn.commit()
        print(f"User '{username}' added successfully.")
    except sqlite3.IntegrityError:
        # slack_user_id already exists (UNIQUE constraint)
        print(f"User '{username}' already exists or Slack ID already registered, skipping.")
    finally:
        conn.close()


add_user(slack_user_id="U0A4V8PLXFC", username="v.belinda.k")
