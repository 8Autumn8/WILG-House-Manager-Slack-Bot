from database.db import execute_query

def add_user(slack_user_id: str, username: str):
    """
    Adds a new user to the 'users' table in Supabase.
    If the Slack ID or username already exists, it will skip insertion.
    """
    # Check if user already exists (by slack_user_id)
    existing_users = execute_query(
        "users",
        "select",
        filters=[("slack_user_id", "eq", slack_user_id)]
    )

    if existing_users:
        print(f"User '{username}' with Slack ID '{slack_user_id}' already exists, skipping.")
        return

    # Insert new user
    try:
        execute_query(
            "users",
            "insert",
            data={"slack_user_id": slack_user_id, "username": username}
        )
        print(f"User '{username}' added successfully.")
    except Exception as e:
        print(f"Failed to add user '{username}': {e}")


# Example usage
add_user(slack_user_id="U0A4V8PLXFC", username="v.belinda.k")
