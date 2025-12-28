SELECT a.assignment_id, j.job_type, a.due_at, '2025-01-01' AS test_completion,
       date('2025-01-01') < date(a.due_at, '-7 days') AS too_early
FROM active_assignments a
JOIN jobs j ON j.job_id = a.job_id
WHERE a.assignment_id = 4;