from database.db import get_db

def db_expire_makeup_jobs():
    """
    Move expired makeup jobs to inactive_jobs with status 'EXPIRED',
    then remove them from makeup_jobs. The assignment may not exist
    in active_assignments since it has already been given up.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Select expired makeup jobs
    cursor.execute("""
        SELECT original_assignment_id, job_id, due_at
        FROM makeup_jobs
        WHERE datetime(due_at) < datetime('now')
    """)
    expired_makeups = cursor.fetchall()

    for original_assignment_id, job_id, due_at in expired_makeups:
        # Move to inactive_jobs
        cursor.execute("""
            INSERT OR REPLACE INTO inactive_jobs (
                assignment_id, slack_user_id, job_id, due_at, status, moved_at
            )
            VALUES (?, NULL, ?, ?, 'EXPIRED', CURRENT_TIMESTAMP)
        """, (original_assignment_id, job_id, due_at))

        # Remove from makeup_jobs
        cursor.execute("""
            DELETE FROM makeup_jobs
            WHERE original_assignment_id = ? AND job_id = ?
        """, (original_assignment_id, job_id))

    conn.commit()
    conn.close()



def giveup_makeup_job(user_id, assignment_id):
    """
    User gives up a job for makeup. Remove the assignment from active_assignments
    and add an entry to makeup_jobs. The database trigger prevents late submissions.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Fetch job_id and due_at for the assignment
    cursor.execute("""
        SELECT job_id, due_at
        FROM active_assignments
        WHERE assignment_id = ? AND slack_user_id = ?
    """, (assignment_id, user_id))
    assignment = cursor.fetchone()

    if not assignment:
        conn.close()
        raise ValueError("Assignment not found or already taken by another user.")

    job_id, due_at = assignment

    # Insert into makeup_jobs
    cursor.execute("""
        INSERT INTO makeup_jobs (original_assignment_id, job_id, due_at, created_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    """, (assignment_id, job_id, due_at))

    # Remove from active_assignments
    cursor.execute("""
        DELETE FROM active_assignments
        WHERE assignment_id = ? AND slack_user_id = ?
    """, (assignment_id, user_id))

    conn.commit()
    conn.close()

def claim_makeup_job(user_id, makeup_job_id):
    """
    User claims a makeup job. Remove the entry from makeup_jobs and add
    a new assignment to active_assignments for the user.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Fetch makeup job details
    cursor.execute("""
        SELECT original_assignment_id, job_id, due_at
        FROM makeup_jobs
        WHERE id = ?
    """, (makeup_job_id,))
    makeup_job = cursor.fetchone()

    if not makeup_job:
        conn.close()
        raise ValueError("Makeup job not found.")

    original_assignment_id, job_id, due_at = makeup_job

    # Insert into active_assignments
    cursor.execute("""
        INSERT INTO active_assignments (slack_user_id, job_id, due_at)
        VALUES (?, ?, ?)
    """, (user_id, job_id, due_at))

    # Remove from makeup_jobs
    cursor.execute("""
        DELETE FROM makeup_jobs
        WHERE id = ?
    """, (makeup_job_id,))

    conn.commit()
    conn.close()