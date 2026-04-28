"""Parallel web research with live fan-out on AG2 Beta.

A lead/coordinator agent decomposes a research question into 3 sub-questions,
delegates each to a researcher subagent (Tavily search + fetch), and watches
all three run concurrently with live progress streamed to the terminal.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from tavily import TavilyClient

from autogen.beta import Agent, MemoryStream, tool
from autogen.beta.config import GeminiConfig, OpenAIConfig
from autogen.beta.config.config import ModelConfig
from autogen.beta.events import (
    TaskCompleted,
    TaskFailed,
    TaskStarted,
    ToolCallEvent,
    ToolErrorEvent,
)
from autogen.beta.tools.subagents import subagent_tool

if TYPE_CHECKING:
    from autogen.beta.annotations import Context
    from autogen.beta.stream import Stream

NUM_RESEARCHERS = 3

# ---------------------------------------------------------------------------
# LLM provider selection
# ---------------------------------------------------------------------------

# Defaults tuned for each provider. Lead uses a stronger model for decomposition
# and synthesis; researchers use a cheaper/faster model for bulk fetching work.
_PROVIDER_DEFAULTS = {
    "gemini": {
        "lead": "gemini-2.5-pro",
        "researcher": "gemini-2.5-flash",
        "env": "GEMINI_API_KEY",
    },
    "openai": {"lead": "gpt-4o", "researcher": "gpt-4o-mini", "env": "OPENAI_API_KEY"},
}


def build_config(role: str) -> ModelConfig:
    """Return a ModelConfig for the given role ('lead' or 'researcher').

    Provider is selected by LLM_PROVIDER env var (default: gemini). Model names
    can be overridden per-role via LEAD_MODEL and RESEARCHER_MODEL.
    """
    provider = os.environ.get("LLM_PROVIDER", "gemini").lower()
    if provider not in _PROVIDER_DEFAULTS:
        raise SystemExit(
            f"LLM_PROVIDER must be one of {list(_PROVIDER_DEFAULTS)}; got {provider!r}"
        )
    defaults = _PROVIDER_DEFAULTS[provider]
    override_var = f"{role.upper()}_MODEL"
    model = os.environ.get(override_var, defaults[role])

    if provider == "openai":
        return OpenAIConfig(model=model)
    return GeminiConfig(model=model)


# ---------------------------------------------------------------------------
# Tools (shared by every researcher)
# ---------------------------------------------------------------------------


@tool
async def tavily_search(query: str, max_results: int = 5) -> list[dict]:
    """Search the web. Returns a list of {title, url, content} dicts ranked by relevance."""
    client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    response = await asyncio.to_thread(
        client.search, query=query, max_results=max_results
    )
    return [
        {"title": r.get("title"), "url": r.get("url"), "content": r.get("content")}
        for r in response.get("results", [])
    ]


@tool
async def fetch_url(url: str) -> str:
    """Return the readable content of a URL as plain text. Use after `tavily_search` to read a full page."""
    client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    response = await asyncio.to_thread(client.extract, urls=url)
    results = response.get("results", [])
    if not results:
        return f"[extract returned no content for {url}]"
    return results[0].get("raw_content") or ""


# ---------------------------------------------------------------------------
# Lane router — prints live progress from every stream, tagged by agent
# ---------------------------------------------------------------------------


class LaneRouter:
    """Subscribes to the parent stream and every child (researcher) stream.

    Each stream gets a short label ([lead], [r1], [r2], ...) that prefixes
    its log lines, so the three researchers running concurrently show up as
    interleaved lanes in the terminal.
    """

    def __init__(self) -> None:
        self._lane_widths = {"lead": 6}

    def attach(self, stream: "Stream", label: str) -> None:
        self._lane_widths.setdefault(label, max(len(label), 4))

        @stream.where(ToolCallEvent).subscribe
        async def _on_tool_call(event: ToolCallEvent) -> None:
            name = event.name
            args = _parse_args(event.arguments)
            if name == "tavily_search":
                q = args.get("query", "")
                self._print(label, f"🔍 search({q!r})")
            elif name == "fetch_url":
                u = args.get("url", "")
                self._print(label, f"📄 fetch({u})")
            elif name.startswith("task_"):
                objective = args.get("objective", "")
                self._print(
                    label, f"🧭 delegate → {name.removeprefix('task_')}: {objective}"
                )
            else:
                self._print(label, f"🛠  {name}({event.arguments[:80]})")

        @stream.where(ToolErrorEvent).subscribe
        async def _on_tool_error(event: ToolErrorEvent) -> None:
            self._print(label, f"❌ {event.name} failed: {event.error!r}")

        @stream.where(TaskStarted).subscribe
        async def _on_task_started(event: TaskStarted) -> None:
            self._print(label, f"▶️  {event.agent_name}: {event.objective}")

        @stream.where(TaskCompleted).subscribe
        async def _on_task_completed(event: TaskCompleted) -> None:
            chars = len(event.result or "")
            self._print(label, f"✅ {event.agent_name} done — {chars} chars")

        @stream.where(TaskFailed).subscribe
        async def _on_task_failed(event: TaskFailed) -> None:
            self._print(label, f"❌ {event.agent_name} failed: {event.error!r}")

    def _print(self, label: str, msg: str) -> None:
        width = self._lane_widths.get(label, 4)
        print(f"[{label:<{width}}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------


RESEARCHER_PROMPT = (
    "You are a focused web researcher. Given an `objective` (a specific sub-question), "
    "you must:\n"
    "  1. Use `tavily_search` to find 3–5 relevant sources.\n"
    "  2. Use `fetch_url` on the 1–2 most promising results to read their content.\n"
    "  3. Produce a concise (≤200 words) answer to the sub-question with inline "
    "     citations of the form [Title](URL) on every factual claim.\n"
    "Prefer recent sources. Do not speculate beyond what you found. If the sources "
    "disagree, say so."
)

LEAD_PROMPT = (
    "You are the lead researcher coordinating a team of 3 specialist researchers "
    "(researcher_1, researcher_2, researcher_3). For every user question you must:\n\n"
    "  1. Decompose the question into exactly 3 disjoint sub-questions.\n"
    "  2. Delegate each sub-question by calling `task_researcher_1`, "
    "     `task_researcher_2`, and `task_researcher_3` — ALL THREE IN THE SAME TURN "
    "     so they execute in parallel. This is critical; do not call them one at a time.\n"
    "  3. After all three return, synthesise a single cohesive answer with numbered "
    "     inline citations `[1]`, `[2]`, etc., followed by a **Sources** section listing "
    "     every URL you cited, in citation order.\n\n"
    "For follow-up questions, reuse prior sources when relevant; only delegate new "
    "research if the follow-up needs information you don't already have."
)


def build_researchers(n: int) -> list[Agent]:
    return [
        Agent(
            name=f"researcher_{i + 1}",
            prompt=RESEARCHER_PROMPT,
            config=build_config("researcher"),
            tools=[tavily_search, fetch_url],
        )
        for i in range(n)
    ]


def build_lead(
    researchers: list[Agent],
    router: LaneRouter,
    parent_storage,
) -> Agent:
    def make_stream_factory(label: str):
        def factory(agent: "Agent", ctx: "Context") -> MemoryStream:
            # Create a child stream that shares storage with the parent so
            # history is unified, but gets its own live subscribers via the router.
            stream = MemoryStream(storage=parent_storage)
            router.attach(stream, label)
            return stream

        return factory

    lead_tools = [
        subagent_tool(
            researcher,
            description=(
                f"Delegate a focused research sub-question to {researcher.name}. "
                "Provide a clear, standalone `objective` (the sub-question)."
            ),
            stream=make_stream_factory(f"r{i + 1}"),
        )
        for i, researcher in enumerate(researchers)
    ]

    return Agent(
        name="lead",
        prompt=LEAD_PROMPT,
        config=build_config("lead"),
        tools=lead_tools,
    )


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


async def main() -> None:
    load_dotenv()

    provider = os.environ.get("LLM_PROVIDER", "gemini").lower()
    if provider not in _PROVIDER_DEFAULTS:
        raise SystemExit(f"LLM_PROVIDER must be one of {list(_PROVIDER_DEFAULTS)}")
    _require_env(_PROVIDER_DEFAULTS[provider]["env"])
    _require_env("TAVILY_API_KEY")

    router = LaneRouter()
    parent_stream = MemoryStream()
    router.attach(parent_stream, "lead")

    researchers = build_researchers(NUM_RESEARCHERS)
    lead = build_lead(researchers, router, parent_stream.history.storage)

    print(
        f"[provider={provider}] "
        f"lead={os.environ.get('LEAD_MODEL', _PROVIDER_DEFAULTS[provider]['lead'])} "
        f"researcher={os.environ.get('RESEARCHER_MODEL', _PROVIDER_DEFAULTS[provider]['researcher'])}",
        flush=True,
    )

    print(
        "Parallel research agent on AG2 Beta. Ctrl-D or 'exit' to quit.\n", flush=True
    )
    try:
        first = input("Research question: ").strip()
    except EOFError:
        return
    if not first or first.lower() in {"exit", "quit"}:
        return

    reply = await lead.ask(first, stream=parent_stream)
    print("\n" + "=" * 60)
    print("REPORT")
    print("=" * 60)
    print(reply.body)
    print("=" * 60 + "\n", flush=True)

    while True:
        try:
            q = input("Follow-up (blank to quit): ").strip()
        except EOFError:
            break
        if not q or q.lower() in {"exit", "quit"}:
            break
        reply = await reply.ask(q, stream=parent_stream)
        print("\n" + "=" * 60)
        print("REPORT")
        print("=" * 60)
        print(reply.body)
        print("=" * 60 + "\n", flush=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_args(raw: str) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _require_env(name: str) -> None:
    if not os.environ.get(name):
        raise SystemExit(
            f"Missing {name}. Copy .env.example to .env and fill in your keys, "
            f"or export {name} in your shell."
        )


if __name__ == "__main__":
    asyncio.run(main())
