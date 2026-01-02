from database.db import execute_query

# ---------- Helpers ----------

def get_user_id(slack_user_id):
    """Return the user_id for a given Slack ID, or None."""
    rows = execute_query(
        "users",
        "select",
        filters=[("slack_user_id", "eq", slack_user_id)]
    )
    return rows[0]["user_id"] if rows else None


def get_user_name_by_id(user_id):
    """Return the username for a given user_id, or 'Unknown User'."""
    rows = execute_query(
        "users",
        "select",
        filters=[("user_id", "eq", user_id)]
    )
    return rows[0]["username"] if rows else "Unknown User"


def get_job_name_from_assignment_id(assignment_id):
    """Return the job_name for a given assignment_id."""
    query = """
        SELECT j.job_name
        FROM active_assignments a
        JOIN jobs j ON a.job_id = j.job_id
        WHERE a.assignment_id = %s
    """
    # Supabase API does not support raw joins easily; we'll query active_assignments first
    assignment_rows = execute_query(
        "active_assignments",
        "select",
        filters=[("assignment_id", "eq", assignment_id)]
    )
    if not assignment_rows:
        return None

    job_id = assignment_rows[0]["job_id"]
    job_rows = execute_query(
        "jobs",
        "select",
        filters=[("job_id", "eq", job_id)]
    )
    return job_rows[0]["job_name"] if job_rows else None


# ---------- Submissions ----------

def add_to_submission_table(
    slack_user_id,
    job_hours,
    assignment_id,
    date_of_completion,
    submission_time,
    witness_slack_user_id=None,
    comments=None,
    channel_id=None  # kept for compatibility
):
    """Add a job submission to Supabase."""
    user_id = get_user_id(slack_user_id)
    witness_user_id = get_user_id(witness_slack_user_id) if witness_slack_user_id else None

    if user_id is None:
        raise ValueError("Submitting user not found")

    # Insert submission
    data = {
        "user_id": user_id,
        "assignment_id": assignment_id,
        "job_hours": job_hours,
        "date_of_completion": date_of_completion,
        "submission_time": submission_time,
        "witness_user_id": witness_user_id,
        "comments": comments,
        "approved": None
    }
    inserted = execute_query("job_submissions", "insert", data=data)
    submission_id = inserted[0]["submission_id"] if inserted else None

    user_name = get_user_name_by_id(user_id)
    job_name = get_job_name_from_assignment_id(assignment_id)
    witness_name = get_user_name_by_id(witness_user_id) if witness_user_id else None

    return submission_id, user_name, job_name, witness_name


# ---------- Queries ----------

def get_all_submissions_and_approved_hours(slack_user_id=None):
    """Return submissions and total approved hours."""
    filters = []
    user_id = None

    if slack_user_id:
        user_id = get_user_id(slack_user_id)
        if user_id:
            filters.append(("user_id", "eq", user_id))

    submissions = execute_query("job_submissions", "select", filters=filters)

    # Calculate approved hours
    approved_rows = execute_query(
        "job_submissions",
        "select",
        filters=[("approved", "eq", "APPROVED")] + (filters if user_id else [])
    )
    approved_hours = sum(r["job_hours"] for r in approved_rows) if approved_rows else 0

    return submissions, approved_hours


# ---------- Approval / Rejection ----------

def reject_jobs_in_db(rejected_ids):
    """Mark submissions as REJECTED."""
    if not rejected_ids:
        return

    for submission_id in rejected_ids:
        execute_query(
            "job_submissions",
            "update",
            data={"approved": "REJECTED"},
            filters=[("submission_id", "eq", submission_id)]
        )


def approve_jobs_in_db(approved_ids):
    """Mark submissions as APPROVED."""
    if not approved_ids:
        return

    for submission_id in approved_ids:
        execute_query(
            "job_submissions",
            "update",
            data={"approved": "APPROVED"},
            filters=[("submission_id", "eq", submission_id)]
        )
