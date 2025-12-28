import gspread
from google.oauth2.service_account import Credentials
import os


SPREADSHEET_NAME = os.getenv("JOB_DESCRIPTION_ASSIGNMENT_SPREADSHEET", "Spring 2026 House & Kitchen Job Description + Assignments")
WORKSHEET_NAME = "Job Descriptions"  # tab name


def get_jobs_from_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_file(
        "google_auth.json",
        scopes=scopes
    )

    client = gspread.authorize(creds)
    print(SPREADSHEET_NAME)
    sheet = client.open(SPREADSHEET_NAME).worksheet(WORKSHEET_NAME)

    rows = sheet.get_all_records()  # list of dicts
    return rows