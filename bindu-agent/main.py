import logging
import os
from typing import Any

from autogen import ConversableAgent
from bindu.penguin import bindufy
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


def build_llm_config() -> dict[str, list[dict[str, str]]]:
    """Build the AG2 model configuration from environment variables."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Add it to your environment or .env file."
        )

    return {
        "config_list": [
            {
                "model": os.getenv("OPENROUTER_MODEL", "anthropic/claude-3-haiku"),
                "api_key": api_key,
                "base_url": os.getenv(
                    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
                ),
            }
        ]
    }


def build_bindu_config() -> dict[str, Any]:
    """Keep service metadata in one place so users can safely customize it."""
    return {
        "author": os.getenv("BINDU_AGENT_AUTHOR", "ag2.developer@example.com"),
        "name": os.getenv("BINDU_AGENT_NAME", "ag2-networked-assistant"),
        "description": os.getenv(
            "BINDU_AGENT_DESCRIPTION",
            "An AG2 ConversableAgent exposed via the Bindu A2A protocol.",
        ),
        "deployment": {
            "url": os.getenv("BINDU_AGENT_URL", "http://localhost:3773"),
            # Tunneling is disabled by default so the sample stays safe for local use.
            "expose": os.getenv("BINDU_AGENT_EXPOSE", "false").lower() == "true",
        },
        "skills": [],
    }


LLM_CONFIG = build_llm_config()
BINDU_CONFIG = build_bindu_config()


def handler(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """Translate a Bindu message list into a one-turn AG2 chat response."""
    if not messages:
        return [{"role": "assistant", "content": "No input provided."}]

    user_input = messages[-1].get("content", "").strip()
    if not user_input:
        return [{"role": "assistant", "content": "Empty message."}]

    # Create fresh agents per request so the service remains stateless and predictable.
    assistant = ConversableAgent(
        name="assistant",
        system_message="You are a helpful AG2 assistant. Keep answers concise.",
        llm_config=LLM_CONFIG,
    )
    user_proxy = ConversableAgent(name="user_proxy", human_input_mode="NEVER")

    logger.info("Handling request with %s incoming messages", len(messages))
    result = user_proxy.initiate_chat(
        assistant,
        message=user_input,
        max_turns=1,
    )

    if result.chat_history:
        reply = result.chat_history[-1].get("content", "").strip()
        if reply:
            return [{"role": "assistant", "content": reply}]

    return [{"role": "assistant", "content": "Task completed."}]


def main() -> None:
    """Run the Bindu-wrapped AG2 service."""
    logger.info("Starting Bindu agent service at %s", BINDU_CONFIG["deployment"]["url"])
    bindufy(BINDU_CONFIG, handler)


if __name__ == "__main__":
    main()
