from sheets.update_hours_sheet import add_to_submission_logs, get_approved_from_sheet
from database.job_submissions import add_to_submission_table, get_all_submissions_and_approved_hours, approve_jobs_in_db, reject_jobs_in_db
from database.users import get_all_user_hours
import slack
import os
import sqlite3




def get_user_submissions(user_id):
    submissions, approved_hours = get_all_submissions_and_approved_hours(user_id)
    # conn = get_db()
    # cursor = conn.execute("SELECT * FROM job_submissions WHERE slack_user_id = ?", (user_id,))
    # return f"{user_id}'s Hours:\n" + cursor.fetchall()
    #print(submissions, approved_hours)
    return submissions, approved_hours

def submit_hours(
    slack_user_id,
    assignment_id,
    job_hours,
    date_of_completion,
    submission_time,
    witness_slack_user_id,
    comments,
    channel_id
):
    print("Submitting hours...")
    try:

        submission_id, user_name, job_name, witness_name = add_to_submission_table(
            slack_user_id,
            job_hours,
            assignment_id,
            date_of_completion,
            submission_time,
            witness_slack_user_id,
            comments,
            channel_id
        )
        print("added to submission table, now updating logs...")
        add_to_submission_logs(submission_id, submission_time, user_name, job_name, date_of_completion, witness_name, comments)
        #return submission_id

        # Notify user on Slack
        return {
        "success": True,
        "submission_id": submission_id,
        "message": f"Submission {submission_id} created",
        "job_name": job_name
        }
    except Exception as e:
        return {
            "success": False,
            "submission_id": -1,
            "message": f"Submission unsuccessful: {str(e)}",
        }

    
def sync_hours():
    approved_ids, rejected_ids = get_approved_from_sheet()
    print("Approving IDs:", approved_ids)
    approve_jobs_in_db(approved_ids)
    reject_jobs_in_db(rejected_ids)
    result = get_all_user_hours()
    return result
