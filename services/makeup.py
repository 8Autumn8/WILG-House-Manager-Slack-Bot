from database.db import get_db
from database.manage_makeup import giveup_makeup_job, db_expire_makeup_jobs, claim_makeup_job

def giveup_job_for_makeup(user_id, assignment_id):
    try:
        giveup_makeup_job(user_id, assignment_id)
    except Exception as e:
        print(f"Error in giveup_job_for_makeup: {e}")
        return
    
def claim_job_for_makeup(user_id, makeup_job_id):
    try:
        claim_makeup_job(user_id, makeup_job_id)
    except Exception as e:
        print(f"Error in claim_job_for_makeup: {e}")
        return

def expire_makeup_jobs():
    db_expire_makeup_jobs()




def claim_job():
    conn = get_db()