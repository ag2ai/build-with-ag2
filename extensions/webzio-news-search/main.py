from __future__ import annotations

import argparse
import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from ag2 import Agent
from ag2.config import OpenAIConfig
from ag2.extensions.tools.search import WebzioNewsSearchToolkit

DEFAULT_PROMPT = (
    "Search Webz news for recent Nvidia supply-chain risk coverage "
    "from the past 30 days and summarize with sources."
)


def build_agent() -> Agent:
    if not os.getenv("WEBZ_API_TOKEN", "").strip():
        raise SystemExit("Set WEBZ_API_TOKEN (https://webz.io).")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        raise SystemExit("Set OPENAI_API_KEY.")

    return Agent(
        "news-researcher",
        config=OpenAIConfig(model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini")),
        tools=[WebzioNewsSearchToolkit()],
    )


async def run(prompt: str) -> None:
    reply = await build_agent().ask(prompt)
    print(reply.body)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search global news with Webz.io from an AG2 agent."
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default=DEFAULT_PROMPT,
        help="Research question for the agent (default: Nvidia supply-chain example).",
    )
    args = parser.parse_args()
    asyncio.run(run(args.prompt))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
