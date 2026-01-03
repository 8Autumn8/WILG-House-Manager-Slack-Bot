from sheets.job_description_sheet import get_jobs_from_sheet
from sheets.job_assignments_sheet import get_job_assignments_from_sheet
from database.manage_jobs import add_job_to_db
from database.create_assignments import add_job_assignments_to_db, make_makeup_job_assignments_to_db

def add_jobs():
    jobs = get_jobs_from_sheet()
    print(jobs)
    add_job_to_db(jobs)
    
def make_job_assignments(start_date):
    assignments = get_job_assignments_from_sheet()
    add_job_assignments_to_db(assignments, start_date)

def make_makeup_job_assignments():
    make_makeup_job_assignments_to_db()

if __name__ == '__main__':
    add_jobs()
    make_job_assignments("2026-1-5")
    make_makeup_job_assignments()