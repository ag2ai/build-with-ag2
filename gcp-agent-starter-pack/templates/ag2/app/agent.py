import os
from datetime import datetime, timezone
from typing import Annotated

from autogen import ConversableAgent, LLMConfig
from autogen.agentchat import ReplyResult
from dotenv import load_dotenv

load_dotenv()

MODEL = "gemini-2.5-flash"

# Use Vertex AI if GCP credentials available, otherwise use API key
if os.getenv("GOOGLE_GEMINI_API_KEY"):
    # Local development with API key
    llm_config = LLMConfig({"api_type": "google", "model": MODEL})
    print("Using GOOGLE_GEMINI_API_KEY for LLM configuration.")
else:
    # Production on GCP with Vertex AI
    import google.auth

    _, project_id = google.auth.default()
    os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
    os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

    llm_config = LLMConfig({"api_type": "google", "model": MODEL})

root_agent = ConversableAgent(
    name="root_agent",
    system_message=(
        "You are a helpful assistant. "
        "Use the available tools to answer questions. "
        "Use get_weather when asked about weather. "
        "Use get_current_time when asked about the time."
    ),
    llm_config=llm_config,
    human_input_mode="NEVER",
)


@root_agent.register_for_llm(
    name="get_weather",
    description="Get weather information for a location",
)
@root_agent.register_for_execution(name="get_weather")
def get_weather(
    location: Annotated[str, "The city or location to get weather for"],
) -> ReplyResult:
    """Simulates getting weather information."""
    if "sf" in location.lower() or "san francisco" in location.lower():
        return ReplyResult(message="It's 60 degrees and foggy in San Francisco.")
    return ReplyResult(message=f"It's 90 degrees and sunny in {location}.")


@root_agent.register_for_llm(
    name="get_current_time",
    description="Get the current UTC time",
)
@root_agent.register_for_execution(name="get_current_time")
def get_current_time() -> ReplyResult:
    """Returns the current UTC time."""
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return ReplyResult(message=f"The current time is {current_time}.")


# Prevent ADK app injection - AG2 uses its own A2A server in fast_api_app.py
app = None
