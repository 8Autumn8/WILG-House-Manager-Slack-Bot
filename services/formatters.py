from datetime import datetime
import os

def format_submissions_table(submissions, approved_hours):
    if not submissions:
        return "*No submissions found.*"

    header = (
        "```"
        "ID   Job Name      Job Hours   Status     Submitted At\n"
        "----------------------------------------\n"
    )

    rows = []
    for s in submissions:
        submitted_at = s["submission_time"]
        if isinstance(submitted_at, str):
            submitted_at = submitted_at.split(".")[0]

        rows.append(
            f"{str(s['submission_id']).ljust(4)} "
            f"{str(s['job_name']).ljust(20)} "
            f"{str(s['job_hours']).ljust(10)} "
            f"{s['approved'].ljust(10)} "
            f"{submitted_at}"
        )

    footer = (
        "\n----------------------------------------\n"
        f"TOTAL APPROVED HOURS: {approved_hours}\n"
        "```"
    )

    return header + "\n".join(rows) + footer


PAGE_SIZE = int(os.getenv("SUBMISSIONS_PAGE_SIZE", 10))

def get_page(submissions, page):
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    return submissions[start:end]

def page_block_formatting_helper(data, page):
    total_pages = (len(data) + PAGE_SIZE - 1) // PAGE_SIZE
    data_on_page = get_page(data, page)
    return data_on_page, total_pages

def build_page_blocks(total_pages, page, table_text, view_type="submissions"):

    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": table_text}}
    ]

    buttons = []
    if page > 1:
        buttons.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "⬅ Prev"},
            "value": f"{view_type}-{page-1}",  # encode view + page
            "action_id": "prev_page"
        })
    if page < total_pages:
        buttons.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "Next ➡"},
            "value": f"{view_type}-{page+1}",  # encode view + page
            "action_id": "next_page"
        })

    if buttons:
        blocks.append({"type": "actions", "elements": buttons})

    return blocks



def format_all_user_hours_table(all_user_hours):
    if not all_user_hours:
        return "*No user hours found.*"

    header = (
        "```"
        "Username        Hours Completed                Missed Jobs\n"
        "------------------------------------------------------------\n"
    )

    rows = []
    for user in all_user_hours:
        rows.append(
            f"{str(user['username']).ljust(20)} "
            f"{str(user['hours_completed']).ljust(16)} "
            f"{str(user['missed_jobs'])}"
        )

    footer = "\n```"

    return header + "\n".join(rows) + footer

def parse_date(date_str):
    if not date_str:
        return None  # missing date

    formats = ["%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d"]  # add more if needed

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")  # return just the date
        except ValueError:
            continue

    # None of the formats worked
    return None


def format_user_active_assignments(assignments):
    #print(assignments)
    if not assignments:
        return "*No active assignments found.*"

    header = (
        "```"
        "ID   Job Name                        Due At                    Status\n"
        "---------------------------------------------------------------------\n"
    )

    rows = []
    for a in assignments:
        due_at = a["due_at"]
        if isinstance(due_at, str):
            due_at = due_at.split(".")[0]

        rows.append(
            f"{str(a['assignment_id']).ljust(4)} "
            f"{str(a['job_name']).ljust(30)} "
            f"{str(due_at).ljust(26)} "
            f"{a['status']}"
        )

    footer = "\n```"

    return header + "\n".join(rows) + footer


def format_makeup_giveup_message(job):
    """
    Formats a message for a job that was given up for makeup.
    Expects a dict with:
    assignment_id, job_id, job_name, job_description, due_at
    """
    due_at = job["due_at"]

    # Normalize datetime
    if isinstance(due_at, str):
        due_at = due_at.split(".")[0]
        due_at = datetime.fromisoformat(due_at)

    due_str = due_at.strftime("%A, %B %d at %I:%M %p")

    return (
        "🛠️ *Job given up for makeup*\n\n"
        f"*Job:* {job['job_name']}\n"
        f"*Description:* {job['job_description']}\n"
        f"*Due:* {due_str}\n"
        f"*Assignment ID:* `{job['assignment_id']}`"
    )


def format_makeup_jobs(jobs):
    if not jobs:
        return "*No makeup jobs found.*"

    header = (
        "```"
        "ID   Job Name                        Due At                  \n"
        "-------------------------------------------------------------\n"
    )

    rows = []
    for j in jobs:
        due_at = j["due_at"]
        if isinstance(due_at, str):
            due_at = due_at.split(".")[0]

        rows.append(
            f"{str(j['original_assignment_id']).ljust(4)} "
            f"{str(j['job_name']).ljust(30)} "
            f"{str(due_at).ljust(26)} "
        )

    footer = "\n```"

    return header + "\n".join(rows) + footer