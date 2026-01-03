from database.db import execute_query, get_job_id, get_user_id

# ---------- User Helpers ----------

def get_user_name_by_id(user_id: int) -> str:
    """Return the username for a given user_id, or 'Unknown User' if not found."""
    rows = execute_query(
        "users",
        "select",
        filters=[("user_id", "eq", user_id)]
    )
    return rows[0]["username"] if rows else "Unknown User"

def get_job_name_from_job_id(job_id):
    rows = execute_query(
        "jobs",
        "select",
        filters=[("job_id", "eq", job_id)]
    )
    return rows[0]["job_name"] if rows else "Unkown Job"

# ---------- Submissions ----------

def add_to_submission_table(
    slack_user_id: str,
    job_hours: float,
    assignment_id: int,
    date_of_completion,
    submission_time,
    witness_slack_user_id: str | None = None,
    comments: str | None = None,
    channel_id: str | None = None
) -> tuple[int | None, str, str | None, str | None]:
    """
    Add a job submission to Supabase.
    Returns: (submission_id, user_name, job_name, witness_name)
    """
    user_id = get_user_id(slack_user_id)
    witness_user_id = get_user_id(witness_slack_user_id) if witness_slack_user_id else None

    if user_id is None:
        raise ValueError("Submitting user not found")

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
    job_name = get_job_id(assignment_id)
    witness_name = get_user_name_by_id(witness_user_id) if witness_user_id else None

    return submission_id, user_name, job_name, witness_name


# ---------- Queries ----------

def get_all_submissions_and_approved_hours(slack_user_id: str | None = None) -> tuple[list[dict], float]:
    """
    Fetch all submissions for a user (or all users if None) and calculate total approved hours.
    Each submission will include the job_name.
    """
    filters = []
    if slack_user_id:
        user_id = get_user_id(slack_user_id)
        if user_id:
            filters.append(("user_id", "eq", user_id))

    submissions = execute_query("job_submissions", "select", filters=filters)

    approved_hours = 0
    
    for submission in submissions:
        job_id = get_job_id(submission["assignment_id"])
        submission["job_name"] = get_job_name_from_job_id(job_id) or "Unknown"
        if submission.get("approved") == "APPROVED":
            approved_hours += submission.get("job_hours", 0) or 0

    return submissions, approved_hours


# ---------- Approval / Rejection ----------

def reject_jobs_in_db(rejected_ids: list[int]):
    """Mark the specified submissions as REJECTED."""
    if not rejected_ids:
        return
    for submission_id in rejected_ids:
        execute_query(
            "job_submissions",
            "update",
            data={"approved": "REJECTED"},
            filters=[("submission_id", "eq", submission_id)]
        )


def approve_jobs_in_db(approved_ids: list[int]):
    """Mark the specified submissions as APPROVED."""
    if not approved_ids:
        return
    for submission_id in approved_ids:
        print("Approving submission ID:", submission_id)
        execute_query(
            "job_submissions",
            "update",
            data={"approved": "APPROVED"},
            filters=[("submission_id", "eq", submission_id)]
        )
