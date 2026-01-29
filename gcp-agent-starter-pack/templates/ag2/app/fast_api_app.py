"""FastAPI application with AG2 A2A protocol support.

This module creates a FastAPI application that serves an AG2 ConversableAgent
via the A2A (Agent-to-Agent) protocol for Cloud Run deployment.
"""

import logging
import os

from a2a.server.apps import A2AFastAPIApplication
from autogen.a2a import A2aAgentServer
from fastapi import FastAPI
from pydantic import BaseModel

from .agent import root_agent
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
APP_URL = os.getenv("APP_URL", "http://0.0.0.0:8000")
server = A2aAgentServer(root_agent, url=APP_URL)

# Build FastAPI app using A2A SDK
app: FastAPI = A2AFastAPIApplication(
    agent_card=server.card,
    extended_agent_card=server.extended_agent_card,
    http_handler=server.build_request_handler(),
).build()

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
