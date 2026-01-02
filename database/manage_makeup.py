from database.db import get_db
from datetime import datetime, timedelta


def db_expire_makeup_jobs():
    """
    Move expired makeup jobs to inactive_jobs with status 'EXPIRED',
    then remove them from makeup_jobs.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT original_assignment_id, job_id, due_at
        FROM makeup_jobs
        WHERE datetime(due_at) < datetime('now')
    """)
    expired_makeups = cursor.fetchall()

    for assignment_id, job_id, due_at in expired_makeups:
        cursor.execute("""
            INSERT OR REPLACE INTO inactive_jobs (
                assignment_id,
                user_id,
                job_id,
                due_at,
                status,
                moved_at
            )
            VALUES (?, NULL, ?, ?, 'EXPIRED', CURRENT_TIMESTAMP)
        """, (assignment_id, job_id, due_at))

        cursor.execute("""
            DELETE FROM makeup_jobs
            WHERE original_assignment_id = ?
        """, (assignment_id,))

    conn.commit()
    conn.close()


def giveup_makeup_job(slack_user_id, assignment_id):
    """
    User gives up a job for makeup.
    Accepts Slack user ID and converts to internal user_id.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Lookup numeric user_id
    cursor.execute("SELECT user_id FROM users WHERE slack_user_id = ?", (slack_user_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError("Slack user ID not found.")
    user_id = row[0]

    # Fetch assignment + job metadata
    cursor.execute("""
        SELECT 
            a.job_id,
            a.due_at,
            j.job_name,
            j.job_description
        FROM active_assignments a
        JOIN jobs j ON j.job_id = a.job_id
        WHERE a.assignment_id = ? AND a.user_id = ?
    """, (assignment_id, user_id))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError("Assignment not found or already removed.")

    job_id, due_at, job_name, job_description = row

    # Determine lateness
    is_late_makeup = datetime.utcnow() > (
        datetime.fromisoformat(due_at) - timedelta(hours=24)
    )

    if is_late_makeup:
        cursor.execute("""
            INSERT INTO makeup_jobs (
                original_assignment_id,
                job_id,
                prev_user_id,
                due_at,
                created_at
            )
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (assignment_id, job_id, user_id, due_at))
    else:
        cursor.execute("""
            INSERT INTO makeup_jobs (
                original_assignment_id,
                job_id,
                due_at,
                created_at
            )
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (assignment_id, job_id, due_at))

    # Remove from active_assignments
    cursor.execute("""
        DELETE FROM active_assignments
        WHERE assignment_id = ? AND user_id = ?
    """, (assignment_id, user_id))

    conn.commit()
    conn.close()

    return {
        "assignment_id": assignment_id,
        "job_id": job_id,
        "job_name": job_name,
        "job_description": job_description,
        "due_at": due_at,
        "is_late_makeup": is_late_makeup
    }


def claim_makeup_job(slack_user_id, assignment_id):
    """
    User claims a makeup job.
    Accepts Slack user ID and converts to internal user_id.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Lookup numeric user_id
    cursor.execute("SELECT user_id FROM users WHERE slack_user_id = ?", (slack_user_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError("Slack user ID not found.")
    user_id = row[0]

    # Fetch makeup job details
    cursor.execute("""
        SELECT 
            m.original_assignment_id,
            m.job_id,
            j.job_name,
            m.due_at
        FROM makeup_jobs m
        JOIN jobs j ON j.job_id = m.job_id
        WHERE m.original_assignment_id = ?
    """, (assignment_id,))
    makeup_job = cursor.fetchone()
    if not makeup_job:
        conn.close()
        raise ValueError("Makeup job not found.")

    assignment_id, job_id, job_name, due_at = makeup_job

    # Insert into active_assignments
    cursor.execute("""
        INSERT INTO active_assignments (
            assignment_id,
            user_id,
            job_id,
            due_at,
            status
        )
        VALUES (?, ?, ?, ?, 'ASSIGNED')
    """, (assignment_id, user_id, job_id, due_at))

    # Remove from makeup_jobs
    cursor.execute("""
        DELETE FROM makeup_jobs
        WHERE original_assignment_id = ?
    """, (assignment_id,))

    conn.commit()
    conn.close()

    return {
        "result": "Makeup job claimed successfully.",
        "job_name": job_name
    }



def db_see_makeup_jobs():
    """
    Retrieve all makeup jobs currently available.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            m.original_assignment_id,
            m.job_id,
            j.job_name,
            j.job_description,
            m.due_at,
            m.created_at
        FROM makeup_jobs m
        JOIN jobs j ON j.job_id = m.job_id
        ORDER BY m.created_at ASC
    """)
    makeup_jobs = cursor.fetchall()
    conn.close()

    return [
        {
            "original_assignment_id": assignment_id,
            "job_id": job_id,
            "job_name": job_name,
            "job_description": job_description,
            "due_at": due_at,
            "created_at": created_at
        }
        for assignment_id, job_id, job_name, job_description, due_at, created_at
        in makeup_jobs
    ]
