from database.db import get_db
import sqlite3
from datetime import datetime, timedelta
from services.formatters import parse_date

FREQUENCY_CONFIG = {
    "DAILY": {"count": 14, "delta": timedelta(days=1)},
    "WEEKLY": {"count": 14, "delta": timedelta(weeks=1)},
    "BIWEEKLY": {"count": 28, "delta": timedelta(weeks=2)},
}



def add_job_assignments_to_db(assignments, start_date):
    if isinstance(start_date, str):
        start_date = datetime.strptime(parse_date(start_date), "%Y-%m-%d",)

    conn = get_db()
    cursor = conn.cursor()

    for assignment in assignments:
        print(assignment)
        job_name = assignment["Job Name"]
        username = assignment["Name"]

        # Get job_id + job_type
        cursor.execute(
            "SELECT job_id, job_type FROM jobs WHERE job_name = ?",
            (job_name,)
        )
        job_row = cursor.fetchone()
        if not job_row:
            print(f"Job '{job_name}' not found, skipping assignment.")
            continue

        job_id, job_type = job_row
        job_type = job_type.upper()

        if job_type not in FREQUENCY_CONFIG:
            print(f"Job type '{job_type}' for job '{job_name}' is invalid, skipping assignment.")
            continue

        # Get slack_user_id
        cursor.execute(
            "SELECT slack_user_id FROM users WHERE username = ?",
            (username,)
        )
        user_row = cursor.fetchone()
        if not user_row:
            print(f"User '{username}' not found, skipping assignment.")
            continue

        slack_user_id = user_row[0]

        config = FREQUENCY_CONFIG[job_type]
        due_at = start_date

        for _ in range(config["count"]):
            cursor.execute(
                """
                INSERT INTO active_assignments (
                    slack_user_id,
                    job_id,
                    due_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    slack_user_id,
                    job_id,
                    due_at.isoformat()
                )
            )
            due_at += config["delta"]

    conn.commit()
    conn.close()
