import sqlite3
from datetime import datetime

DB_FILE = "house_manager.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON;")  # enable foreign keys
    c = conn.cursor()

    # Drop tables
    c.executescript("""
    DROP TABLE IF EXISTS job_submissions;
    DROP TABLE IF EXISTS active_assignments;
    DROP TABLE IF EXISTS jobs;
    DROP TABLE IF EXISTS users;

    CREATE TABLE users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        slack_user_id TEXT UNIQUE NOT NULL,
        username TEXT,
        hours_needed INTEGER DEFAULT 28,
        hours_completed INTEGER DEFAULT 0
    );

    CREATE TABLE jobs (
        job_id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_name TEXT NOT NULL,
        job_type TEXT NOT NULL  -- 'KITCHEN' or 'WEEKLY'
    );

    CREATE TABLE active_assignments (
        assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        slack_user_id TEXT NOT NULL,
        job_id INTEGER NOT NULL,
        due_at DATETIME NOT NULL,
        status TEXT DEFAULT 'ASSIGNED'
    );

    CREATE TABLE job_submissions (
        submission_id INTEGER PRIMARY KEY AUTOINCREMENT,
        slack_user_id TEXT,
        job_hours DOUBLE,
        assignment_id INTEGER,
        date_of_completion DATETIME,
        submission_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        witness_slack_user_id TEXT,
        comments TEXT DEFAULT NULL,
        approved TEXT DEFAULT 'PENDING'
    );

    DROP TRIGGER IF EXISTS enforce_submission_deadlines;

    CREATE TRIGGER enforce_submission_deadlines
    BEFORE INSERT ON job_submissions
    WHEN NEW.assignment_id != 0
    BEGIN
        -- Kitchen jobs: must be done on due date
        SELECT RAISE(ABORT, 'Kitchen jobs must be done on the due date')
        WHERE EXISTS (
            SELECT 1
            FROM active_assignments a
            JOIN jobs j ON j.job_id = a.job_id
            WHERE a.assignment_id = NEW.assignment_id
              AND j.job_type = 'KITCHEN'
              AND date(NEW.date_of_completion) != date(a.due_at)
        );

        -- Weekly jobs: completed within 7 days before due date
        SELECT RAISE(ABORT, 'Weekly jobs must be completed within 7 days before the due date')
        WHERE EXISTS (
            SELECT 1
            FROM active_assignments a
            JOIN jobs j ON j.job_id = a.job_id
            WHERE a.assignment_id = NEW.assignment_id
              AND j.job_type = 'WEEKLY'
              AND date(NEW.date_of_completion) < date(a.due_at, '-7 days')
        );

        -- All jobs: submission must be within 7 days after due date
        SELECT RAISE(ABORT, 'Submission window (7 days after due date) has passed')
        WHERE EXISTS (
            SELECT 1
            FROM active_assignments a
            WHERE a.assignment_id = NEW.assignment_id
              AND datetime(NEW.submission_time) > datetime(a.due_at, '+7 days')
        );
    END;
    """)
    conn.commit()
    conn.close()

def test_inserts():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Add a user
    c.execute("INSERT INTO users (slack_user_id, username) VALUES (?, ?)", ("U001", "Belinda"))

    # Add jobs
    c.execute("INSERT INTO jobs (job_name, job_type) VALUES (?, ?)", ("Guest Bathroom Cleaning", "WEEKLY"))
    c.execute("INSERT INTO jobs (job_name, job_type) VALUES (?, ?)", ("Kitchen Cleaning", "KITCHEN"))

    # Add assignments
    c.execute("INSERT INTO active_assignments (slack_user_id, job_id, due_at) VALUES (?, ?, ?)",
              ("U001", 1, "2025-12-21"))
    c.execute("INSERT INTO active_assignments (slack_user_id, job_id, due_at) VALUES (?, ?, ?)",
              ("U001", 2, "2025-12-22"))

    conn.commit()

    # -------- Test submissions --------
    try:
        # Valid WEEKLY submission: within 7 days before due date
        c.execute("INSERT INTO job_submissions (slack_user_id, job_hours, assignment_id, date_of_completion) "
                  "VALUES (?, ?, ?, ?)",
                  ("U001", 1, 1, "2025-12-15"))
        print("Weekly submission inserted successfully ✅")
    except sqlite3.IntegrityError as e:
        print("Weekly submission failed ❌", e)

    try:
        # Invalid WEEKLY submission: too early
        c.execute("INSERT INTO job_submissions (slack_user_id, job_hours, assignment_id, date_of_completion) "
                  "VALUES (?, ?, ?, ?)",
                  ("U001", 1, 1, "2025-12-10"))
        print("Weekly early submission inserted ✅")
    except sqlite3.IntegrityError as e:
        print("Weekly early submission failed ❌", e)

    try:
        # Valid KITCHEN submission: exactly on due date
        c.execute("INSERT INTO job_submissions (slack_user_id, job_hours, assignment_id, date_of_completion) "
                  "VALUES (?, ?, ?, ?)",
                  ("U001", 2, 2, "2025-12-22"))
        print("Kitchen submission inserted successfully ✅")
    except sqlite3.IntegrityError as e:
        print("Kitchen submission failed ❌", e)

    try:
        # Invalid KITCHEN submission: wrong day
        c.execute("INSERT INTO job_submissions (slack_user_id, job_hours, assignment_id, date_of_completion) "
                  "VALUES (?, ?, ?, ?)",
                  ("U001", 2, 2, "2025-12-21"))
        print("Kitchen wrong day submission inserted ✅")
    except sqlite3.IntegrityError as e:
        print("Kitchen wrong day submission failed ❌", e)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    test_inserts()
