"""FastAPI application with AG2 A2A protocol support.

This module creates a FastAPI application that serves an AG2 ConversableAgent
via the A2A (Agent-to-Agent) protocol for Cloud Run deployment.
"""

import logging
import os

from a2a.server.apps import A2AFastAPIApplication
from a2a.types import AgentSkill
from autogen.a2a import A2aAgentServer
from autogen.a2a.server import CardSettings
from fastapi import FastAPI
from pydantic import BaseModel

from .agent import root_agent

# Define agent skills for the A2A agent card
AGENT_SKILLS = [
    AgentSkill(
        id="get_weather",
        name="Get Weather",
        description="Get weather information for a location",
        tags=["weather", "forecast"],
        examples=["What's the weather in San Francisco?", "How's the weather in NYC?"],
    ),
    AgentSkill(
        id="get_current_time",
        name="Get Current Time",
        description="Get the current UTC time",
        tags=["time", "utility"],
        examples=["What time is it?", "What's the current time?"],
    ),
]
from .app_utils.telemetry import setup_telemetry

setup_telemetry()

# Logging
if os.getenv("K_SERVICE"):  # Use GCP logging on Cloud Run
    from google.cloud import logging as google_cloud_logging

    logging_client = google_cloud_logging.Client()
    logger = logging_client.logger(__name__)
else:
    # Use standard logging locally
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

# Create AG2 A2A server
APP_URL = os.getenv("APP_URL", "http://0.0.0.0:8000/a2a/app/")
server = A2aAgentServer(
    root_agent,
    url=APP_URL,
    agent_card=CardSettings(skills=AGENT_SKILLS),
)

# Build FastAPI app using A2A SDK
app: FastAPI = A2AFastAPIApplication(
    agent_card=server.card,
    extended_agent_card=server.extended_agent_card,
    http_handler=server.build_request_handler(),
).build(
    agent_card_url="/a2a/app/.well-known/agent-card.json",
    rpc_url="/a2a/app/",
    extended_agent_card_url="/a2a/app/agent/authenticatedExtendedCard",
)

app.title = "AG2 Agent"
app.description = "AG2 ConversableAgent with A2A protocol support"


class Feedback(BaseModel):
    """Feedback model for logging user feedback."""

    session_id: str | None = None
    message: str | None = None
    rating: int | None = None
    metadata: dict | None = None


@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    """Collect and log feedback.

    Args:
        feedback: The feedback data to log

    Returns:
        Success message
    """
    if hasattr(logger, "log_struct"):
        logger.log_struct(feedback.model_dump(), severity="INFO")
    else:
        logger.info("Feedback: %s", feedback.model_dump())
    return {"status": "success"}


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for Cloud Run."""
    return {"status": "ok"}
