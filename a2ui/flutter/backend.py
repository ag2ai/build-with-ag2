#!/usr/bin/env python3
"""A2UI + A2A backend for the Flutter demo. Agent runs on port 9000."""

import os
import sys
from pathlib import Path

from typing import Annotated

from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from autogen.a2a import A2aAgentServer, CardSettings
from autogen import LLMConfig
from autogen.agents.experimental.a2ui import A2UIAgent, A2UIAction

load_dotenv()

api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
if not api_key:
    print("Set GOOGLE_GEMINI_API_KEY in .env to run this demo.")
    sys.exit(1)

llm_config = LLMConfig(
    {
        "api_type": "google",
        "model": "gemini-3.1-flash-lite-preview",
    }
)

# ─── Custom catalog (optional) ───
# If you want custom components like LinkedInPost/XPost, provide a catalog JSON.
# Note that A2UIAgent always has the basic catalog (Column, Row, Card, Text, Image, Button, etc.)
CATALOG_PATH = Path(__file__).parent / "social_catalog.json"

CUSTOM_RULES = """**CUSTOM COMPONENT RULES:**
- For 'LinkedInPost', populate ALL fields: authorName, authorHeadline, authorAvatarUrl, body, hashtags, mediaChild, likes, comments, reposts.
- For 'XPost', populate ALL fields: authorName, authorHandle, authorAvatarUrl, verified, body, mediaChild, replies, reposts, likes, views, bookmarks.
- Engagement metrics are integers, not strings.
- Create Image components separately and reference by ID in mediaChild.
- For ALL Image components used as media or hero images, set "variant": "header" and "fit": "cover" so they fill the full width.
- For avatar images, set "variant": "avatar".
"""


# ─── Tool ───
def schedule_posts(
    time: Annotated[str | list, "The time to schedule posts for"] = "not specified",
) -> str:
    """Schedule the marketing posts (email, LinkedIn, X) for publishing at the given time."""
    # ChoicePicker may return a list; extract first value
    if isinstance(time, list):
        time = time[0] if time else "not specified"
    print(f"  [schedule_posts] Scheduling all posts for {time}")
    return (
        f"All three posts have been scheduled for {time} tomorrow!\n\n"
        f"- Email: queued for {time}\n"
        f"- LinkedIn: scheduled for {time}\n"
        f"- X/Twitter: scheduled for {time}"
    )


# ─── A2UI agent ───
a2ui_agent = A2UIAgent(
    name="marketing_previewer",
    system_message=(
        "You are a marketing content designer. You work in a multi-step flow:\n\n"
        "## STEP 1: Generate previews (initial request or rewrite)\n"
        "When you receive a product brief OR a 'rewrite_previews' action, create "
        "THREE preview cards in a single A2UI response:\n\n"
        "1. **Email preview**: Use basic catalog components in a Card:\n"
        "   To:, Subject:, Divider, Image, headline (h2), body, Divider, CTA Button (use openUrl functionCall action to link to the shop URL), "
        "Divider, footer (caption)\n\n"
        "2. **LinkedIn preview**: LinkedInPost with ALL fields populated\n\n"
        "3. **X/Twitter preview**: XPost with ALL fields populated, body under 280 chars\n\n"
        "Use a Column as root with section headers (Text with variant 'h2') between previews.\n"
        "IMPORTANT: Do NOT use markdown syntax (##, **, etc.) in Text component values. "
        "Use the 'variant' field for styling instead (h1, h2, h3, caption, body).\n"
        "At the bottom, add a Row with Approve and Rewrite buttons.\n\n"
        "IMPORTANT: Always use surfaceId 'marketing' for all surfaces.\n\n"
        "## STEP 2: Approved — show scheduling options on a NEW surface\n"
        "When you receive an 'approve_previews' action, create a NEW surface with "
        "surfaceId 'scheduling' (do NOT touch the 'marketing' surface). Use the same catalogId.\n"
        "Then updateComponents on 'scheduling' with:\n"
        "- Text (h2): 'Previews Approved! Choose a schedule:'\n"
        "- Row with three quick-schedule buttons: 9 AM, 10 AM, 2 PM (static context)\n"
        "- A ChoicePicker with id 'custom_time' for selecting a custom time, with options "
        "from 9:00 AM to 5:00 PM in 1-hour increments. Use variant 'mutuallyExclusive' and "
        "value bound to data model path '/customTime'. Each option should have a label "
        "like '9:00 AM' and value '9:00 AM'.\n"
        "- A 'Schedule Custom' button that reads the selected time via {path: '/customTime'}\n"
        "- Include an updateDataModel on 'scheduling' to initialize {customTime: '12:00 PM'}\n\n"
        "IMPORTANT: The 'marketing' surface with previews must remain untouched when approving.\n\n"
        "IMPORTANT: When the brief mentions image URLs, use those exact URLs.\n\n"
        "IMPORTANT: For ALL content Image components, use this product image URL: "
        "http://localhost:9000/images/bottle-hero.png\n"
        "IMPORTANT: For ALL avatar Image components, use this avatar image URL: "
        "http://localhost:9000/images/AG2-square.png\n"
        "Do NOT invent or guess image URLs. Always use the URL above.\n\n"
        "First write a short text summary, then the A2UI JSON."
    ),
    llm_config=llm_config,
    custom_catalog=CATALOG_PATH,
    custom_catalog_rules=CUSTOM_RULES,
    functions=[schedule_posts],
    actions=[
        # Step 1 actions (shown with previews)
        A2UIAction(
            name="approve_previews",
            description="User approved the previews. Show the scheduling options with time buttons and custom time input.",
        ),
        A2UIAction(
            name="rewrite_previews",
            description="Regenerate all three previews with a completely different creative angle and tone",
        ),
        # Step 2 actions (shown after approval)
        A2UIAction(
            name="schedule_9am",
            tool_name="schedule_posts",
            description="Schedule all posts for 9:00 AM tomorrow",
            example_context={"time": "9:00 AM"},
        ),
        A2UIAction(
            name="schedule_10am",
            tool_name="schedule_posts",
            description="Schedule all posts for 10:00 AM tomorrow",
            example_context={"time": "10:00 AM"},
        ),
        A2UIAction(
            name="schedule_2pm",
            tool_name="schedule_posts",
            description="Schedule all posts for 2:00 PM tomorrow",
            example_context={"time": "2:00 PM"},
        ),
        A2UIAction(
            name="schedule_custom",
            tool_name="schedule_posts",
            description="Schedule all posts for a custom time entered by the user",
            example_context={"time": {"path": "/customTime"}},
        ),
        # Client-side action (no server round-trip)
        A2UIAction(
            name="openUrl",
            action_type="functionCall",
            description="Open a URL in the user's browser. Use for CTA buttons like 'Shop Now'.",
            example_args={"url": "https://ag2.ai"},
        ),
    ],
)

# ─── Wrap in A2A server ───
# A2aAgentServer auto-detects A2UIAgent and:
#   - Uses A2UIAgentExecutor (splits response into TextPart + A2UI DataPart)
#   - Declares the A2UI v0.9 extension in the agent card
#   - Handles extension negotiation (clients without A2UI get text only)
server = A2aAgentServer(
    agent=a2ui_agent,
    url="http://localhost:9000",
    agent_card=CardSettings(
        name="Marketing Preview Designer",
        description="Creates marketing preview cards using A2UI (email, LinkedIn, X/Twitter).",
    ),
)

app = server.build()

# Serve static images, like the water bottle image and AG2 avatar
IMAGES_DIR = Path(__file__).parent / "images"
if IMAGES_DIR.exists():
    app.mount("/images", StaticFiles(directory=str(IMAGES_DIR)), name="images")

# Add CORS middleware for Flutter web development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9000)
