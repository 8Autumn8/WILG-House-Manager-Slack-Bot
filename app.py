import slack
import os
import threading
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, json, request, Response, jsonify
from slackeventsapi import SlackEventAdapter
from services.submissions import submit_hours, get_user_submissions, sync_hours
from services.formatters import format_submissions_table, build_page_blocks, format_all_user_hours_table, format_user_active_assignments, parse_date, format_makeup_giveup_message, format_makeup_jobs, page_block_formatting_helper
from services.makeup import claim_job_for_makeup, giveup_job_for_makeup, expire_makeup_jobs, see_makeup_jobs, get_available_jobs_by_id
from services.assignments import generate_user_table, get_user_assignments, expire_assignments
from services.reminders import get_expiring_jobs
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

#env_path = Path(__file__).parent.parent / '.env'
load_dotenv()
client = slack.WebClient(token=os.getenv("SLACK_TOKEN"))
app = Flask(__name__)


slack_event_adapter = SlackEventAdapter(os.getenv('SIGNING_SECRET'), '/slack/events', app)
BOT_ID = client.api_call("auth.test")['user_id']


# @slack_event_adapter.on('message')
# def message(payload):
#     event = payload.get('event', {})
#     channel_id = event.get('channel')
#     user_id = event.get('user')
#     text = event.get('text')
#     if BOT_ID != user_id:
#         response = client.chat_postMessage(channel=channel_id, text=text)

    # if 'hello' in text.lower():
    #     client.chat_postMessage(channel=channel_id, text=f"Hello, <@{user_id}>!")
    # elif 'how are you' in text.lower():
    #     client.chat_postMessage(channel=channel_id, text=f"I'm just a computer program, but thanks for asking, <@{user_id}>!")
    # elif 'goodbye' in text.lower():
    #     client.chat_postMessage(channel=channel_id, text=f"Goodbye, <@{user_id}>! Have a great day!")

def get_user_id_by_username(username):
    # Remove @ if present
    username = username.lstrip("@")

    # Get all users
    result = client.users_list()
    for member in result["members"]:
        if member["name"] == username:  # matches user_name
            return member["id"]
    return None


def to_datetime_str(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value        # already serialized
    return value.isoformat()

def submit_hours_background(user_id, assignment_id, job_hours, date_of_completion, submission_time, witness_slack_user_id, comments, channel_id):
    result = submit_hours(user_id, assignment_id, job_hours, date_of_completion, submission_time, witness_slack_user_id, comments, channel_id)

    if result["success"]:
        client.chat_postMessage(
            channel=channel_id,
            text=f"✅ {result['message']}"
        )
        client.chat_postMessage(channel=witness_slack_user_id, text=f"You have been listed as a witness for a job submission by <@{user_id}>. They submitted {job_hours} hours for {result['job_name']} completed on {date_of_completion}.")

    else:
        client.chat_postMessage(
            channel=channel_id,
            text=f"❌ {result['message']}"
        )


@app.route('/submit-hour', methods=['POST'])
def submit_hour_api():
    data = request.form
    #print(data)
    commands = data.get('text', '').split()
    if len(commands) < 4:
        return jsonify({
            "response_type": "ephemeral",
            "text": f"❌ Missing required parameters: {', '.join(commands)}"
        }), 400
         

    user_id = data.get("user_id")
    channel_id = data.get("channel_id")
    assignment_id = int(commands[0])
    job_hours = float(commands[1])
    date_of_completion = parse_date(commands[2])
    #print(date_of_completion)
    if date_of_completion is None:
        return jsonify({
            "response_type": "ephemeral",
            "text": f"❌ Invalid date format: {commands[2]}"
        }), 400

    witness_slack_user_id = get_user_id_by_username(commands[3])
    if not witness_slack_user_id or witness_slack_user_id == user_id:
        return jsonify({
            "response_type": "ephemeral",
            "text": f"❌ Could not find witness user: {commands[3]}"
        }), 400
    comments = ' '.join(commands[4::]) if len(commands) > 4 else ""
    submission_time = data.get("submission_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    username = data.get('user_name')
    # Immediately ACK Slack
    response_message = f"{username} submitted a job. Processing..."
    client.chat_postMessage(channel=channel_id, text=response_message)

    # Run the slow DB + Sheet operation in the background
    threading.Thread(
        target=submit_hours_background,
        args=(user_id, assignment_id, job_hours, date_of_completion, submission_time, witness_slack_user_id, comments, channel_id)
    ).start()

    # Return empty 200 response so Slack doesn't timeout
    return Response(), 200

def claim_job_for_makeup_background(channel_id, user_id, assignment_id):
    result = claim_job_for_makeup(user_id, assignment_id)
    if result["result"] == "ERROR":
        message = f"❌ Could not claim job for makeup: {result['message']}"
    else:
        message = f"✅ Job claimed for makeup: {result['job_name']} due @ {result['due_at']}"

    client.chat_postMessage(
        channel=channel_id,
        text=message
    )

@app.route('/claim-makeup-job', methods=['POST'])
def claim_job_makeup_job_api():
    data = request.form
    user_id = data.get('user_id')
    user_name = data.get('user_name')
    channel_id = data.get('channel_id')
    assignmnet_id = data.get('text')
    message = f"{user_name} is claiming a makeup job..."
    response = client.chat_postMessage(channel=channel_id, text=message)
    #print(data)
    
    threading.Thread(
        target=claim_job_for_makeup_background,
        args=(channel_id, user_id, assignmnet_id)
    ).start()
    return Response(), 200

MAKEUP_HOUR_CHANNEL = os.getenv("MAKEUP_HOUR_CHANNEL_ID")
def giveup_job_for_makeup_background(channel_id, user_id, assignment_id):
    # print("CHANNEL,", channel_id)
    # print("MAKEUP,", MAKEUP_HOUR_CHANNEL)
    result = giveup_job_for_makeup(user_id, assignment_id)
    if result["result"] == "ERROR":
        message = f"❌ Could not give up job for makeup: {result['message']}"
        client.chat_postMessage(
            channel=channel_id,
            text=message
        )
    elif isinstance(result, Exception):
        client.chat_postMessage(
            channel=channel_id,
            text=f"❌ An error occurred while giving up the job for makeup: {str(result)}"
        )
    else:
        
        message = format_makeup_giveup_message(result)
        client.chat_postMessage(
            channel=MAKEUP_HOUR_CHANNEL, #makeup hour channel for postings
            text=message
        )


@app.route('/giveup-job-for-makeup', methods=['POST'])
def giveup_job_for_makeup_api():
    data = request.form
    #print(data)
    user_id = data.get('user_id')
    channel_id = data.get('channel_id')
    assignmnet_id = data.get('text')
    user_name = data.get('user_name')
    message = f"Giving up {user_name}'s job for makeup..."
    response = client.chat_postMessage(channel=channel_id, text=message)
    #print(data)
    
    threading.Thread(
        target=giveup_job_for_makeup_background,
        args=(channel_id, user_id, assignmnet_id)
    ).start()
    return Response(), 200

def handle_actions_background(payload):
    
    payload_json = json.loads(payload)

    action = payload_json["actions"][0]
    #page = int(action["value"])
    
    channel_id = payload_json["channel"]["id"]
    payload = json.loads(action["value"])
    user_name = payload["user_name"]
    view_type = payload["view_type"]  
    page = int(payload["page"])

    if view_type == "submissions":
        user_id = payload["user_id"]
        submissions, approved_hours = get_user_submissions(user_id)
        submissions, total_pages = page_block_formatting_helper(submissions, page)
        table_text = format_submissions_table(submissions, approved_hours)
        blocks = build_page_blocks(total_pages, page, table_text, view_type="submissions", user_id=user_id, user_name=user_name)
    elif view_type == "makeup":
        makeup_jobs = see_makeup_jobs()
        makeup_jobs, total_pages = page_block_formatting_helper(makeup_jobs, page)
        table_text = format_makeup_jobs(makeup_jobs)
        blocks = build_page_blocks(total_pages, page,table_text, view_type="makeup", user_name=user_name)
    elif view_type == "active":
        user_id = payload["user_id"]
        assignments = get_user_assignments(user_id)
        #print("Assignments:", assignments)
        assignments, total_pages = page_block_formatting_helper(assignments, page)
        #print("Paged Assignments:", assignments)
        table_text = format_user_active_assignments(assignments)
        blocks = build_page_blocks(total_pages, page, table_text, view_type="active", user_name=user_name, user_id=user_id)
    elif view_type == "available_job_id_makeup":
        job_id = int(payload["job_id"])
        result = get_available_jobs_by_id(job_id)
        if result["result"] == "ERROR":
            client.chat_postMessage(
                channel=channel_id,
                text=f"❌ Could not get available jobs for job ID {job_id}: {result['message']}"
            )
            return
        makeup_jobs, total_pages = page_block_formatting_helper(result["available_jobs"], page)
        table_text = format_makeup_jobs(makeup_jobs)
        blocks = build_page_blocks(total_pages, page,table_text, view_type="available_job_id_makeup", job_id=job_id, user_name=user_name)

    # Update original message
    client.chat_update(
        channel=channel_id,
        ts=payload_json["message"]["ts"],
        text=f"Updating....",
        blocks=blocks
    )

    return

@app.route("/slack/actions", methods=["POST"])
def handle_actions():
    payload = request.form["payload"]
    payload_json = json.loads(payload)

    channel_id = payload_json["channel"]["id"]

    client.chat_update(
        channel=channel_id,
        ts=payload_json["message"]["ts"],
        text ="Getting Next Page...",
    )
    threading.Thread(

        target=handle_actions_background,
        args=(payload,)
    ).start()

    return Response(), 200

def get_my_hour_submissions_background(user_id, channel_id):
    submissions, approved_hours = get_user_submissions(user_id)
    page = 1
    submissions, total_pages = page_block_formatting_helper(submissions, page)
    table_text = format_submissions_table(submissions, approved_hours)
    blocks = build_page_blocks(total_pages, page, table_text, view_type="submissions", user_id=user_id)

    #print(blocks)
    #submissions_message = format_submissions_table(submissions, approved_hours)
    client.chat_postMessage(
        channel=channel_id,
        text="Here are your submissions", 
        blocks=blocks
    )

@app.route('/get-my-hour-submissions', methods=['GET', 'POST'])
def get_my_hour_submissions_api():
    data = request.form
    user_id = data.get('user_id')
    channel_id = data.get('channel_id')
    user_name = data.get('user_name')
    message = f"Getting hour submissions for {user_name}"
    response = client.chat_postMessage(channel=channel_id, text=message)

    threading.Thread(
        target=get_my_hour_submissions_background,
        args=(user_id, channel_id)
    ).start()

    return Response(), 200

house_mnager_channel_id = os.getenv("HOUSE_MANAGER_CHANNEL_ID")
def update_approved_hours_background():
    # Placeholder for actual update logic
    # For now, just simulate a delay

    all_user_hours = sync_hours()
    message = format_all_user_hours_table(all_user_hours)
    client.chat_postMessage(
        channel=house_mnager_channel_id, #house manager channel for hour postings
        text=message
    )



ADMINS = os.getenv("ADMIN_USER_IDS").split(",")
@app.route('/update-approved-hours', methods=['POST', 'GET'])
def update_approved_hours_api():
    data = request.form
    #print(data)
    user_id = data.get('user_id')
    if user_id not in ADMINS:
        return jsonify({
            "response_type": "ephemeral",
            "text": "❌ You do not have permission to perform this action."
        }), 403
    channel_id = "C0A4RQ854H3" #data.get('channel_id')
    message = f"Admin is syncing approved hours."
    response = client.chat_postMessage(channel=channel_id, text=message)

    threading.Thread(
        target=update_approved_hours_background,
        args=[]
    ).start()

    return Response(), 200

def generate_user_table_background(channel_id):
    message = f"Generated user table"
    response = client.users_list()
    #print(response)
    user_tuples = [
        (
            user.get("profile", {}).get("display_name_normalized")
            or user.get("profile", {}).get("real_name_normalized")
            or user.get("name")
            or user["id"],
            user["id"],
        )
        for user in response["members"]
        if not user.get("deleted", False)
    ]

    #print(user_tuples)
    generate_user_table(user_tuples)
    response = client.chat_postMessage(channel=channel_id, text=message)

@app.route('/generate-user-table', methods=['POST'])
def generate_user_table_api():
    data = request.form
    user_id = data.get('user_id')
    #print(user_id)
    if user_id not in ADMINS:
        return jsonify({
            "response_type": "ephemeral",
            "text": "❌ You do not have permission to perform this action."
        }), 403
    channel_id = data.get('channel_id')
    message = f"Creating user table..."
    response = client.chat_postMessage(channel=channel_id, text=message)
    #print(data)

    threading.Thread(
        target=generate_user_table_background,
        args=(channel_id,)
    ).start()
    

    #ping witness that job person had them as the witness
    return Response(), 200


def get_available_jobs_of_this_id_background(channel_id, job_id):
    result = get_available_jobs_by_id(job_id)
    if result["result"] == "ERROR":
        client.chat_postMessage(
            channel=channel_id,
            text=f"❌ Could not get available jobs for job ID {job_id}: {result['message']}"
        )
        return
    available_jobs = result["available_jobs"]

    makeup_jobs, total_pages = page_block_formatting_helper(available_jobs, 1)
    table_text = format_makeup_jobs(makeup_jobs)
    #print(table_text)
    blocks = build_page_blocks(total_pages, 1,table_text, view_type="available_job_id_makeup", job_id=job_id, user_name=None)
    client.chat_postMessage(
        channel=channel_id,
        text=f"Makeup Jobs of {job_id}",
        blocks=blocks
    )


@app.route('/get-available-jobs-of-this-id', methods=['POST'])
def get_available_jobs_of_this_id_api():
    data = request.form
    user_id = data.get('user_id')
    job_id = int(data.get('text').split()[-1])  # Extract job_id from the last part of the text
    channel_id = data.get('channel_id')
    message = f"Getting available jobs for job ID: {job_id}"
    response = client.chat_postMessage(channel=channel_id, text=message)
    #print(data)

    threading.Thread(
        target=get_available_jobs_of_this_id_background,
        args=(channel_id, job_id)
    ).start()
    
    #ping witness that job person had them as the witness
    return Response(), 200

def get_my_assignments_background(user_id, channel_id):
    assignments = get_user_assignments(user_id)
    #print("Assignments:", assignments)
    page = 1
    assignments, total_pages = page_block_formatting_helper(assignments, page)
    #print("Paged Assignments:", assignments)
    table_text = format_user_active_assignments(assignments)
    blocks = build_page_blocks(total_pages, page, table_text, view_type="active", user_id=user_id)
    client.chat_postMessage(
        channel=user_id,
        text="Assignments:",
        blocks=blocks
    )   

@app.route('/get-my-assignments', methods=['GET', 'POST'])
def get_my_assignments_api():
    data = request.form
    user_id = data.get('user_id')
    channel_id = data.get('channel_id')
    #print(data)
    user_name = data.get('user_name')
    message = f"Getting {user_name}'s assignments"
    response = client.chat_postMessage(channel=user_id, text=message)

    threading.Thread(
        target=get_my_assignments_background,
        args=(user_id, channel_id)
    ).start()

    return Response(), 200


def see_makeup_jobs_background(channel_id):
    page = 1
    makeup_jobs = see_makeup_jobs()
    makeup_jobs, total_pages = page_block_formatting_helper(makeup_jobs, page)
    table_text = format_makeup_jobs(makeup_jobs)
    #print(table_text)
    blocks = build_page_blocks(total_pages, page,table_text, view_type="makeup")
    client.chat_postMessage(
        channel=channel_id,
        text="Makeup Jobs",
        blocks=blocks
    )

@app.route('/see-makeup-jobs', methods=['GET', 'POST'])
def see_makeup_jobs_api():
    data = request.form
    user_id = data.get('user_id')
    channel_id = data.get('channel_id')
    message = f"Getting available makeup jobs"
    response = client.chat_postMessage(channel=channel_id, text=message)

    threading.Thread(
        target=see_makeup_jobs_background,
        args=(channel_id,)
    ).start()

    return Response(), 200

#SCHEDULER TO RUN STUFF PERIODICALLY
def send_expiring_job_reminders():
    #print("Sending expiring job reminders...")
    expiring_jobs = get_expiring_jobs()
    #(expiring_jobs)
    for job in expiring_jobs:
        text = f"⚠️ Job *{job['job_name']}* is expiring in a few hours! Please submit your hours, otherwise you will forfeit the hours for this job."
        client.chat_postMessage(channel=job['slack_user_id'], text=text)

@app.route('/run-expiring-jobs', methods=['GET', 'POST'])
def run_expiring_job_reminders_api():
    #print("Running expiring job reminders...")
    client.chat_postMessage(channel=house_mnager_channel_id, text="Cron Job: Running expiring job reminders...")
    send_expiring_job_reminders()
    return Response(), 200


def expire_incomplete_jobs():
    expire_makeup_jobs()
    expire_assignments()
    return

@app.route('/expire-incomplete-jobs', methods=['GET', 'POST'])
def expire_incomplete_jobs_api():
    print("Expiring incomplete jobs...")
    client.chat_postMessage(channel=house_mnager_channel_id, text="Cron Job: Expiring incomplete jobs...")
    expire_incomplete_jobs()
    return Response(), 200


@app.route("/ping")
def ping():
    return "pong", 200



if __name__ == '__main__':
    # scheduler = BackgroundScheduler()
    # scheduler.add_job(send_expiring_job_reminders, 'cron', hour=1, minute=23)  # 9 AM daily
    # scheduler.add_job(expire_incomplete_jobs, 'cron', hour=0, minute=0)  # Midnight daily
    # scheduler.start()
    app.run(debug=True)