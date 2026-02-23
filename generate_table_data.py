from sheets.job_description_sheet import get_jobs_from_sheet
from sheets.job_assignments_sheet import get_job_assignments_from_sheet
from database.manage_jobs import add_job_to_db
from database.create_assignments import add_job_assignments_to_db, make_makeup_job_assignments_to_db, add_makeup_jobs_to_makeup_table
from sheets.makeup_hour_sheet import get_makeup_job_assignments_from_sheet

def add_jobs():
    jobs = get_jobs_from_sheet()
    #print(jobs)
    add_job_to_db(jobs)
    
def make_job_assignments(start_date, end_date):
    assignments = get_job_assignments_from_sheet()
    #print("ASSIGNEMNTS", assignments)
    add_job_assignments_to_db(assignments, start_date, end_date)

def make_permanent_makeup_job_assignments():
    make_makeup_job_assignments_to_db()

def generate_makeup_jobs(start_date,end_date):
    makeup_jobs = get_makeup_job_assignments_from_sheet()
    add_makeup_jobs_to_makeup_table(makeup_jobs, start_date, end_date)



if __name__ == '__main__':
    
    #add_jobs()
    make_job_assignments("2026-2-16", "2026-5-10")
    #make_job_assignments("2026-5-4", "2026-5-10")
    #generate_makeup_jobs("2026-2-2", "2026-5-20")
    #make_permanent_makeup_job_assignments()