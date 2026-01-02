from database.db import execute_query

def add_job_to_db(jobs):
    """
    Add or update jobs in the Supabase 'jobs' table.
    If a job with the same job_id exists, update its fields; otherwise insert.
    """
    for job in jobs:
        job_id = job["Job ID"]

        # Check if job exists
        existing = execute_query(
            "jobs",
            "select",
            filters=[("job_id", "eq", job_id)]
        )

        job_data = {
            "job_id": job_id,
            "job_name": job["Job Name"],
            "job_description": job.get("Job Description"),
            "num_hours": job.get("Num Hours"),
            "job_type": job["Job Type"],
            "due_by_time": job.get("Due By Time")
        }

        if existing:
            # Update existing job
            execute_query(
                "jobs",
                "update",
                data=job_data,
                filters=[("job_id", "eq", job_id)]
            )
        else:
            # Insert new job
            execute_query(
                "jobs",
                "insert",
                data=job_data
            )
