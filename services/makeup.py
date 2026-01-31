from database.manage_makeup import giveup_makeup_job, db_expire_makeup_jobs, claim_makeup_job, db_see_makeup_jobs

def giveup_job_for_makeup(user_id, assignment_id):
    try:
        #print("HERE")
        return giveup_makeup_job(user_id, assignment_id)
    except Exception as e:
        #print(f"Error in giveup_job_for_makeup: {e}")
        return {"result": "ERROR", "message": str(e)}
    
def claim_job_for_makeup(user_id, makeup_job_id):
    try:
        return claim_makeup_job(user_id, makeup_job_id)
    except Exception as e:
        #print(f"Error in claim_job_for_makeup: {e}")
        return {"result": "ERROR", "message": str(e)}

def see_makeup_jobs():
    try:
        return db_see_makeup_jobs()
    except Exception as e:
        #print(f"Error in see_makeup_jobs: {e}")
        return e

def get_available_jobs_by_id(job_id):
    try:
        all_makeup_jobs = db_see_makeup_jobs(job_id)
        available_jobs = [job for job in all_makeup_jobs if job['job_id'] == job_id]
        return {"result": "SUCCESS", "available_jobs": available_jobs}
    except Exception as e:
        #print(f"Error in get_available_jobs_by_id: {e}")
        return {"result": "ERROR", "message": str(e)}

def expire_makeup_jobs():
    db_expire_makeup_jobs()




# def claim_job():
#     conn = get_db()