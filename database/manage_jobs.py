from typing import List, Dict
from database.db import execute_query

def add_job_to_db(jobs: List[Dict]):
    """
    Add or update jobs in the 'jobs' table.
    If a job with the same job_id exists, update it; otherwise, insert a new record.

    Each job dict should have keys:
        - "Job ID" (required)
        - "Job Name" (required)
        - "Job Type" (required)
        - "Job Description" (optional)
        - "Num Hours" (optional)
        - "Due By Time" (optional)
    """
    for job in jobs:
        job_id = job.get("Job ID")
        if job_id is None:
            print("Skipping job with missing Job ID:", job)
            continue

        job_data = {
            "job_id": job_id,
            "job_name": job.get("Job Name", f"Job {job_id}"),
            "job_description": job.get("Job Description"),
            "num_hours": job.get("Num Hours"),
            "job_type": job.get("Job Type", "UNKNOWN"),
            "due_by_time": job.get("Due By Time")
        }

        # Check if job exists
        existing = execute_query(
            "jobs",
            "select",
            filters=[("job_id", "eq", job_id)]
        )

        if existing:
            # Update existing job
            execute_query(
                "jobs",
                "update",
                data=job_data,
                filters=[("job_id", "eq", job_id)]
            )
            print(f"Updated job {job_id} → {job_data['job_name']}")
        else:
            # Insert new job
            execute_query(
                "jobs",
                "insert",
                data=job_data
            )
            print(f"Inserted new job {job_id} → {job_data['job_name']}")
