from datetime import datetime, timedelta, timezone
from database.db import execute_query
from database.db import get_table

FREQUENCY_CONFIG = {
    "DAILY": {"count": 14, "delta": timedelta(days=1)},
    "WEEKLY": {"count": 14, "delta": timedelta(weeks=1)},
    "BIWEEKLY": {"count": 28, "delta": timedelta(weeks=2)},
    "KITCHEN": {"count": 14, "delta": timedelta(weeks=1)},  # weekly recurrence
}

ET_OFFSET = timezone(timedelta(hours=-5))


def add_job_assignments_to_db(assignments, start_date):
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d")

    weekdays = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6
    }

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
        due_time_str = job.get("due_by_time", "12:00:00")

        if job_type not in FREQUENCY_CONFIG:
            print(f"Job type '{job_type}' is invalid, skipping assignment.")
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

        hour, minute, second = map(int, due_time_str.split(":"))

        # KITCHEN jobs: assign due date based on the weekday in the job name
        if job_type == "KITCHEN":
            due_at = start_date
            for day_name, weekday_num in weekdays.items():
                if day_name in job_name.lower():
                    days_ahead = (weekday_num - due_at.weekday() + 7) % 7
                    due_at += timedelta(days=days_ahead)
                    break
            # Set due time from job's due_by_time
            due_at = due_at.replace(hour=hour, minute=minute, second=second, microsecond=0, tzinfo=ET_OFFSET)
        else:
            # Other jobs: 1 week after start date
            due_at = start_date + timedelta(weeks=1)
            due_at = due_at.replace(hour=hour, minute=minute, second=second, microsecond=0, tzinfo=ET_OFFSET)

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

        execute_query("active_assignments", "insert", data=records_to_insert)
        print(f"Inserted {len(records_to_insert)} assignments for {username} → {job_name}")



def make_makeup_job_assignments_to_db():
    """
    Creates a permanent 'Makeup Job' (job_id=0) and assigns it to all users.
    This job never expires and is always in users' active assignments.
    """
    # 1️⃣ Create Job 0 if it doesn't exist
    existing_job = execute_query(
        "jobs",
        "select",
        filters=[("job_id", "eq", 0)]
    )
    if not existing_job:
        execute_query(
            "jobs",
            "insert",
            data=[{
                "job_id": 0,
                "job_name": "Makeup Job",
                "job_description": "Permanent makeup job for all users",
                "num_hours": 1,
                "job_type": "MAKEUP",
                "due_by_time": "23:59:59-05:00"
            }]
        )
        print("Created permanent Makeup Job (job_id=0).")
    else:
        print("Permanent Makeup Job already exists.")

    # 2️⃣ Assign Job 0 to all users
    users_response = get_table("users").select("*").execute()
    users = users_response.data  # ✅ extract the list of rows

    far_future_due = datetime(2026, 12, 31, 23, 59, 0).isoformat() + "-05:00"

    records_to_insert = []
    for user in users:
        user_id = user["user_id"]

        # Skip if user already has Job 0 assigned
        existing_assignment = execute_query(
            "active_assignments",
            "select",
            filters=[("user_id", "eq", user_id), ("job_id", "eq", 0)]
        )
        if existing_assignment:
            continue

        records_to_insert.append({
            "user_id": user_id,
            "job_id": 0,
            "due_at": far_future_due,
            "status": "ASSIGNED"
        })

    if records_to_insert:
        execute_query("active_assignments", "insert", data=records_to_insert)
        print(f"Assigned permanent Makeup Job to {len(records_to_insert)} users.")
    else:
        print("All users already have the permanent Makeup Job assigned.")
