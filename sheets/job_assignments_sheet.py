import gspread
from google.oauth2.service_account import Credentials
import os
from pathlib import Path

SPREADSHEET_NAME = os.getenv("JOB_DESCRIPTION_ASSIGNMENT_SPREADSHEET", "Spring 2026 House & Kitchen Job Description + Assignments")
WORKSHEET_NAME = "Job Assignments"  # tab name

auth_file = Path(__file__).parent.parent / "google_auth.json"
def get_job_assignments_from_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_file(
        auth_file,
        scopes=scopes
    )

    client = gspread.authorize(creds)
    print(SPREADSHEET_NAME)
    sheet = client.open(SPREADSHEET_NAME).worksheet(WORKSHEET_NAME)

    rows = sheet.get_all_records()  # list of dicts
    return rows

