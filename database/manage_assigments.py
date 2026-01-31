from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from database.db import execute_query, get_user_id, get_job_id, get_slack_user_id

# ---------- Expiring Assignments ----------

ET = ZoneInfo("America/New_York")  # Eastern Time (DST-aware)

def get_expiring_assignments(days_after_due: int = 5) -> list[dict]:
    """
    Return active assignments that will expire in `days_before_expire` days from today (in EST).
    Each dict includes assignment_id, slack_user_id, job_name, and due_at.
    """
    # Fetch all active assignments with status ASSIGNED
    all_assignments = execute_query(
        "active_assignments",
        "select",
        filters=[("status", "eq", "ASSIGNED")]
    )

    today = datetime.now(ET).date()  # current date in Eastern Time
    expiring_jobs = []

    for assignment in all_assignments:
        # Parse the assignment's due_at
        due_dt = datetime.fromisoformat(assignment["due_at"])
        if due_dt.tzinfo is None:
            due_dt = due_dt.replace(tzinfo=ET)
        due_date = due_dt.date()

        # How many days have passed since due date
        days_since_due = (today - due_date).days

        # Trigger reminder [days_after_due] days after due date
        if days_since_due == days_after_due:
            # Get job_name (all assignments have a job_id)
            job_id = get_job_id(assignment["assignment_id"])
            job_rows = execute_query(
                "jobs",
                "select",
                filters=[("job_id", "eq", job_id)]
            )
            job_name = job_rows[0]["job_name"] if job_rows else "Unknown Job"

            # Get the Slack user ID
            slack_user_id = get_slack_user_id(assignment["user_id"])

            # Append to the list
            expiring_jobs.append({
                "assignment_id": assignment["assignment_id"],
                "slack_user_id": slack_user_id,
                "job_name": job_name,
                "due_at": assignment["due_at"]
            })

    # Optional: sort by due date ascending
    expiring_jobs.sort(key=lambda a: a["due_at"])

    print("Expiring jobs:", expiring_jobs)
    return expiring_jobs


# ---------- Expire Assignments ----------

def expire_active_assignments(expire_after_days: int = 7):
    """
    Move expired assignments from active_assignments to inactive_jobs with status 'EXPIRED'.
    An assignment is expired if due_at + `expire_after_days` < today.
    """
    all_assignments = execute_query("active_assignments", "select")
    today = datetime.utcnow().date()
    submissions = execute_query("job_submissions", "select", filters=[("approved", "neq", "REJECTED")]) 
    submission_set = set()
    if submissions:
        submission_set = {s["assignment_id"] for s in submissions}
        print(submission_set)
    for assignment in all_assignments:
        due_date = datetime.fromisoformat(assignment["due_at"]).date()
        
        if due_date + timedelta(days=expire_after_days) < today and assignment["assignment_id"] not in submission_set:
            # Insert into inactive_jobs
            execute_query(
                "inactive_jobs",
                "insert",
                data={
                    "assignment_id": assignment["assignment_id"],
                    "user_id": assignment["user_id"],
                    "due_at": assignment["due_at"],
                    "status": "EXPIRED",
                    "came_from": "ASSIGNMENT",
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
    user_id = get_user_id(slack_user_id)

    active_assignments = execute_query(
        "active_assignments",
        "select",
        filters=[("user_id", "eq", user_id)]
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
        if job_id is None:
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

    results.sort(key=lambda r: r["due_at"] or "")
    #print("Active assignments retrieved:", results)
    return results
