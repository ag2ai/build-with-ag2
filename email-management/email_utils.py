import base64
import os
from typing import Dict, List, Optional, Union, Tuple
from collections import defaultdict
from googleapiclient.discovery import build, Resource
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from datetime import datetime

# several functions are adapted from https://github.com/Tylerbryy/zinbo/blob/main/src/gmail_service.py

SCOPES = ["https://mail.google.com/"]


def get_user_email(gmail: Resource) -> str:
    profile = gmail.users().getProfile(userId="me").execute()
    return profile.get("emailAddress", "")


from googleapiclient.discovery import Resource

from bs4 import BeautifulSoup  # Install with: pip install beautifulsoup4


def extract_email_body_and_attachments(
    parts: List[Dict[str, Union[str, Dict]]],
    strip_html: bool = False,
    exclude_prev_msg: bool = False,
) -> (str, List[str]):
    """
    Extracts and decodes the email body, preferring 'text/plain' but falling back to 'text/html' if needed.
    Also extracts attachment filenames.

    Args:
        parts (List[Dict[str, Union[str, Dict]]]): List of email parts from Gmail API.
        strip_html (bool): If True, removes HTML tags and returns plain text.
        exclude_prev_msg (bool): If True, removes previous messages from the body (usually prefixed with '>').

    Returns:
        Tuple[str, List[str]]: Decoded email body and a list of attachment filenames.
    """
    body = ""
    attachments = []
    for part in parts:
        mime_type = part.get("mimeType", "")
        filename = part.get("filename", "")
        data = part.get("body", {}).get("data", "")

        # Extract plain text or HTML body
        if data:
            try:
                decoded_body = base64.urlsafe_b64decode(data.encode("ASCII")).decode(
                    "utf-8"
                )

                if mime_type == "text/plain" and not body:  # Prefer plain text
                    body = decoded_body
                elif (
                    mime_type == "text/html" and not body
                ):  # Use HTML if no plain text is found
                    body = decoded_body
            except Exception as decode_error:
                print(f"Failed to decode email body: {decode_error}")

        # Extract attachments
        if filename:
            if "body" in part and "attachmentId" in part["body"]:
                attachments.append(filename)

    # Convert HTML to plain text if strip_html=True
    if strip_html and body:
        soup = BeautifulSoup(body, "html.parser")
        body = soup.get_text(separator="\n").strip()

    # Remove previous messages in the thread (if exclude_prev_msg=True)
    if exclude_prev_msg and body:
        body_lines = body.splitlines()
        filtered_lines = []
        for line in body_lines:
            if line.startswith(">"):
                break  # Stop at the first quoted message
            filtered_lines.append(line)
        body = "\n".join(filtered_lines).strip()

    return body, attachments
    return body


def fetch_email_thread(
    gmail: Resource, thread_id: str
) -> List[Dict[str, Union[str, List[str]]]]:
    """
    Fetches all emails in a thread given a thread ID.

    Args:
        gmail (Resource): Gmail API service instance.
        thread_id (str): The thread ID of the email conversation.

    Returns:
        List[Dict[str, Union[str, List[str]]]]: List of email messages in the thread.
    """
    try:
        # Fetch the full thread details
        thread = (
            gmail.users()
            .threads()
            .get(userId="me", id=thread_id, format="full")
            .execute()
        )

        emails = []
        for message in thread.get("messages", []):
            email_data = {
                "message_id": message["id"],
                "thread_id": message["threadId"],
                "subject": next(
                    (
                        header["value"]
                        for header in message["payload"]["headers"]
                        if header["name"] == "Subject"
                    ),
                    "No Subject",
                ),
                "from": next(
                    (
                        header["value"]
                        for header in message["payload"]["headers"]
                        if header["name"] == "From"
                    ),
                    "Unknown",
                ),
                "to": next(
                    (
                        header["value"]
                        for header in message["payload"]["headers"]
                        if header["name"] == "To"
                    ),
                    "Unknown",
                ),
                "date": next(
                    (
                        header["value"]
                        for header in message["payload"]["headers"]
                        if header["name"] == "Date"
                    ),
                    "Unknown",
                ),
                "body": "",
                "attachments": [],
            }

            # Extract the email body (text/plain only)
            parts = message.get("payload", {}).get("parts", [])
            body, attachments = extract_email_body_and_attachments(
                parts, strip_html=True, exclude_prev_msg=True
            )
            email_data["body"] = body
            if len(attachments) > 0:
                email_data["attachments"] = attachments

            emails.append(email_data)

        return emails

    except Exception as e:
        print(f"Error fetching thread {thread_id}: {e}")
        return []


def fetch_emails(
    gmail: Resource,
    page_token: Optional[str],
    filter_by: Optional[Union[str, List[str]]] = ["UNREAD"],
) -> Tuple[List[Dict[str, Union[str, List[str]]]], Optional[str]]:
    try:
        results = (
            gmail.users()
            .messages()
            .list(
                userId="me",
                labelIds=filter_by if filter_by else [],
                pageToken=page_token,  # Include the page token in the request if there is one
            )
            .execute()
        )
    except Exception as e:
        print(f"Failed to fetch emails: {e}")
        return [], None

    messages: List[Dict[str, Union[str, List[str]]]] = results.get("messages", [])
    page_token = results.get("nextPageToken")
    return messages, page_token


def convert_timestamp_to_local(timestamp_ms):
    """
    Convert a Unix timestamp in milliseconds to local time.

    Args:
        timestamp_ms (int): Timestamp in milliseconds.

    Returns:
        str: Formatted local time as 'YYYY-MM-DD HH:MM:SS'.
    """
    # Convert milliseconds to seconds
    timestamp_s = timestamp_ms / 1000

    # Convert to local datetime
    local_dt = datetime.fromtimestamp(timestamp_s)

    # Format it as a readable string
    formatted_time = local_dt.strftime("%Y-%m-%d %H:%M:%S %Z")

    return formatted_time


def get_gmail_service():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def parse_email_data(
    gmail, message_info: Dict[str, Union[str, List[str]]]
) -> Dict[str, Union[str, List[str]]]:
    """Fetches and parses email data, including subject, sender, body, and attachments."""
    try:
        msg = (
            gmail.users()
            .messages()
            .get(userId="me", id=message_info["id"], format="full")
            .execute()
        )
    except Exception as e:
        print(f"Failed to fetch email data: {e}")
        return {}

    try:
        headers = msg["payload"]["headers"]
        subject = next(
            header["value"] for header in headers if header["name"] == "Subject"
        )
        to = next(header["value"] for header in headers if header["name"] == "To")
        sender = next(header["value"] for header in headers if header["name"] == "From")
        cc = next(
            (header["value"] for header in headers if header["name"] == "Cc"), None
        )
        msg_id = msg["id"]
        thread_id = msg["threadId"]
        receive_time = convert_timestamp_to_local(int(msg["internalDate"]))
    except Exception as e:
        print(f"Failed to parse email headers: {e}")
        return {}

    print(f"Fetched email - Subject: {subject}, Sender: {sender}")

    # Extract the plain text body
    parts = msg["payload"].get("parts", [])
    body, attachments = extract_email_body_and_attachments(
        parts, strip_html=True, exclude_prev_msg=False
    )

    # Parse email data
    email_data_parsed: Dict[str, Union[str, List[str]]] = {
        "message_id": msg_id,
        "thread_id": thread_id,
        "subject": subject,
        "to": to,
        "from": sender,
        "cc": cc,
        "received_time": receive_time,
        "labels": msg.get("labelIds", []),
        "body": body,
        "attachments": attachments,  # List of attachment filenames
    }

    return email_data_parsed


def group_emails_by_sender(
    email_list: List[Dict[str, Union[str, List[str]]]],
) -> Dict[str, List[Dict[str, Union[str, List[str]]]]]:
    """
    Groups emails by sender email.

    Args:
        email_list (List[Dict[str, Union[str, List[str]]]]): List of parsed email data.

    Returns:
        Dict[str, List[Dict[str, Union[str, List[str]]]]]: Dictionary with sender emails as keys
        and lists of corresponding emails as values.
    """
    grouped_emails = defaultdict(list)

    for email_data in email_list:
        sender = email_data.get(
            "from", "Unknown Sender"
        )  # Default to 'Unknown Sender' if missing
        grouped_emails[sender].append(email_data)

    return dict(grouped_emails)


def mark_email_as_read(gmail_service, message_id):
    """Marks an email as read by removing the 'UNREAD' label."""
    try:
        gmail_service.users().messages().modify(
            userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}
        ).execute()
        return f"Email {message_id} marked as read."
    except Exception as e:
        return f"Failed to mark email as read: {e}"
