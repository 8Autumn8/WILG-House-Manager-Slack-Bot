
from database.db import get_db

def get_all_user_hours():
    conn = get_db()
    cursor = conn.execute("SELECT username, hours_completed, hours_needed FROM users")
    return cursor.fetchall()