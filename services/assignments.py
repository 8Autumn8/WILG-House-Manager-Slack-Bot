from database.db import get_db
from database.manage_assigments import get_active_assignments, expire_active_assignments


def create_user_ids(spreadsheet_url):
    return

def generate_user_table(user_tuples):
    conn = get_db()
    for name, user_id in user_tuples:
        conn.execute(
            """
            INSERT INTO users (username, slack_user_id)
            VALUES (?, ?)
            ON CONFLICT(slack_user_id)
            DO UPDATE SET username = excluded.username
            """,
            (name, user_id)
        )
    conn.commit()
    conn.close()


def expire_assignments():
    expire_active_assignments()

def get_user_assignments(user_id):

    return get_active_assignments(user_id)