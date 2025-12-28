from database.db import get_db

def get_user_name(conn, slack_user_id):
    cursor = conn.execute("SELECT username FROM users WHERE slack_user_id = ?", (slack_user_id,))
    row = cursor.fetchone()
    return row[0] if row else "Unknown User"

def get_job_name(conn, job_id):
    cursor = conn.execute("SELECT job_name FROM jobs WHERE job_id = ?", (job_id,))
    row = cursor.fetchone()
    return row[0] if row else "Unknown Job"



def get_job_name_from_assignment_id(conn, assignment_id):
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT j.job_name
        FROM active_assignments a
        JOIN jobs j ON a.job_id = j.job_id
        WHERE a.assignment_id = ?
        """,
        (assignment_id,)
    )

    row = cursor.fetchone()

    return row[0] if row else None

def add_to_submission_table(    
    slack_user_id,
    job_hours,
    assignment_id,
    date_of_completion,
    submission_time,
    witness_slack_user_id,
    comments,
    channel_id
):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO job_submissions
        (slack_user_id, job_hours, assignment_id, date_of_completion, submission_time, witness_slack_user_id, comments)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (slack_user_id, job_hours, assignment_id, date_of_completion, submission_time, witness_slack_user_id, comments)
    )
    conn.commit()
    submission_id = cursor.lastrowid

    # Lookup names
    user_name = get_user_name(conn, slack_user_id)
    job_name = get_job_name_from_assignment_id(conn, assignment_id)
    witness_name = get_user_name(conn, witness_slack_user_id)
    conn.close()
    return submission_id, user_name, job_name, witness_name

def get_all_submissions_and_approved_hours(slack_user_id=None):
    conn = get_db()
    cursor = conn.cursor()

    params = []
    user_filter = ""

    if slack_user_id:
        user_filter = "WHERE slack_user_id = ?"
        params.append(slack_user_id)

    # 1️⃣ Get ALL submissions (approved + pending + rejected)
    cursor.execute(
        f"""
        SELECT
            js.submission_id,
            j.job_name,
            js.job_hours,
            js.approved,
            js.submission_time
        FROM job_submissions js
        JOIN jobs j ON js.job_id = j.job_id
        {user_filter}
        ORDER BY js.submission_time DESC
        """,
        params
    )

    submissions = [dict(row) for row in cursor.fetchall()]
    #print(submissions)

    # 2️⃣ Sum ONLY approved hours
    cursor.execute(
        f"""
        SELECT COALESCE(SUM(job_hours), 0)
        FROM job_submissions
        WHERE approved = 'APPROVED'
        { "AND slack_user_id = ?" if slack_user_id else "" }
        """,
        params
    )

    approved_hours = cursor.fetchone()[0]

    conn.close()
    return submissions, approved_hours

def reject_jos_in_db(rejected_ids):
    if not rejected_ids:
        return

    conn = get_db()
    cursor = conn.cursor()

    query = f"""
    UPDATE job_submissions
    SET approved = 'REJECTED'
    WHERE submission_id IN ({','.join(['?']*len(rejected_ids))})
    """

    cursor.execute(query, rejected_ids)
    conn.commit()
    conn.close()
    return

def approve_jobs_in_db(approved_ids):
    if not approved_ids:
        return

    conn = get_db()
    cursor = conn.cursor()

    query = f"""
    UPDATE job_submissions
    SET approved = 'APPROVED'
    WHERE submission_id IN ({','.join(['?']*len(approved_ids))})
    """

    cursor.execute(query, approved_ids)
    conn.commit()
    conn.close()
    return