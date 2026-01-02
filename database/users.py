from database.db import execute_query

def get_all_user_hours():
    """
    Retrieve all users with their hours completed, hours needed, and missed jobs.
    Returns a list of dicts.
    """
    rows = execute_query("users", "select", columns=["username", "hours_completed", "hours_needed", "missed_jobs"])

    return [
        {
            "username": row.get("username"),
            "hours_completed": row.get("hours_completed"),
            "hours_needed": row.get("hours_needed"),
            "missed_jobs": row.get("missed_jobs")
        }
        for row in rows
    ]



def db_generate_user_table(user_tuples):
    """
    Insert or update users in the Supabase 'users' table.
    user_tuples: list of (username, slack_user_id)
    """
    for name, slack_user_id in user_tuples:
        # Check if user already exists
        existing = execute_query(
            "users",
            "select",
            filters=[("slack_user_id", "eq", slack_user_id)]
        )

        user_data = {
            "username": name,
            "slack_user_id": slack_user_id
        }

        if existing:
            # Update username if Slack ID already exists
            execute_query(
                "users",
                "update",
                data=user_data,
                filters=[("slack_user_id", "eq", slack_user_id)]
            )
        else:
            # Insert new user
            execute_query("users", "insert", data=user_data)
