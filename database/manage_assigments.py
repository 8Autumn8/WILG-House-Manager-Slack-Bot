from datetime import datetime, timedelta
from database.db import execute_query, get_user_id


# ---------- Expiring Assignments ----------

def get_expiring_assignments():
    """
    Return active assignments that will expire in 6 days from today.
    """
    all_assignments = execute_query("active_assignments", "select", filters=[("status", "eq", "ASSIGNED")])

    expiring_jobs = []
    today = datetime.utcnow().date()

    for assignment in all_assignments:
        due_date = datetime.fromisoformat(assignment["due_at"]).date()
        if due_date + timedelta(days=6) == today:
            # Fetch job name
            job_rows = execute_query("jobs", "select", filters=[("job_id", "eq", assignment["job_id"])])
            job_name = job_rows[0]["job_name"] if job_rows else "Unknown Job"

            expiring_jobs.append({
                "assignment_id": assignment["assignment_id"],
                "user_id": assignment["user_id"],
                "job_name": job_name,
                "due_at": assignment["due_at"]
            })

    return expiring_jobs


# ---------- Expire Assignments ----------

def expire_active_assignments():
    """
    Move expired assignments from active_assignments to inactive_jobs with status 'EXPIRED'.
    An assignment is expired if due_at + 6 days < today.
    """
    all_assignments = execute_query("active_assignments", "select")

    today = datetime.utcnow().date()

    for assignment in all_assignments:
        due_date = datetime.fromisoformat(assignment["due_at"]).date()
        if due_date + timedelta(days=6) < today:
            # Insert into inactive_jobs
            execute_query(
                "inactive_jobs",
                "insert",
                data={
                    "assignment_id": assignment["assignment_id"],
                    "user_id": assignment["user_id"],
                    "job_id": assignment["job_id"],
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

def get_active_assignments(slack_user_id):
    """
    Fetch all active assignments for a user, returned as list of dicts.
    """
    user_id = get_user_id(slack_user_id)
    if not user_id:
        return []

    assignments = execute_query(
        "active_assignments",
        "select",
        filters=[("user_id", "eq", user_id)]
    )

    results = []
    for assignment in assignments:
        job_rows = execute_query("jobs", "select", filters=[("job_id", "eq", assignment["job_id"])])
        job_name = job_rows[0]["job_name"] if job_rows else "Unknown Job"

        results.append({
            "assignment_id": assignment["assignment_id"],
            "job_name": job_name,
            "due_at": assignment["due_at"],
            "user_id": assignment["user_id"],
            "status": assignment.get("status", "UNKNOWN")
        })

    # Sort by due date ascending
    results.sort(key=lambda r: r["due_at"])
    return results
