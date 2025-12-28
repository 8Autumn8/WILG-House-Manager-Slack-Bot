

from database.db import get_db
from datetime import datetime, timedelta


def get_expiring_assignments():
    conn = get_db()
    cursor = conn.cursor()

    # Find jobs expiring today
    today = datetime.now().date()
    today_str = today.strftime("%Y-%m-%d")

    cursor.execute("""
        SELECT
            a.assignment_id,
            a.slack_user_id,
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

    # Select expired assignments
    cursor.execute("""
        SELECT assignment_id, slack_user_id, job_id, due_at, status
        FROM active_assignments
        WHERE datetime(due_at, '+6 days') < datetime('now', 'start of day')
    """)
    expired_assignments = cursor.fetchall()

    for assignment_id, slack_user_id, job_id, due_at, status in expired_assignments:

        # Move to inactive_jobs as EXPIRED
        cursor.execute("""
            INSERT OR REPLACE INTO inactive_jobs (
                assignment_id, slack_user_id, job_id, due_at, status, moved_at
            ) VALUES (?, ?, ?, ?, 'EXPIRED', CURRENT_TIMESTAMP)
        """, (assignment_id, slack_user_id, job_id, due_at))

        # Remove from active_assignments
        cursor.execute("""
            DELETE FROM active_assignments
            WHERE assignment_id = ?
        """, (assignment_id,))

    conn.commit()
    conn.close()


def get_active_assignments(user_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            a.assignment_id,
            j.job_name,
            a.due_at,
            a.slack_user_id,
            a.status
        FROM active_assignments a
        JOIN jobs j ON a.job_id = j.job_id
        WHERE a.slack_user_id = ?
        ORDER BY a.due_at ASC
    """, (user_id,))

    active_assignments = cursor.fetchall()
    conn.close()
    return active_assignments