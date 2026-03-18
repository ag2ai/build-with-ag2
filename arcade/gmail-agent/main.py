"""AG2 agent that manages Gmail via Arcade SDK.

Setup:
    pip install "ag2[openai]" arcadepy
    export OPENAI_API_KEY=...
    export ARCADE_API_KEY=...
    export ARCADE_USER_ID=your@email.com   # email used to sign up at arcade.dev

Example prompts:
    "Show my unread emails"
    "List emails from someone@example.com"
    "Search for emails about the Arcade partnership"
    "Show the full thread for this email"
    "Reply to this email: sounds good, see you then"
    "Archive all emails from newsletter@substack.com"
    "Trash this email"
    "Send an email to someone@example.com about scheduling a demo"
"""

import datetime
import os

from arcadepy import Arcade
from autogen import AssistantAgent, UserProxyAgent
from bs4 import BeautifulSoup


def _strip_html(text: str) -> str:
    """Parse HTML and extract plain text."""
    return BeautifulSoup(text, "html.parser").get_text(separator=" ", strip=True)


# ---------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------

arcade = Arcade(api_key=os.environ["ARCADE_API_KEY"])
ARCADE_USER_ID = os.environ["ARCADE_USER_ID"]

# ---------------------------------------------------------------------
# Arcade helper
# ---------------------------------------------------------------------


def call_arcade_tool(tool_name: str, inputs: dict) -> dict:
    """Authorize (if needed) and execute an Arcade tool, returning the output."""
    auth = arcade.tools.authorize(tool_name=tool_name, user_id=ARCADE_USER_ID)
    if auth.status != "completed":
        print(
            f"\n[Auth required] Visit this URL to authorize {tool_name}:\n  {auth.url}\n"
        )
        arcade.auth.wait_for_completion(auth.id)

    result = arcade.tools.execute(
        tool_name=tool_name,
        input=inputs,
        user_id=ARCADE_USER_ID,
    )
    if not result.output:
        return {}
    data = result.output.model_dump()
    return data.get("value") or {}


_SKIP_KEYS = {"html_body", "raw", "raw_message"}
_BODY_KEYS = {"body", "text_body", "content"}
_BODY_MAX_CHARS = 2000
_SLIM_KEYS = {"id", "from_", "subject", "date", "snippet", "thread_id", "label_ids"}


def _clean_body(text: str) -> str:
    """Strip HTML and truncate to _BODY_MAX_CHARS."""
    text = _strip_html(text)
    if len(text) > _BODY_MAX_CHARS:
        text = text[:_BODY_MAX_CHARS] + " …[truncated]"
    return text


def _clean_full(obj):
    """Full clean: drop skip keys, strip HTML from body fields, truncate."""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k in _SKIP_KEYS:
                continue
            cleaned = _clean_full(v)
            if k in _BODY_KEYS and isinstance(cleaned, str):
                cleaned = _clean_body(cleaned)
            result[k] = cleaned
        return result
    if isinstance(obj, list):
        return [_clean_full(i) for i in obj]
    if isinstance(obj, str):
        return _strip_html(obj) if "<" in obj and ">" in obj else obj
    return obj


def _slim_email(email: dict) -> dict:
    """Keep only metadata fields from a single email dict."""
    return {k: v for k, v in email.items() if k in _SLIM_KEYS}


def _clean_slim(data: dict) -> dict:
    """Slim clean for list/search: strip body from each email, keep metadata only."""
    emails = data.get("emails") or data.get("messages") or []
    threads = data.get("threads") or []
    if emails:
        return {"emails": [_slim_email(e) for e in emails]}
    if threads:
        return {
            "threads": threads,
            "num_threads": data.get("num_threads", len(threads)),
        }
    return {}


# ---------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------


def list_emails(
    sender: str = None, max_results: int = 50, is_unread: bool = False
) -> dict:
    """List emails from Gmail inbox.
    - sender: filter by sender email address (optional)
    - max_results: maximum number of emails to return (default 50)
    - is_unread: if True, return only unread emails
    """
    inputs: dict = {"max_results": max_results, "is_unread": is_unread}
    if sender:
        inputs["sender"] = sender
    return _clean_slim(call_arcade_tool("Gmail.ListEmails", inputs))


def get_thread(thread_id: str) -> dict:
    """Fetch the full conversation thread by thread ID."""
    return _clean_full(call_arcade_tool("Gmail.GetThread", {"thread_id": thread_id}))


def search_emails(
    subject: str = None,
    body: str = None,
    sender: str = None,
    date_range: str = None,
    max_results: int = 50,
) -> dict:
    """Search emails by subject, body keywords, sender, or date range.
    - subject: words to find in the subject
    - body: words to find in the body
    - sender: sender name or email
    - date_range: e.g. 'after:2026/03/01 before:2026/03/17'
    - max_results: max number of results (default 50)
    """
    inputs: dict = {"max_results": max_results}
    if subject:
        inputs["subject"] = subject
    if body:
        inputs["body"] = body
    if sender:
        inputs["sender"] = sender
    if date_range:
        inputs["date_range"] = date_range
    return _clean_slim(call_arcade_tool("Gmail.SearchThreads", inputs))


def mark_as_read(email_id: str) -> dict:
    """Mark an email as read by removing the UNREAD label."""
    return call_arcade_tool(
        "Gmail.ChangeEmailLabels",
        {"email_id": email_id, "labels_to_remove": ["UNREAD"]},
    )


def mark_as_unread(email_id: str) -> dict:
    """Mark an email as unread by adding the UNREAD label."""
    return call_arcade_tool(
        "Gmail.ChangeEmailLabels", {"email_id": email_id, "labels_to_add": ["UNREAD"]}
    )


def archive_email(email_id: str) -> dict:
    """Archive an email by removing the INBOX label (keeps in All Mail)."""
    return call_arcade_tool(
        "Gmail.ChangeEmailLabels", {"email_id": email_id, "labels_to_remove": ["INBOX"]}
    )


def trash_email(email_id: str) -> dict:
    """Move an email to Trash by its ID."""
    return call_arcade_tool("Gmail.TrashEmail", {"email_id": email_id})


def send_email(to: str, subject: str, body: str) -> dict:
    """Send a new email.
    - to: recipient email address
    - subject: email subject line
    - body: plain-text email body
    """
    return call_arcade_tool(
        "Gmail.SendEmail", {"recipient": to, "subject": subject, "body": body}
    )


def create_draft(to: str, subject: str, body: str) -> dict:
    """Save an email as a draft without sending.
    - to: recipient email address
    - subject: email subject line
    - body: plain-text email body
    """
    return call_arcade_tool(
        "Gmail.WriteDraftEmail", {"recipient": to, "subject": subject, "body": body}
    )


def reply_to_email(email_id: str, body: str) -> dict:
    """Reply to an email (sender only).
    - email_id: ID of the message to reply to
    - body: plain-text reply body
    """
    return call_arcade_tool(
        "Gmail.ReplyToEmail",
        {
            "reply_to_message_id": email_id,
            "body": body,
            "reply_to_whom": "ONLY_THE_SENDER",
        },
    )


def reply_all_to_email(email_id: str, body: str) -> dict:
    """Reply to all recipients of an email.
    - email_id: ID of the message to reply to
    - body: plain-text reply body
    """
    return call_arcade_tool(
        "Gmail.ReplyToEmail",
        {"reply_to_message_id": email_id, "body": body, "reply_to_whom": "EVERYONE"},
    )


# ---------------------------------------------------------------------
# Agent setup
# ---------------------------------------------------------------------

llm_config = {
    "config_list": [{"model": "gpt-4o", "api_key": os.environ["OPENAI_API_KEY"]}],
    "max_tokens": 4096,
}

_today = datetime.date.today().strftime("%Y-%m-%d")

_SYSTEM_MESSAGE = (
    f"Today's date is {_today}.\n\n"
    "You are a helpful Gmail assistant that manages emails via Arcade tools. "
    "Use the provided tools to complete the user's requests.\n\n"
    "LISTING EMAILS:\n"
    "Always call list_emails() and display results immediately — never ask 'would you like to view them?' first. "
    "Display as a numbered list in this format:\n"
    "  1. From: sender@example.com | Subject: Subject line | Date: YYYY-MM-DD\n"
    "     Snippet: first line of email body...\n"
    "Group by sender if multiple senders are present. "
    "Show 'Total: N emails' at the end.\n\n"
    "READING THREAD:\n"
    "Call get_thread() with the thread_id to show the full conversation. "
    "Display each message with sender, date, and body in chronological order.\n\n"
    "SEARCHING:\n"
    "Use search_emails() with subject, body, sender, or date_range parameters. "
    "Extract the relevant fields from the user's query and pass them separately. "
    "Results return threads with 'id', 'snippet' fields. Display as a numbered list with snippet. "
    "To read a full thread use get_thread() with the thread id. "
    "If results equal max_results (meaning there may be more), ask the user: "
    "'Found N results (showing first N). Would you like to see more?' and end with TERMINATE. "
    "If they confirm, call search_emails() again with a higher max_results.\n\n"
    "SENDING / REPLYING:\n"
    "Before executing, always show a preview and end with TERMINATE:\n"
    "---\n"
    "To: <recipient>\n"
    "Subject: <subject>\n"
    "Body: <body>\n"
    "---\n"
    "Only send after the user explicitly confirms with 'yes', 'send it', or 'confirm'. "
    "If the user requests changes, update the preview and end with TERMINATE again.\n\n"
    "DESTRUCTIVE ACTIONS (trash):\n"
    "Always show a confirmation prompt and end with TERMINATE before trashing. "
    "Only call trash_email() after explicit user confirmation.\n\n"
    "SAFE ACTIONS (archive, mark as read/unread):\n"
    "Execute directly without asking for confirmation.\n\n"
    "AFTER COMPLETING ANY TASK:\n"
    "End your reply with TERMINATE. Do not ask follow-up questions."
)

assistant = AssistantAgent(
    name="GmailAssistant",
    llm_config=llm_config,
    system_message=_SYSTEM_MESSAGE,
    is_termination_msg=lambda msg: "TERMINATE" in (msg.get("content") or ""),
)

user_proxy = UserProxyAgent(
    name="User",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=20,
    is_termination_msg=lambda msg: "TERMINATE" in (msg.get("content") or ""),
    code_execution_config=False,
)

for func, description in [
    (
        list_emails,
        "List emails from Gmail. Filter by sender, unread status, and max results.",
    ),
    (get_thread, "Get the full conversation thread by thread ID."),
    (search_emails, "Search emails by subject, body keywords, sender, or date range."),
    (mark_as_read, "Mark an email as read by its ID."),
    (mark_as_unread, "Mark an email as unread by its ID."),
    (
        archive_email,
        "Archive an email by its ID (removes from inbox, keeps in All Mail).",
    ),
    (trash_email, "Move an email to Trash by its ID."),
    (send_email, "Send a new email to a recipient with subject and body."),
    (create_draft, "Save a new email as a draft without sending."),
    (reply_to_email, "Reply to an email (sender only) by message ID with a body."),
    (
        reply_all_to_email,
        "Reply to all recipients of an email by message ID with a body.",
    ),
]:
    user_proxy.register_for_execution()(func)
    assistant.register_for_llm(description=description)(func)

# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

if __name__ == "__main__":
    print("Gmail Assistant ready. Type your request (or 'exit' to quit).")
    while True:
        message = input("\nYou: ").strip()
        if not message or message.lower() in ("exit", "quit", "bye"):
            print("Goodbye!")
            break
        user_proxy.initiate_chat(
            recipient=assistant,
            message=message,
            clear_history=False,
        )
        print("\nAnything else? (type your next request or 'exit' to quit)")
