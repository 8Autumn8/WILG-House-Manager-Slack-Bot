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
        start_date = datetime.strptime(start_date, "%Y-%m-%d")

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
        job_time_str = job.get("time", "00:00:00")  # expected format: HH:MM:SS

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

        # Generate first due_at datetime
        due_at = start_date.replace(
            hour=int(job_time_str[:2]),
            minute=int(job_time_str[3:5]),
            second=int(job_time_str[6:8]),
            microsecond=0
        )

        # If job name contains a weekday, adjust start date to that day
        weekdays = {
            "monday": 0, "tuesday": 1, "wednesday": 2,
            "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6
        }
        for day_name, weekday_num in weekdays.items():
            if day_name in job_name.lower():
                # Move due_at forward to the next matching weekday
                days_ahead = (weekday_num - due_at.weekday() + 7) % 7
                if days_ahead != 0:
                    due_at += timedelta(days=days_ahead)
                break

        # Generate recurring assignments
        config = FREQUENCY_CONFIG[job_type]

        records_to_insert = []
        current_due = due_at
        for _ in range(config["count"]):
            records_to_insert.append({
                "user_id": user_id,
                "job_id": job_id,
                "due_at": current_due.isoformat()
            })
            current_due += config["delta"]

        # Insert all at once
        execute_query("active_assignments", "insert", data=records_to_insert)
        print(f"Inserted {len(records_to_insert)} assignments for {username} → {job_name}")
