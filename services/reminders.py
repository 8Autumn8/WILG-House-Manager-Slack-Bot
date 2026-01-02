from datetime import datetime, timedelta
from database.manage_assigments import get_expiring_assignments

def get_expiring_jobs():
    
    return get_expiring_assignments()