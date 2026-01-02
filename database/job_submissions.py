from database.db import get_db


# ---------- Helpers ----------

def get_user_id(conn, slack_user_id):
    row = conn.execute(
        "SELECT user_id FROM users WHERE slack_user_id = ?",
        (slack_user_id,)
    ).fetchone()
    return row[0] if row else None


def get_user_name_by_id(conn, user_id):
    row = conn.execute(
        "SELECT username FROM users WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    return row[0] if row else "Unknown User"


def get_job_name_from_assignment_id(conn, assignment_id):
    row = conn.execute(
        """
        SELECT j.job_name
        FROM active_assignments a
        JOIN jobs j ON a.job_id = j.job_id
        WHERE a.assignment_id = ?
        """,
        (assignment_id,)
    ).fetchone()

    return row[0] if row else None


# ---------- Submissions ----------

def add_to_submission_table(
    slack_user_id,
    job_hours,
    assignment_id,
    date_of_completion,
    submission_time,
    witness_slack_user_id,
    comments,
    channel_id  # unused but kept for compatibility
):
    conn = get_db()
    cursor = conn.cursor()

    user_id = get_user_id(conn, slack_user_id)
    witness_user_id = get_user_id(conn, witness_slack_user_id)

    if user_id is None:
        conn.close()
        raise ValueError("Submitting user not found")

    cursor.execute(
        """
        INSERT INTO job_submissions
        (user_id, assignment_id, job_hours, date_of_completion, submission_time, witness_user_id, comments)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            assignment_id,
            job_hours,
            date_of_completion,
            submission_time,
            witness_user_id,
            comments
        )
    )

    conn.commit()
    submission_id = cursor.lastrowid

    user_name = get_user_name_by_id(conn, user_id)
    job_name = get_job_name_from_assignment_id(conn, assignment_id)
    witness_name = (
        get_user_name_by_id(conn, witness_user_id)
        if witness_user_id else None
    )

    conn.close()
    return submission_id, user_name, job_name, witness_name


# ---------- Queries ----------

def get_all_submissions_and_approved_hours(slack_user_id=None):
    conn = get_db()
    cursor = conn.cursor()

    params = []
    user_filter = ""

    if slack_user_id:
        user_id = get_user_id(conn, slack_user_id)
        user_filter = "WHERE js.user_id = ?"
        params.append(user_id)

    cursor.execute(
        f"""
        SELECT
            js.submission_id,
            j.job_name,
            js.job_hours,
            js.approved,
            js.submission_time
        FROM job_submissions js
        LEFT JOIN active_assignments a
            ON a.assignment_id = js.assignment_id
        LEFT JOIN inactive_jobs i
            ON i.assignment_id = js.assignment_id
        LEFT JOIN completed_job_history h
            ON h.assignment_id = js.assignment_id
        JOIN jobs j
            ON j.job_id = COALESCE(a.job_id, i.job_id, h.job_id)
        {user_filter}
        ORDER BY js.submission_time DESC
        """,
        params
    )

    submissions = [dict(row) for row in cursor.fetchall()]

    sum_query = """
        SELECT COALESCE(SUM(job_hours), 0)
        FROM job_submissions
        WHERE approved = 'APPROVED'
    """
    sum_params = []

    if slack_user_id:
        sum_query += " AND user_id = ?"
        sum_params.append(user_id)

    cursor.execute(sum_query, sum_params)
    approved_hours = cursor.fetchone()[0]

    conn.close()
    return submissions, approved_hours


# ---------- Approval / Rejection ----------

def reject_jobs_in_db(rejected_ids):
    if not rejected_ids:
        return

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        f"""
        UPDATE job_submissions
        SET approved = 'REJECTED'
        WHERE submission_id IN ({','.join(['?'] * len(rejected_ids))})
        """,
        rejected_ids
    )

    conn.commit()
    conn.close()


def approve_jobs_in_db(approved_ids):
    print(approved_ids)
    if not approved_ids:
        return

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        f"""
        UPDATE job_submissions
        SET approved = 'APPROVED'
        WHERE submission_id IN ({','.join(['?'] * len(approved_ids))})
        """,
        approved_ids
    )

    conn.commit()
    conn.close()
