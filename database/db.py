# db.py
from supabase import create_client, Client
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Supabase URL and service role key
SUPABASE_URL: str = os.getenv("SUPABASE_URL")
SUPABASE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # backend key

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")

# Create Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Helper functions to replace SQLite get_db()
def get_table(table_name: str):
    """
    Returns a handle to a Supabase table.
    Usage: get_table("jobs").select("*").execute()
    """
    return supabase.table(table_name)

def execute_query(table_name: str, query_type: str, data=None, filters=None):
    """
    Generalized query executor
    - table_name: the Supabase table
    - query_type: "select", "insert", "update", "delete"
    - data: dict or list of dicts for insert/update
    - filters: list of tuples for filtering, e.g. [("id", "eq", 1)]
    """
    tbl = get_table(table_name)

    if query_type == "select":
        q = tbl.select("*")
        if filters:
            for col, op, val in filters:
                q = q.eq(col, val) if op == "eq" else q
        return q.execute().data

    elif query_type == "insert":
        return tbl.insert(data).execute().data

    elif query_type == "update":
        q = tbl.update(data)
        if filters:
            for col, op, val in filters:
                q = q.eq(col, val) if op == "eq" else q
        return q.execute().data

    elif query_type == "delete":
        q = tbl.delete()
        if filters:
            for col, op, val in filters:
                q = q.eq(col, val) if op == "eq" else q
        return q.execute().data

    else:
        raise ValueError(f"Unknown query_type: {query_type}")
    

def get_user_id(slack_user_id):
    """
    Return the numeric user_id for a given Slack ID, or None if not found.
    """
    rows = execute_query("users", "select", filters=[("slack_user_id", "eq", slack_user_id)])
    return rows[0]["user_id"] if rows else None
