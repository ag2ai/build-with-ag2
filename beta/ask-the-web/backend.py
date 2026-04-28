"""Citation-backed web Q&A on AG2 Beta.

A single Beta `Agent` with two Tavily tools (`tavily_search`, `fetch_url`) exposed
through `autogen.beta.ag_ui.AGUIStream`. The frontend subscribes to the SSE
stream, renders streaming text, and builds live source cards from tool events.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from tavily import TavilyClient

from autogen.beta import Agent, tool
from autogen.beta.ag_ui import AGUIStream
from autogen.beta.config import GeminiConfig, OpenAIConfig
from autogen.beta.config.config import ModelConfig

load_dotenv()


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@tool
async def tavily_search(query: str, max_results: int = 5) -> list[dict]:
    """Search the web. Returns a list of {title, url, content} dicts ranked by relevance.

    Use this first to discover candidate sources for a question.
    """
    client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    response = await asyncio.to_thread(client.search, query=query, max_results=max_results)
    return [
        {"title": r.get("title"), "url": r.get("url"), "content": r.get("content")}
        for r in response.get("results", [])
    ]


@tool
async def fetch_url(url: str) -> str:
    """Return the readable content of a URL as plain text.

    Use this after `tavily_search` to read the full contents of the most relevant
    1–3 results before answering.
    """
    client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    response = await asyncio.to_thread(client.extract, urls=url)
    results = response.get("results", [])
    if not results:
        return f"[extract returned no content for {url}]"
    return results[0].get("raw_content") or ""


# ---------------------------------------------------------------------------
# LLM provider selection (env-driven)
# ---------------------------------------------------------------------------


_PROVIDER_DEFAULTS = {
    "gemini": {"model": "gemini-2.5-pro", "env": "GEMINI_API_KEY"},
    "openai": {"model": "gpt-4o", "env": "OPENAI_API_KEY"},
}


def build_config() -> ModelConfig:
    provider = os.environ.get("LLM_PROVIDER", "gemini").lower()
    if provider not in _PROVIDER_DEFAULTS:
        raise SystemExit(f"LLM_PROVIDER must be one of {list(_PROVIDER_DEFAULTS)}")

    model = os.environ.get("MODEL", _PROVIDER_DEFAULTS[provider]["model"])

    env = _PROVIDER_DEFAULTS[provider]["env"]
    if not os.environ.get(env):
        raise SystemExit(
            f"{env} is required for LLM_PROVIDER={provider}. "
            f"Copy .env.example to .env and add your key."
        )

    if provider == "openai":
        return OpenAIConfig(model=model, streaming=True)
    return GeminiConfig(model=model, streaming=True)


def _require_tavily() -> None:
    if not os.environ.get("TAVILY_API_KEY"):
        raise SystemExit("TAVILY_API_KEY is required. Copy .env.example to .env and add your key.")


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


SYSTEM_PROMPT = (
    "You are a web research assistant. For EVERY user question (including follow-ups):\n\n"
    "  1. Call `tavily_search` with a focused query to find candidate sources.\n"
    "  2. Call `fetch_url` on the 1–3 most relevant results to read their full content.\n"
    "  3. Write a concise answer grounded ONLY in the fetched content. Do not use prior\n"
    "     knowledge beyond what you have just read.\n"
    "  4. Cite every factual claim inline with numbered footnotes like `[1]`, `[2]`.\n"
    "     CITATION NUMBERING RULE: number sources in the exact order you called\n"
    "     `fetch_url` this turn. The first URL you fetched is `[1]`, the second is\n"
    "     `[2]`, etc. Do NOT reuse numbers from previous turns — every turn starts\n"
    "     fresh from `[1]`.\n"
    "  5. End with a **Sources** section listing every URL you cited, in citation order:\n"
    "        [1] <title> — <url>\n"
    "        [2] <title> — <url>\n\n"
    "TOOL-CALL DISCIPLINE: emit ONLY ONE tool call per turn. Never call multiple\n"
    "tools in the same turn (no parallel `fetch_url` calls). After each tool result\n"
    "you may emit the next tool call. This is a hard requirement.\n\n"
    "For follow-up questions, always run a fresh search + fetch so that citation\n"
    "numbers in the new answer correspond to new fetches in this turn. If search and\n"
    "fetches do not give enough information to answer, say so explicitly rather than\n"
    "speculating."
)


_require_tavily()

agent = Agent(
    name="ask_the_web",
    prompt=SYSTEM_PROMPT,
    config=build_config(),
    tools=[tavily_search, fetch_url],
)


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

stream = AGUIStream(agent)
app.mount("/chat", stream.build_asgi())

_assets_dir = Path(__file__).parent / "assets"
app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")


@app.get("/")
async def serve_frontend() -> FileResponse:
    return FileResponse(Path(__file__).parent / "frontend.html")


@app.get("/healthz")
async def healthz() -> dict:
    provider = os.environ.get("LLM_PROVIDER", "gemini").lower()
    return {
        "ok": True,
        "provider": provider,
        "model": os.environ.get("MODEL", _PROVIDER_DEFAULTS[provider]["model"]),
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8765"))
    uvicorn.run(app, host="0.0.0.0", port=port)
