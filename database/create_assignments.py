from datetime import datetime, timedelta
from services.formatters import parse_date
from database.db import get_table, execute_query

FREQUENCY_CONFIG = {
    "DAILY": {"count": 14, "delta": timedelta(days=1)},
    "WEEKLY": {"count": 14, "delta": timedelta(weeks=1)},
    "BIWEEKLY": {"count": 28, "delta": timedelta(weeks=2)},
}


def add_job_assignments_to_db(assignments, start_date):
    """
    Adds recurring job assignments for users to Supabase.
    assignments: list of dicts with keys "Job Name" and "Name"
    start_date: str ("YYYY-MM-DD") or datetime
    """
    # Parse start_date if string
    if isinstance(start_date, str):
        start_date = datetime.strptime(parse_date(start_date), "%Y-%m-%d")

    for assignment in assignments:
        job_name = assignment["Job Name"]
        username = assignment["Name"]

        print(f"Processing assignment: {username} → {job_name}")

        # Get job info
        job_rows = execute_query(
            "jobs",
            "select",
            filters=[("job_name", "eq", job_name)]
        )
        if not job_rows:
            print(f"Job '{job_name}' not found, skipping assignment.")
            continue
        job = job_rows[0]
        job_id, job_type = job["job_id"], job["job_type"].upper()

        if job_type not in FREQUENCY_CONFIG:
            print(f"Job type '{job_type}' for job '{job_name}' is invalid, skipping assignment.")
            continue

        # Get user_id
        user_rows = execute_query(
            "users",
            "select",
            filters=[("username", "eq", username)]
        )
        if not user_rows:
            print(f"User '{username}' not found, skipping assignment.")
            continue
        user_id = user_rows[0]["user_id"]

        # Generate recurring assignments
        config = FREQUENCY_CONFIG[job_type]
        due_at = start_date

        records_to_insert = []
        for _ in range(config["count"]):
            records_to_insert.append({
                "user_id": user_id,
                "job_id": job_id,
                "due_at": due_at.isoformat()
            })
            due_at += config["delta"]

        # Insert all at once
        execute_query("active_assignments", "insert", data=records_to_insert)
        print(f"Inserted {len(records_to_insert)} assignments for {username} → {job_name}")
