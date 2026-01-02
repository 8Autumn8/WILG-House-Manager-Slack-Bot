import gspread
from google.oauth2.service_account import Credentials
import os

# This is the house manager spreadsheet that also holds all the submission records, publically available to everyone.
SPREADSHEET_NAME = os.getenv("SUBMISSION_SPREADSHEET") # exact sheet name

def add_to_submission_logs(submission_id, submission_time, name, job, date_of_completion, witness, comments):
    
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_file(
        "google_auth.json",
        scopes=scopes
    )
    print("Updating Google Sheet...")
    client = gspread.authorize(creds)
    sheet = client.open(SPREADSHEET_NAME).sheet1


    # Prepare row data
    row = [
        submission_id,
        submission_time,  # passed in from code
        name,
        job,
        date_of_completion,
        witness,
        comments,
        ""  # Approved? checkbox stays empty
    ]
    print("Appending row to Google Sheet:", row)
    # Append row
    sheet.append_row(row)

SOURCE_SHEET_NAME = "New Hour Submissions"
DEST_SHEET_NAME = "Old Hour Submissions"

def get_approved_from_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_file(
        "google_auth.json",
        scopes=scopes
    )
    client = gspread.authorize(creds)

    sh = client.open(SPREADSHEET_NAME)
    source_sheet = sh.worksheet(SOURCE_SHEET_NAME)
    dest_sheet = sh.worksheet(DEST_SHEET_NAME)

    all_rows = source_sheet.get_all_records()   # list[dict]
    all_values = source_sheet.get_all_values()  # list[list]
    header = all_values[0]

    to_move_rows = []
    to_move_row_numbers = []
    approved_ids = []
    rejected_ids = []

    # Rows start at 2 because row 1 is the header
    for i, row in enumerate(all_rows, start=2):
        if row.get("Approved?") == "Approved":
            to_move_rows.append([row[h] for h in header])
            to_move_row_numbers.append(i)
            approved_ids.append(row["Submission ID"])
        elif row.get("Approved?") == "Rejected":
            to_move_rows.append([row[h] for h in header])
            to_move_row_numbers.append(i)
            rejected_ids.append(row["Submission ID"])

    if not to_move_rows:
        #print("No approved submissions found.")
        return approved_ids, rejected_ids

    # Append approved rows to destination sheet
    dest_sheet.append_rows(
        to_move_rows,
        value_input_option="USER_ENTERED"
    )

    # Delete approved rows from source (bottom → top)
    for row_num in sorted(to_move_row_numbers, reverse=True):
        source_sheet.delete_rows(row_num)
        
    return approved_ids, rejected_ids

#update_spreadsheet("submission_id", "submission_time", "user_name", "job_name", "date_of_completion", "witness_name", "comments")