CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    slack_user_id TEXT UNIQUE NOT NULL,
    username TEXT,
    hours_needed INTEGER DEFAULT 28,
    hours_completed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id INTEGER PRIMARY KEY,
    job_name TEXT NOT NULL,
    job_description TEXT,
    num_hours INTEGER,
    job_type TEXT,
);

CREATE TABLE IF NOT EXISTS active_assignments (
    assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    slack_user_id TEXT NOT NULL,
    job_id INTEGER NOT NULL,
    due_at DATETIME NOT NULL,
    status TEXT DEFAULT 'ASSIGNED'
);

CREATE TABLE IF NOT EXISTS inactive_jobs (
    assignment_id INTEGER PRIMARY KEY,
    slack_user_id TEXT NOT NULL,
    job_id INTEGER NOT NULL,
    due_at DATETIME NOT NULL,
    status TEXT NOT NULL,
    moved_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS completed_job_history (
    assignment_id INTEGER PRIMARY KEY,
    slack_user_id TEXT NOT NULL,
    job_id INTEGER NOT NULL,
    due_at DATETIME NOT NULL
);


CREATE TABLE IF NOT EXISTS makeup_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_assignment_id INTEGER NOT NULL,
    job_id INTEGER NOT NULL,
    due_at DATETIME NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS job_submissions (
    submission_id INTEGER PRIMARY KEY AUTOINCREMENT,
    slack_user_id TEXT,
    job_hours DOUBLE,
    assignment_id INTEGER,
    date_of_completion DATETIME,
    submission_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    witness_slack_user_id TEXT,
    comments TEXT DEFAULT None,
    approved TEXT DEFAULT 'PENDING'
);

DROP TRIGGER IF EXISTS credit_hours_after_approval;

CREATE TRIGGER credit_hours_after_approval
AFTER UPDATE ON job_submissions
WHEN NEW.approved = 'APPROVED'
 AND OLD.approved != 'APPROVED'
BEGIN
    UPDATE users
    SET hours_completed = hours_completed + NEW.job_hours
    WHERE slack_user_id = NEW.slack_user_id;
END;


DROP TRIGGER IF EXISTS remove_submission_status_on_rejection;
CREATE TRIGGER remove_submission_status_on_rejection
AFTER UPDATE ON job_submissions
WHEN NEW.approved = 'REJECTED'
 AND OLD.approved != 'REJECTED'
BEGIN
    UPDATE active_assignments
    SET status = 'ASSIGNED'
    WHERE assignment_id = NEW.assignment_id;
END;

DROP TRIGGER IF EXISTS mark_assignment_submitted;

CREATE TRIGGER mark_assignment_submitted
AFTER INSERT ON job_submissions
WHEN NEW.assignment_id IS NOT NULL
 AND NEW.assignment_id != 0
BEGIN
    UPDATE active_assignments
    SET status = 'SUBMITTED'
    WHERE assignment_id = NEW.assignment_id
      AND status = 'ASSIGNED';
END;
DROP TRIGGER IF EXISTS move_assignment_to_history;

CREATE TRIGGER move_assignment_to_history
AFTER UPDATE ON job_submissions
WHEN NEW.approved = 'APPROVED'
 AND OLD.approved != 'APPROVED'
BEGIN
    -- Insert into history
    INSERT OR REPLACE INTO completed_job_history (
        assignment_id,
        slack_user_id,
        job_id,
        assigned_at,
        due_at
    )
    SELECT
        a.assignment_id,
        a.slack_user_id,
        a.job_id,
        a.due_at AS assigned_at,
        a.due_at
    FROM active_assignments a
    WHERE a.assignment_id = NEW.assignment_id;

    -- Remove from active assignments
    DELETE FROM active_assignments
    WHERE assignment_id = NEW.assignment_id;
END;

DROP TRIGGER IF EXISTS move_assignment_to_inactive_on_rejection;

CREATE TRIGGER move_assignment_to_inactive_on_rejection
AFTER UPDATE ON job_submissions
WHEN NEW.approved = 'REJECTED'
 AND OLD.approved != 'REJECTED'
BEGIN
    -- Copy assignment to inactive_jobs
    INSERT OR REPLACE INTO inactive_jobs (
        assignment_id,
        slack_user_id,
        job_id,
        due_at,
        status
    )
    SELECT
        a.assignment_id,
        a.slack_user_id,
        a.job_id,
        a.due_at,
        'REJECTED'
    FROM active_assignments a
    WHERE a.assignment_id = NEW.assignment_id;

    -- Remove from active assignments
    DELETE FROM active_assignments
    WHERE assignment_id = NEW.assignment_id;
END;

DROP TRIGGER IF EXISTS enforce_submission_deadlines;

CREATE TRIGGER enforce_submission_deadlines
BEFORE INSERT ON job_submissions
WHEN NEW.assignment_id != 0
BEGIN
    -- Kitchen jobs must be done exactly on due date
    SELECT RAISE(ABORT, 'Kitchen jobs must be done on the due date')
    WHERE EXISTS (
        SELECT 1
        FROM active_assignments a
        JOIN jobs j ON j.job_id = a.job_id
        WHERE a.assignment_id = NEW.assignment_id
          AND j.job_type = 'KITCHEN'
          AND date(NEW.date_of_completion) != date(a.due_at)
    );

    -- Weekly jobs must be done within 7 days before due date
    SELECT RAISE(ABORT, 'Weekly jobs must be done within 7 days before due date')
    WHERE EXISTS (
        SELECT 1
        FROM active_assignments a
        JOIN jobs j ON j.job_id = a.job_id
        WHERE a.assignment_id = NEW.assignment_id
          AND j.job_type = 'WEEKLY'
          AND date(NEW.date_of_completion) < date(a.due_at, '-7 days')
    );

    -- Submission must be within 7 days after due date (all jobs)
    SELECT RAISE(ABORT, 'Submission window (7 days after due date) has passed')
    WHERE EXISTS (
        SELECT 1
        FROM active_assignments a
        WHERE a.assignment_id = NEW.assignment_id
          AND datetime(NEW.submission_time) > datetime(a.due_at, '+7 days')
    );
END;


DROP TRIGGER IF EXISTS prevent_late_makeup;

CREATE TRIGGER prevent_late_makeup
BEFORE INSERT ON makeup_jobs
FOR EACH ROW
BEGIN
    -- Check if the original assignment's due date has passed
    SELECT RAISE(ABORT, 'Cannot create makeup job: assignment due date has passed')
    WHERE EXISTS (
        SELECT 1
        FROM active_assignments
        WHERE assignment_id = NEW.original_assignment_id
          AND datetime(due_at) < datetime('now')
    );
END;
