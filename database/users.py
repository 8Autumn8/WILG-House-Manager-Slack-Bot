from database.db import get_db

def get_all_user_hours():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT username, hours_completed, hours_needed, missed_jobs  FROM users")
    rows = cursor.fetchall()
    conn.close()

    # Optional: return as list of dicts
    return [
        {"username": row[0], "hours_completed": row[1], "hours_needed": row[2], "missed_jobs": row[3]}
        for row in rows
    ]
