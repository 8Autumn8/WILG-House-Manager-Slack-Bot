from datetime import datetime, timedelta
from database.db import execute_query, get_user_id

# ---------- Expiring Assignments ----------

def get_expiring_assignments(days_before_expire: int = 6) -> list[dict]:
    """
    Return active assignments that will expire in `days_before_expire` days from today.
    Each dict includes assignment_id, user_id, job_name, and due_at.
    """
    all_assignments = execute_query(
        "active_assignments",
        "select",
        filters=[("status", "eq", "ASSIGNED")]
    )

    today = datetime.utcnow().date()
    expiring_jobs = []

    for assignment in all_assignments:
        due_date = datetime.fromisoformat(assignment["due_at"]).date()
        if due_date + timedelta(days=days_before_expire) == today:
            # Fetch job_name
            job_rows = execute_query(
                "jobs",
                "select",
                filters=[("job_id", "eq", assignment["job_id"])]
            )
            job_name = job_rows[0]["job_name"] if job_rows else "Unknown Job"

            expiring_jobs.append({
                "assignment_id": assignment["assignment_id"],
                "user_id": assignment["user_id"],
                "job_name": job_name,
                "due_at": assignment["due_at"]
            })

    return expiring_jobs


# ---------- Expire Assignments ----------

def expire_active_assignments(expire_after_days: int = 6):
    """
    Move expired assignments from active_assignments to inactive_jobs with status 'EXPIRED'.
    An assignment is expired if due_at + `expire_after_days` < today.
    """
    all_assignments = execute_query("active_assignments", "select")
    today = datetime.utcnow().date()

    for assignment in all_assignments:
        due_date = datetime.fromisoformat(assignment["due_at"]).date()
        if due_date + timedelta(days=expire_after_days) < today:
            # Insert into inactive_jobs
            execute_query(
                "inactive_jobs",
                "insert",
                data={
                    "assignment_id": assignment["assignment_id"],
                    "user_id": assignment["user_id"],
                    "due_at": assignment["due_at"],
                    "status": "EXPIRED",
                    "moved_at": datetime.utcnow().isoformat()
                }
            )
            # Delete from active_assignments
            execute_query(
                "active_assignments",
                "delete",
                filters=[("assignment_id", "eq", assignment["assignment_id"])]
            )


# ---------- Active Assignments for a User ----------

# services/assignments.py
from database.db import execute_query

def get_active_assignments(slack_user_id: int):
    """
    Get all active assignments for a user, including job info.
    Returns a list of dicts with:
    - assignment_id
    - job_id
    - job_name
    - job_type
    - num_hours
    - due_at
    - status
    """
    # Step 1: Get all active assignments for this user
    active_assignments = execute_query(
        "active_assignments",
        "select",
        filters=[("slack_user_id", "eq", slack_user_id)]
    )

    if not active_assignments:
        return []

    results = []

    # Step 2: For each assignment, get job_id from assignment_jobs, then job info
    for assignment in active_assignments:
        assignment_id = assignment.get("assignment_id")
        if not assignment_id:
            continue  # skip if somehow missing

        # Get the job_id from assignment_jobs
        assignment_job = execute_query(
            "assignment_jobs",
            "select",
            filters=[("assignment_id", "eq", assignment_id)]
        )

        if not assignment_job:
            continue  # skip if no mapping found

        job_id = assignment_job[0].get("job_id")
        if not job_id:
            continue  # skip if job_id missing

        # Get job info
        job_info = execute_query(
            "jobs",
            "select",
            filters=[("job_id", "eq", job_id)]
        )

        if not job_info:
            continue

        job = job_info[0]

        # Combine into a single dict
        results.append({
            "assignment_id": assignment_id,
            "job_id": job_id,
            "job_name": job.get("job_name"),
            "job_type": job.get("job_type"),
            "num_hours": job.get("num_hours"),
            "due_at": assignment.get("due_at"),
            "status": assignment.get("status")
        })

    return results
