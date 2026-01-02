from database.db import get_db
from datetime import datetime


def get_expiring_assignments():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            a.assignment_id,
            a.user_id,
            j.job_name,
            a.due_at
        FROM active_assignments a
        JOIN jobs j ON a.job_id = j.job_id
        WHERE a.status = 'ASSIGNED'
          AND datetime(a.due_at, '+6 days') >= datetime('now', 'start of day')
          AND datetime(a.due_at, '+6 days') < datetime('now', 'start of day', '+1 day')
    """)

    expiring_jobs = cursor.fetchall()
    conn.close()
    return expiring_jobs


def expire_active_assignments():
    """
    Move expired assignments from active_assignments to inactive_jobs with status 'EXPIRED'.
    An assignment is expired if due_at + 6 days < today.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT assignment_id, user_id, job_id, due_at
        FROM active_assignments
        WHERE datetime(due_at, '+6 days') < datetime('now', 'start of day')
    """)
    expired_assignments = cursor.fetchall()

    for assignment_id, user_id, job_id, due_at in expired_assignments:
        cursor.execute("""
            INSERT OR REPLACE INTO inactive_jobs (
                assignment_id,
                user_id,
                job_id,
                due_at,
                status,
                moved_at
            )
            VALUES (?, ?, ?, ?, 'EXPIRED', CURRENT_TIMESTAMP)
        """, (assignment_id, user_id, job_id, due_at))

        cursor.execute("""
            DELETE FROM active_assignments
            WHERE assignment_id = ?
        """, (assignment_id,))

    conn.commit()
    conn.close()


def get_active_assignments(slack_user_id):
    conn = get_db()
    cursor = conn.cursor()

    # Look up the numeric user_id
    cursor.execute("SELECT user_id FROM users WHERE slack_user_id = ?", (slack_user_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return []  # Slack ID not found
    user_id = row[0]

    # Fetch assignments
    cursor.execute("""
        SELECT
            a.assignment_id,
            j.job_name,
            a.due_at,
            a.user_id,
            a.status
        FROM active_assignments a
        JOIN jobs j ON a.job_id = j.job_id
        WHERE a.user_id = ?
        ORDER BY a.due_at ASC
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()

    # Return as list of dicts
    return [
        {
            "assignment_id": r[0],
            "job_name": r[1],
            "due_at": r[2],
            "user_id": r[3],
            "status": r[4]
        }
        for r in rows
    ]

