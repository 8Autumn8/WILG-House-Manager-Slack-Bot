from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List
from database.db import execute_query, get_user_id

ET_OFFSET = timezone(timedelta(hours=-5))

# ---------- Expire Makeup Jobs ----------

def db_expire_makeup_jobs():
    """
    Move expired makeup jobs to inactive_jobs with status 'EXPIRED',
    then remove them from makeup_jobs.
    """
    all_makeups = execute_query("makeup_jobs", "select")
    now = datetime.now(ET_OFFSET)

    for m in all_makeups:
        due_at = datetime.fromisoformat(m["due_at"])
        if due_at < now:
            # Insert into inactive_jobs
            execute_query(
                "inactive_jobs",
                "insert",
                data={
                    "assignment_id": m["original_assignment_id"],
                    "user_id": None,
                    "job_id": m["job_id"],
                    "due_at": m["due_at"],
                    "status": "EXPIRED",
                    "moved_at": now.isoformat()
                }
            )
            # Delete from makeup_jobs
            execute_query(
                "makeup_jobs",
                "delete",
                filters=[("original_assignment_id", "eq", m["original_assignment_id"])]
            )

# ---------- Give Up Makeup Job ----------

def giveup_makeup_job(slack_user_id: str, assignment_id: int) -> Dict:
    """
    User gives up a job for makeup.
    Returns metadata about the job.
    """
    user_id = get_user_id(slack_user_id)
    if not user_id:
        raise ValueError("Slack user ID not found.")

    # Fetch active assignment
    assignments = execute_query(
        "active_assignments",
        "select",
        filters=[("assignment_id", "eq", assignment_id), ("user_id", "eq", user_id)]
    )
    if not assignments:
        raise ValueError("Assignment not found or already removed.")

    assignment = assignments[0]

    # Check job info
    job_rows = execute_query("jobs", "select", filters=[("job_id", "eq", assignment["job_id"])])
    job = job_rows[0] if job_rows else {}

    due_at = datetime.fromisoformat(assignment["due_at"])
    is_late_makeup = datetime.now(ET_OFFSET) > (due_at - timedelta(hours=24))

    # Insert into makeup_jobs
    makeup_data = {
        "original_assignment_id": assignment_id,
        "job_id": assignment["job_id"],
        "due_at": assignment["due_at"],
        "created_at": datetime.now(ET_OFFSET).isoformat()
    }

    if is_late_makeup:
        makeup_data["prev_user_id"] = user_id

    execute_query("makeup_jobs", "insert", data=makeup_data)

    # Remove from active_assignments
    execute_query(
        "active_assignments",
        "delete",
        filters=[("assignment_id", "eq", assignment_id), ("user_id", "eq", user_id)]
    )

    return {
        "assignment_id": assignment_id,
        "job_id": assignment["job_id"],
        "job_name": job.get("job_name", "Unknown Job"),
        "job_description": job.get("job_description"),
        "due_at": assignment["due_at"],
        "is_late_makeup": is_late_makeup
    }

# ---------- Claim Makeup Job ----------

def claim_makeup_job(slack_user_id: str, assignment_id: int) -> Dict:
    """
    User claims a makeup job.
    """
    user_id = get_user_id(slack_user_id)
    if not user_id:
        raise ValueError("Slack user ID not found.")

    # Fetch makeup job
    makeups = execute_query("makeup_jobs", "select", filters=[("original_assignment_id", "eq", assignment_id)])
    if not makeups:
        raise ValueError("Makeup job not found.")

    makeup = makeups[0]

    # Insert into active_assignments
    execute_query(
        "active_assignments",
        "insert",
        data={
            "assignment_id": assignment_id,
            "user_id": user_id,
            "job_id": makeup["job_id"],
            "due_at": makeup["due_at"],
            "status": "ASSIGNED"
        }
    )

    # Remove from makeup_jobs
    execute_query(
        "makeup_jobs",
        "delete",
        filters=[("original_assignment_id", "eq", assignment_id)]
    )

    # Get job name
    job_rows = execute_query("jobs", "select", filters=[("job_id", "eq", makeup["job_id"])])
    job_name = job_rows[0]["job_name"] if job_rows else "Unknown Job"

    return {
        "result": "Makeup job claimed successfully.",
        "job_name": job_name
    }

# ---------- See Makeup Jobs ----------

def db_see_makeup_jobs() -> List[Dict]:
    """
    Retrieve all makeup jobs currently available.
    """
    makeups = execute_query("makeup_jobs", "select")

    results = []
    for m in makeups:
        job_rows = execute_query("jobs", "select", filters=[("job_id", "eq", m["job_id"])])
        job = job_rows[0] if job_rows else {}

        results.append({
            "original_assignment_id": m["original_assignment_id"],
            "job_id": m["job_id"],
            "job_name": job.get("job_name", "Unknown Job"),
            "job_description": job.get("job_description"),
            "due_at": m["due_at"],
            "created_at": m.get("created_at")
        })

    # Sort by created_at ascending
    results.sort(key=lambda r: r["created_at"] or "")
    return results
