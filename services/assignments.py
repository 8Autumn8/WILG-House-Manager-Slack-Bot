from database.manage_assigments import get_active_assignments, expire_active_assignments
from database.users import db_generate_user_table

def create_user_ids(spreadsheet_url):
    return

def generate_user_table(user_tuples):
    db_generate_user_table(user_tuples)

def expire_assignments():
    expire_active_assignments()

def get_user_assignments(user_id):

    return get_active_assignments(user_id)