import random

from dotenv import load_dotenv

load_dotenv()

from email_utils import (
    get_gmail_service,
    get_user_email,
    fetch_emails,
    parse_email_data,
    group_emails_by_sender,
    mark_email_as_read,
    archive_email,
    trash_email,
    fetch_email_thread,
)
import autogen
from autogen.agentchat import initiate_group_chat
from autogen import ConversableAgent, LLMConfig
from autogen.agentchat.group import (
    RevertToUserTarget,
)
from autogen.agentchat.group.patterns import DefaultPattern

llm_config = LLMConfig(
    {"api_type": "openai", "model": "gpt-5-nano"},
    cache_seed=42,
    temperature=1,
    tools=[],
    timeout=120,
)

max_unread_emails_limit = 20
is_mock_read_email = False


# -------------- Connect to Google Email --------------
# Get the Gmail service (this will prompt you to authenticate if needed)
gmail_service = get_gmail_service()

# Get the logged-in user's email address
user_email = get_user_email(gmail_service)
print(f"Logged in as: {user_email}")

# Fetch unread emails
page_token = None
unread_emails = []
# Loop through pages to fetch all unread emails
while True:
    messages, page_token = fetch_emails(
        gmail_service, page_token, filter_by=["UNREAD", "CATEGORY_PERSONAL"]
    )
    if not messages:
        break

    for msg in messages:
        email_data = parse_email_data(gmail_service, msg)
        if email_data:
            unread_emails.append(email_data)
        if len(unread_emails) >= max_unread_emails_limit:
            break
    if not page_token or len(unread_emails) >= max_unread_emails_limit:
        break

# group_by_sender
grouped_emails = group_emails_by_sender(unread_emails)
sorted_grouped_emails_tuple = sorted(
    grouped_emails.items(), key=lambda x: len(x[1]), reverse=True
)

sorted_grouped_emails = {}
for sender, emails in sorted_grouped_emails_tuple:
    # strip email adress in "<>" from example "CGE-UAW at Penn State <cgepsu@138327365.mailchimpapp.com>""
    stripped_sender = sender.split("<")[1].split(">")[0] if "<" in sender else sender
    sorted_grouped_emails[stripped_sender] = emails


read_email_ids = []


# -------- First, sort emails by sender. Provide the option to mark all emails from a specific sender as read. --------
def mark_all_from_sender_as_read(sender: str) -> str:
    try:
        emails = sorted_grouped_emails[sender]
    except KeyError:
        return f"No emails found from {sender}."
    # print warning message: sender, first 10 email subjects and random 3 email bodies
    print("*" * 100)
    print("*" * 100)
    print(f"WARNING: Marking all emails as read from {sender}")
    for email in emails[:10]:
        print(f"Selected Email Subject: {email['subject']}")

    random_emails = random.sample(emails, 1)
    for email in random_emails:
        print(f"Selected Email Body: {email['body']}")

    print("*" * 100)
    print("*" * 100)
    user_input = input("Do you want to continue? (yes/no): ")
    if user_input.lower() == "yes" or user_input.lower() == "y":
        print("Marking all emails as read...")
        # mark all emails as read
        for email in emails:
            read_email_ids.append(email["message_id"])
            if not is_mock_read_email:
                mark_email_as_read(gmail_service, email["message_id"])
        return "All emails marked as read successfully!"
    else:
        return "Operation cancelled by user."


user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="ALWAYS",
    max_consecutive_auto_reply=1,
    code_execution_config=False,
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
)

filter_agent = ConversableAgent(
    name="filter_agent",
    llm_config=llm_config,
    system_message="""You are an email bulk-action assistant.
You have been given a list of senders with the number of unread emails and sample subjects from each.
This is the complete data you have — you cannot fetch additional emails or access the inbox directly.

Your only available action is mark_all_from_sender_as_read, which marks all unread emails from a given sender as read.

Your workflow:
1. Review the provided sender list and identify low-priority senders whose emails can be safely marked as read in bulk (e.g. newsletters, notifications, automated alerts).
2. If you find low-priority senders: present your recommendations, ask for confirmation, then call mark_all_from_sender_as_read for each confirmed sender.
3. If no low-priority senders are found, immediately reply with TERMINATE — do not ask follow-up questions.
4. After processing all confirmed senders, reply with TERMINATE.

Do not claim capabilities you don't have. If the user asks for something outside your scope (e.g. listing all emails, archiving, deleting), explain that this step only handles bulk mark-as-read by sender, and that individual email actions are available in the next step.""",
    functions=[mark_all_from_sender_as_read],
)

# construct input string
input_str = ""
for sender, emails in sorted_grouped_emails.items():
    if len(emails) <= 1:
        continue
    input_str += f"{sender}: {len(emails)} emails\n"
    input_str += "First 5 email subjects:\n"
    for i, email in enumerate(emails[:10]):
        input_str += f"{i}. {email['subject']}\n"
    input_str += "\n"
    print("-" * 100)
    print("\n")

# Only proceed with filtering if there are senders with multiple emails
if input_str.strip():
    agent_pattern = DefaultPattern(
        agents=[
            filter_agent,
        ],
        initial_agent=filter_agent,
        user_agent=user_proxy,
        group_after_work=RevertToUserTarget(),
    )

    try:
        result, final_context, last_agent = initiate_group_chat(
            pattern=agent_pattern,
            messages=input_str,
            max_rounds=30,
        )
    except (IndexError, ValueError) as e:
        print(f"Skipping bulk filtering due to message processing error: {e}")
        print(
            "You may want to try using a different LLM provider or update the autogen library."
        )
else:
    print("No senders with multiple emails found. Skipping bulk filtering.")

# remove read emails from unread_emails
for email in unread_emails:
    if email["message_id"] in read_email_ids:
        unread_emails.remove(email)


# -------------- Part 2: Email Assistant to help with reading emails one by one, marking as read, and drafting responses --------------
def list_emails(count: int = 10) -> str:
    """List unread emails with their ID, sender, subject, and received time. Use count to limit results."""
    emails_to_show = unread_emails[:count]
    if not emails_to_show:
        return "No unread emails."
    result = f"Showing {len(emails_to_show)} of {len(unread_emails)} unread emails:\n\n"
    for i, email in enumerate(emails_to_show, 1):
        result += f"{i}. [{email['message_id']}]\n"
        result += f"   From: {email['from']}\n"
        result += f"   Subject: {email['subject']}\n"
        result += f"   Received: {email.get('received_time', 'N/A')}\n\n"
    return result


def mark_one_email_as_read(email_id: str) -> str:
    read_email_ids.append(email_id)
    if is_mock_read_email:
        return "Successfully marked email as read."
    return mark_email_as_read(
        gmail_service, email_id
    )  # send request to mark email as read


def get_email_body(email_id: str) -> str:
    for email in unread_emails:
        if email["message_id"] == email_id:
            return email["body"]
    return "Email not found."


def get_full_thread(email_thread_id: str) -> str:
    """Get the full thread of an email as a formatted string for the agent."""
    thread_emails = fetch_email_thread(gmail_service, email_thread_id)
    if not thread_emails:
        return "No thread found or error fetching thread."

    # Format the thread as a readable string for the agent
    formatted_thread = "Email Thread:\n" + "=" * 80 + "\n"
    for i, email in enumerate(thread_emails, 1):
        formatted_thread += f"\n--- Email {i} of {len(thread_emails)} ---\n"
        formatted_thread += f"Message ID: {email.get('message_id', 'N/A')}\n"
        formatted_thread += f"From: {email.get('from', 'N/A')}\n"
        formatted_thread += f"To: {email.get('to', 'N/A')}\n"
        formatted_thread += f"Date: {email.get('date', 'N/A')}\n"
        formatted_thread += f"Subject: {email.get('subject', 'N/A')}\n"
        if email.get("attachments"):
            formatted_thread += f"Attachments: {', '.join(email['attachments'])}\n"
        formatted_thread += f"\nBody:\n{email.get('body', 'No body content')}\n"
        formatted_thread += "-" * 80 + "\n"

    return formatted_thread


def archive_one_email(email_id: str) -> str:
    """Archive an email — removes it from Inbox but keeps it in All Mail."""
    if is_mock_read_email:
        return "Successfully archived email (mock)."
    return archive_email(gmail_service, email_id)


def trash_one_email(email_id: str) -> str:
    """Move an email to Trash. It will be permanently deleted after 30 days."""
    if is_mock_read_email:
        return "Successfully moved email to trash (mock)."
    return trash_email(gmail_service, email_id)


email_assistant = ConversableAgent(
    name="email_assistant",
    llm_config=llm_config,
    system_message="""You are an email assistant with access to the user's unread emails.
You have been provided a list of unread emails with their IDs, senders, and subjects.

You can perform the following actions using your tools:
- list_emails(count): list unread emails with ID, sender, subject, and date. Default count is 10.
- mark_one_email_as_read: mark a single email as read (stays in inbox)
- archive_one_email: remove email from inbox, keep it in All Mail (reversible)
- trash_one_email: move email to Trash (deleted after 30 days)
- get_email_body: fetch the body of a specific email
- get_full_thread: fetch the full conversation thread of an email

Your workflow:
1. Classify ALL provided emails into:
   - "Mark as read": low-priority, no action needed
   - "Archive": can be cleaned up from inbox
   - "Read full email to decide": needs review before acting
   Confirm your classification with the user before taking any action.

2. After retrieving full emails, summarize key points briefly for each.

3. If any email requires a response, ask the user if they want to draft one.
   Get the full thread first, then draft a response based on user intent. Put the draft in ```txt``` format.

Important: only call tools after the user confirms. Never perform bulk actions without explicit confirmation.
""",
    functions=[
        list_emails,
        mark_one_email_as_read,
        archive_one_email,
        trash_one_email,
        get_email_body,
        get_full_thread,
    ],
)

# construct input string
email_str = ""
for email in unread_emails:
    email_str += f"Email ID: {email['message_id']}\n"
    email_str += f"Thread ID: {email['thread_id']}\n"
    email_str += f"From: {email['from']}\n"
    email_str += f"Subject: {email['subject']}\n"
    email_str += "\n"

# Only proceed if there are unread emails to process
if email_str.strip():
    agent_pattern = DefaultPattern(
        agents=[
            email_assistant,
        ],
        initial_agent=email_assistant,
        user_agent=user_proxy,
        group_after_work=RevertToUserTarget(),
    )

    try:
        result, final_context, last_agent = initiate_group_chat(
            pattern=agent_pattern,
            messages=email_str,
            max_rounds=30,
        )
    except (AssertionError, IndexError, ValueError) as e:
        print(f"Skipping email assistant chat due to error: {e}")
else:
    print("No unread emails remaining to process after filtering.")
