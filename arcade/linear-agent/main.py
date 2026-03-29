"""AG2 agent that manages Linear issues via Arcade SDK. See README.md for setup and usage."""

import datetime
import os

from arcadepy import Arcade
from autogen import AssistantAgent, UserProxyAgent

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
    return result.output if result.output else {}


# ---------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------


def list_issues(assignee: str = "@me", state: str = None, limit: int = 50) -> dict:
    """List Linear issues assigned to a user.
    - assignee: '@me' for current user, or a name/email for someone else
    - state: filter by workflow state (e.g. 'In Progress', 'Todo', 'Backlog')
    - limit: max number of issues to return (max 50)
    """
    inputs: dict = {"assignee": assignee, "limit": limit}
    if state:
        inputs["state"] = state
    return call_arcade_tool("Linear.ListIssues", inputs)


def get_issue(issue_id: str) -> dict:
    """Fetch current field values of a single Linear issue by identifier (e.g. 'ENG-869')."""
    return call_arcade_tool("Linear.GetIssue", {"issue_id": issue_id})


def update_issue(
    issue_id: str,
    title: str = None,
    priority: str = None,
    assignee: str = None,
    due_date: str = None,
    description: str = None,
    state: str = None,
) -> dict:
    """Update fields of an existing Linear issue. Only provided fields are changed.
    - issue_id: identifier like 'ENG-869'
    - priority: none | urgent | high | medium | low (case-insensitive)
    - due_date: YYYY-MM-DD format
    """
    inputs: dict = {"issue_id": issue_id}
    if title is not None:
        inputs["title"] = title
    if priority is not None:
        inputs["priority"] = priority.lower()
    if assignee is not None:
        inputs["assignee"] = assignee
    if due_date is not None:
        inputs["due_date"] = due_date
    if description is not None:
        inputs["description"] = description
    if state is not None:
        inputs["state"] = state
    return call_arcade_tool("Linear.UpdateIssue", inputs)


def create_issue(
    title: str,
    team: str,
    priority: str,
    description: str = "",
    assignee: str = "@me",
    due_date: str = None,
) -> dict:
    """Create a new Linear issue.
    - team: team name or key (e.g. 'AG2', 'ENG') — not an email
    - assignee: name, email, or '@me' for the current user
    - priority: none | urgent | high | medium | low (case-insensitive)
    - due_date: YYYY-MM-DD format
    - description: optional markdown text
    """
    inputs: dict = {
        "title": title,
        "team": team,
        "priority": priority.lower(),
        "assignee": assignee,
    }
    if description:
        inputs["description"] = description
    if due_date:
        inputs["due_date"] = due_date
    return call_arcade_tool("Linear.CreateIssue", inputs)


# ---------------------------------------------------------------------
# Agent setup
# ---------------------------------------------------------------------

llm_config = {
    "config_list": [{"model": "gpt-4o", "api_key": os.environ["OPENAI_API_KEY"]}],
}

_today = datetime.date.today().strftime("%Y-%m-%d")

_SYSTEM_MESSAGE = (
    f"Today's date is {_today}. Always use this year when resolving relative dates "
    f"(e.g. 'March 17th' → '{_today[:4]}-03-17'). due_date must be in YYYY-MM-DD format.\n\n"
    "You are a helpful assistant that manages Linear issues via Arcade tools. "
    "Use the provided tools to complete the user's requests.\n\n"
    "LISTING ISSUES:\n"
    "Use list_issues() to fetch issues. Pass assignee='@me' for the current user, or a name/email "
    "for someone else. Pass state to filter (e.g. 'In Progress', 'Todo'). "
    "Always display results as a numbered list in this format:\n"
    "  1. [ENG-123] Title\n"
    "     Status: In Progress | Priority: High | Assignee: john@example.com\n"
    "     Team: Engineering\n"
    "Group issues by State if multiple states are present. "
    "Show a summary line at the end: 'Total: N issues'.\n\n"
    "GETTING ISSUE DETAILS:\n"
    "When the user asks about a specific issue's fields (due date, status, assignee, etc.), "
    "always call get_issue() to fetch current data — never answer from memory.\n\n"
    "UPDATING ISSUES:\n"
    "Use update_issue() to change fields on an existing issue. "
    "Only pass the fields that need to change. Never use create_issue to update an existing issue.\n\n"
    "CREATING ISSUES:\n"
    "Before calling create_issue, always show a preview and end with TERMINATE:\n"
    "---\n"
    "Title: <title>\n"
    "Team: <team>\n"
    "Priority: <priority>\n"
    "Assignee: <assignee>\n"
    "Due date: <due_date or 'None'>\n"
    "Description: <description or 'None'>\n"
    "---\n"
    "Only call create_issue after the user explicitly confirms. "
    "If the user requests changes, update the preview and end with TERMINATE again.\n\n"
    "AFTER COMPLETING ANY TASK:\n"
    "End your reply with TERMINATE. Do not ask follow-up questions."
)

assistant = AssistantAgent(
    name="LinearAssistant",
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
        list_issues,
        "List Linear issues. Filter by assignee ('@me' or name/email), state, and limit.",
    ),
    (
        get_issue,
        "Get current field values of a single Linear issue by its identifier (e.g. 'ENG-869').",
    ),
    (
        update_issue,
        "Update fields of an existing Linear issue. Only provided fields are changed.",
    ),
    (
        create_issue,
        "Create a new Linear issue with title, team, priority, and optional fields.",
    ),
]:
    user_proxy.register_for_execution()(func)
    assistant.register_for_llm(description=description)(func)

# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

if __name__ == "__main__":
    print("Linear Assistant ready. Type your request (or 'exit' to quit).")
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
