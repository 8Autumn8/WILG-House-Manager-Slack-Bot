from database.db import get_db
import sqlite3

def add_job_to_db(jobs):
    conn = get_db()
    cursor = conn.cursor()

    for job in jobs:
        cursor.execute(
            """
            INSERT INTO jobs (
                job_id,
                job_name,
                job_description,
                num_hours,
                job_type,
                due_by_time
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                job_name = excluded.job_name,
                job_description = excluded.job_description,
                num_hours = excluded.num_hours,
                job_type = excluded.job_type,
                due_by_time = excluded.due_by_time
            """,
            (
                job["Job ID"],
                job["Job Name"],
                job.get("Job Description"),
                job.get("Num Hours"),
                job["Job Type"],
                job["Due By Time"],
            )
        )

    conn.commit()
    conn.close()
