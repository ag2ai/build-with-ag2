"""
Web UI mode: run GPT Researcher with a live AG-UI frontend.

Start the server:
    python server.py

Then open http://localhost:8457 in your browser.

The research pipeline uses AG2's DefaultPattern to orchestrate 7 agents in a
sequential pipeline. Each agent has its own tool(s) and hands off to the next
via AgentNameTarget, following the same pattern as AG2's pipeline cookbook.
This orchestration happens inside an agent that represents the main agent for
AG-UI. 

A custom AG-UI SSE endpoint translates AG2 group chat events into AG-UI
protocol events for the frontend. A separate /logs SSE endpoint forwards
gpt-researcher's internal streaming output.
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, StreamingResponse
from gpt_researcher import GPTResearcher

from autogen import ConversableAgent, UserProxyAgent, LLMConfig
from autogen.agentchat import a_run_group_chat
from autogen.agentchat.group import (
    AgentNameTarget,
    AgentTarget,
    ContextVariables,
    OnCondition,
    ReplyResult,
    RevertToUserTarget,
    StringLLMCondition,
    TerminateTarget,
)
from autogen.agentchat.group.patterns import DefaultPattern
from autogen.events.agent_events import (
    ExecutedFunctionEvent,
    GroupChatRunChatEvent,
    InputRequestEvent,
    RunCompletionEvent,
    TextEvent,
    ToolCallEvent,
)

load_dotenv()


def load_task() -> dict:
    return json.loads(Path("task.json").read_text())


# ---------------------------------------------------------------------------
# Streaming adapter: mimics a WebSocket so gpt-researcher streams to a queue
# ---------------------------------------------------------------------------


class StreamAdapter:
    """Imitation WebSocket that gpt-researcher writes to via send_json().

    This allows us to get the streaming output from gpt-researcher as
    it utilises the WebSocket interface for its internal streaming.

    Messages are pushed to an asyncio Queue and consumed by the /logs SSE
    endpoint so the frontend receives real-time updates during long-running
    research and report-writing steps.
    """

    def __init__(self) -> None:
        self.queue: asyncio.Queue = asyncio.Queue()
        self.active = False

    def reset(self) -> None:
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        self.active = True

    async def send_json(self, data: dict) -> None:
        """Called by gpt-researcher internals. Filters per-call cost messages."""
        if self.active:
            if data.get("type") == "cost":
                return
            await self.queue.put(data)

    async def emit(self, data: dict) -> None:
        """Emit directly to the queue (bypasses filters)."""
        if self.active:
            await self.queue.put(data)

    def stop(self) -> None:
        self.active = False
        self.queue.put_nowait(None)


_stream_adapter = StreamAdapter()


# Module-level state shared across pipeline steps within a single run.
_researcher: GPTResearcher | None = None
_supplementary_researcher: GPTResearcher | None = None
_report: str = ""
_last_gptr_cost: float = 0.0
_hitl_respond = None  # Callable stored when InputRequestEvent fires
_hitl_pending = False  # True when human_review is waiting for input


async def _emit_state(active_agent: str, stage: str) -> None:
    """Push pipeline state to /logs so the frontend updates in real time."""
    await _stream_adapter.emit(
        {
            "type": "state",
            "data": {"active_agent": active_agent, "stage": stage},
        }
    )


async def _emit_gptr_cost() -> None:
    """Push gpt-researcher cost delta to /logs."""
    global _last_gptr_cost
    total = _researcher.get_costs() if _researcher else 0.0
    if _supplementary_researcher:
        total += _supplementary_researcher.get_costs()
    delta = total - _last_gptr_cost
    if delta > 0.0001:
        _last_gptr_cost = total
        await _stream_adapter.emit(
            {
                "type": "cost",
                "data": {"total_cost": f"${delta:.4f}"},
            }
        )


# ---------------------------------------------------------------------------
# Pipeline tool functions — each returns ReplyResult with handoff target
# ---------------------------------------------------------------------------


async def init_research(
    query: Annotated[str, "The research question to investigate"],
    context_variables: ContextVariables,
) -> ReplyResult:
    """Chief Editor: initialize the research pipeline with a query."""
    global _researcher, _supplementary_researcher, _report, _last_gptr_cost
    _last_gptr_cost = 0.0
    _stream_adapter.reset()
    task = load_task()
    _researcher = GPTResearcher(
        query=query,
        report_type=task.get("report_type", "research_report"),
        websocket=_stream_adapter,
    )
    _supplementary_researcher = None
    _report = ""
    context_variables["stage"] = "planning"
    context_variables["active_agent"] = "Chief Editor"
    context_variables["query"] = query
    await _emit_state("Chief Editor", "planning")
    return ReplyResult(
        message=f"Research initialized for: '{query}'. Editor, plan the report sections.",
        context_variables=context_variables,
        target=AgentNameTarget("editor"),
    )


async def plan_sections(
    sections: Annotated[str, "Comma-separated list of 3-5 report sections"],
    context_variables: ContextVariables,
) -> ReplyResult:
    """Editor: plan the research outline with report sections."""
    context_variables["active_agent"] = "Editor"
    context_variables["sections"] = sections
    await _emit_state("Editor", "planning")
    return ReplyResult(
        message=f"Report outline: {sections}. Researcher, gather information.",
        context_variables=context_variables,
        target=AgentNameTarget("researcher"),
    )


async def do_research(context_variables: ContextVariables) -> ReplyResult:
    """Researcher: search the web and collect sources."""
    context_variables["stage"] = "researching"
    context_variables["active_agent"] = "Researcher"
    await _emit_state("Researcher", "researching")
    await _researcher.conduct_research()
    await _emit_gptr_cost()
    sources = _researcher.get_source_urls()
    context = _researcher.get_research_context()
    context_variables["sources_count"] = len(sources)
    return ReplyResult(
        message=(
            f"Research complete. {len(sources)} sources collected.\n\n"
            f"Findings summary:\n{context[:3000] if context else 'No context.'}\n\n"
            f"Top sources: {', '.join(sources[:5])}{'...' if len(sources) > 5 else ''}\n\n"
            "Reviewer, evaluate quality and identify gaps."
        ),
        context_variables=context_variables,
        target=AgentNameTarget("reviewer"),
    )


async def evaluate_research(
    quality_score: Annotated[int, "Quality score 1 (poor) to 10 (excellent)"],
    gaps: Annotated[str, "Missing topics or 'none' if comprehensive"],
    context_variables: ContextVariables,
) -> ReplyResult:
    """Reviewer: evaluate research quality and identify gaps."""
    context_variables["active_agent"] = "Reviewer"
    context_variables["review_score"] = quality_score
    context_variables["gaps"] = gaps
    await _emit_state("Reviewer", "reviewing")
    has_gaps = gaps.strip().lower() not in ("none", "")
    if has_gaps:
        msg = f"Quality: {quality_score}/10. Gaps: {gaps}. Revisor, run supplementary research."
    else:
        msg = (
            f"Quality: {quality_score}/10. Comprehensive. Revisor, confirm and proceed."
        )
    return ReplyResult(
        message=msg,
        context_variables=context_variables,
        target=AgentNameTarget("revisor"),
    )


async def do_revision(
    supplementary_query: Annotated[str, "Focused query to fill gaps, or 'none'"],
    context_variables: ContextVariables,
) -> ReplyResult:
    """Revisor: run supplementary research if gaps were found."""
    global _supplementary_researcher
    context_variables["active_agent"] = "Revisor"
    await _emit_state("Revisor", "revising")
    if supplementary_query.strip().lower() != "none":
        _supplementary_researcher = GPTResearcher(
            query=supplementary_query,
            report_type="resource_report",
            websocket=_stream_adapter,
        )
        await _supplementary_researcher.conduct_research()
        await _emit_gptr_cost()
        extra = _supplementary_researcher.get_source_urls()
        context_variables["supplementary_sources_count"] = len(extra)
        msg = f"Supplementary research done — {len(extra)} extra sources. Human review, present findings."
    else:
        msg = "No revision needed. Human review, present findings."
    return ReplyResult(
        message=msg,
        context_variables=context_variables,
        target=AgentNameTarget("human_review"),
    )


async def present_for_review(context_variables: ContextVariables) -> ReplyResult:
    """Human Review: present research findings for human approval."""
    query = context_variables.get("query", "")
    sources_count = context_variables.get("sources_count", 0)
    score = context_variables.get("review_score", 0)
    gaps = context_variables.get("gaps", "none")
    sections = context_variables.get("sections", "")
    supplementary = context_variables.get("supplementary_sources_count", 0)

    # Gather rich data from the researcher instances
    source_urls = list(_researcher.get_source_urls()) if _researcher else []
    context = _researcher.get_research_context() if _researcher else ""
    if _supplementary_researcher:
        source_urls += list(_supplementary_researcher.get_source_urls())
        supp_context = _supplementary_researcher.get_research_context()
        if supp_context:
            context += "\n\n--- Supplementary ---\n" + supp_context

    global _hitl_pending
    _hitl_pending = True
    await _emit_state("Human Review", "human_review")

    # Push structured summary to /logs so the frontend renders rich HTML
    await _stream_adapter.emit(
        {
            "type": "hitl_summary",
            "data": {
                "query": query,
                "sections": sections,
                "sources": source_urls[:10],
                "sources_count": len(source_urls),
                "findings_preview": context[:1500] if context else "",
                "score": score,
                "gaps": gaps,
            },
        }
    )

    summary = (
        f"Research summary for your review:\n\n"
        f"- Query: {query}\n"
        f"- Sources collected: {sources_count}"
        + (f" (+{supplementary} supplementary)" if supplementary else "")
        + f"\n- Quality score: {score}/10\n"
        f"- Gaps: {gaps}\n\n"
        "Please review and either approve to proceed with writing, "
        "or provide feedback for additional research."
    )
    return ReplyResult(
        message=summary,
        context_variables=context_variables,
        target=RevertToUserTarget(),
    )


async def do_write_report(context_variables: ContextVariables) -> ReplyResult:
    """Writer: compile the final research report."""
    global _report
    context_variables["stage"] = "writing"
    context_variables["active_agent"] = "Writer"
    await _emit_state("Writer", "writing")
    _report = await _researcher.write_report()
    await _emit_gptr_cost()
    context_variables["report"] = _report
    return ReplyResult(
        message="Report written. Publisher, finalize it.",
        context_variables=context_variables,
        target=AgentNameTarget("publisher"),
    )


async def do_publish(context_variables: ContextVariables) -> ReplyResult:
    """Publisher: finalize the report with metadata."""
    context_variables["stage"] = "complete"
    context_variables["active_agent"] = "Publisher"
    await _emit_state("Publisher", "complete")
    sources_count = context_variables.get("sources_count", 0)
    supplementary = context_variables.get("supplementary_sources_count", 0)
    total = sources_count + supplementary
    metadata = f"\n\n---\n*{total} sources · {datetime.now().strftime('%B %d, %Y')}*"
    context_variables["report"] = _report + metadata
    await _stream_adapter.emit(
        {
            "type": "state",
            "data": {
                "active_agent": "Publisher",
                "stage": "complete",
                "report": _report + metadata,
            },
        }
    )
    _stream_adapter.stop()
    return ReplyResult(
        message=f"Report published. {total} sources, {len(_report)} characters.",
        context_variables=context_variables,
    )


# ---------------------------------------------------------------------------
# Pipeline agents — each has focused tools and hands off to the next
# ---------------------------------------------------------------------------

llm_config = LLMConfig(
    {"model": "gpt-4o-mini", "parallel_tool_calls": False, "cache_seed": None}
)

DISPLAY_NAMES = {
    "chief_editor": "Chief Editor",
    "editor": "Editor",
    "researcher": "Researcher",
    "reviewer": "Reviewer",
    "revisor": "Revisor",
    "human_review": "Human Review",
    "writer": "Writer",
    "publisher": "Publisher",
}

chief_editor = ConversableAgent(
    name="chief_editor",
    system_message=(
        "You are the Chief Editor. When given a research query, "
        "call init_research with the query to start the pipeline."
    ),
    functions=[init_research],
    llm_config=llm_config,
)

editor = ConversableAgent(
    name="editor",
    system_message=(
        "You are the Editor. Based on the research topic, plan 3-5 key sections "
        "the report should cover. Call plan_sections with a comma-separated list."
    ),
    functions=[plan_sections],
    llm_config=llm_config,
)

researcher_agent = ConversableAgent(
    name="researcher",
    system_message=(
        "You are the Researcher. Call do_research to search the web and "
        "collect sources on the topic."
    ),
    functions=[do_research],
    llm_config=llm_config,
)

reviewer_agent = ConversableAgent(
    name="reviewer",
    system_message=(
        "You are the Reviewer. Read the research findings summary carefully, "
        "then call evaluate_research with a quality score (1-10) and any gaps "
        "you notice (or 'none' if comprehensive)."
    ),
    functions=[evaluate_research],
    llm_config=llm_config,
)

revisor_agent = ConversableAgent(
    name="revisor",
    system_message=(
        "You are the Revisor. If gaps were identified, call do_revision with a "
        "focused supplementary query. Otherwise call do_revision with 'none'."
    ),
    functions=[do_revision],
    llm_config=llm_config,
)

writer_agent = ConversableAgent(
    name="writer",
    system_message="You are the Writer. Call do_write_report to compile the report.",
    functions=[do_write_report],
    llm_config=llm_config,
)

publisher_agent = ConversableAgent(
    name="publisher",
    system_message="You are the Publisher. Call do_publish to finalize the report.",
    functions=[do_publish],
    llm_config=llm_config,
)

human_review_agent = ConversableAgent(
    name="human_review",
    system_message=(
        "You are the Human Review checkpoint. On your first turn, call "
        "present_for_review to show the research summary and wait for human input. "
        "On your second turn (after receiving human feedback), evaluate what the "
        "user said and use the appropriate handoff."
    ),
    functions=[present_for_review],
    llm_config=llm_config,
)

user = UserProxyAgent(name="user", code_execution_config=False)

# --- Handoffs ---
chief_editor.handoffs.set_after_work(AgentTarget(editor))
editor.handoffs.set_after_work(AgentTarget(researcher_agent))
researcher_agent.handoffs.set_after_work(AgentTarget(reviewer_agent))
reviewer_agent.handoffs.set_after_work(AgentTarget(revisor_agent))
revisor_agent.handoffs.set_after_work(AgentTarget(human_review_agent))
human_review_agent.handoffs.add_llm_condition(
    OnCondition(
        target=AgentTarget(researcher_agent),
        condition=StringLLMCondition(
            "The user wants changes, more research, or is not satisfied."
        ),
    )
)
human_review_agent.handoffs.add_llm_condition(
    OnCondition(
        target=AgentTarget(writer_agent),
        condition=StringLLMCondition(
            "The user approves or wants to proceed with writing."
        ),
    )
)
human_review_agent.handoffs.set_after_work(AgentTarget(writer_agent))  # fallback
writer_agent.handoffs.set_after_work(AgentTarget(publisher_agent))
publisher_agent.handoffs.set_after_work(TerminateTarget())


# ---------------------------------------------------------------------------
# Custom AG-UI SSE endpoint — translates AG2 group chat events to AG-UI
# ---------------------------------------------------------------------------


def _timestamp() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


app = FastAPI()


@app.post("/research/")
async def research_endpoint(request: Request):
    """Run the multi-agent pipeline and stream AG-UI events."""
    body = await request.json()
    query = body["messages"][-1]["content"]
    thread_id = body.get("threadId", "research-thread")
    run_id = body.get("runId", f"run-{uuid4()}")

    shared_context = ContextVariables(
        data={
            "stage": "idle",
            "active_agent": "",
            "query": "",
            "sections": "",
            "sources_count": 0,
            "review_score": 0,
            "gaps": "",
            "supplementary_sources_count": 0,
            "report": "",
        }
    )

    pattern = DefaultPattern(
        initial_agent=chief_editor,
        agents=[
            chief_editor,
            editor,
            researcher_agent,
            reviewer_agent,
            revisor_agent,
            human_review_agent,
            writer_agent,
            publisher_agent,
        ],
        user_agent=user,
        context_variables=shared_context,
    )

    response = await a_run_group_chat(pattern, messages=query, max_rounds=50)

    async def generate():
        yield _sse(
            {
                "type": "RUN_STARTED",
                "threadId": thread_id,
                "runId": run_id,
                "timestamp": _timestamp(),
            }
        )

        try:
            async for event in response.events:
                if isinstance(event, GroupChatRunChatEvent):
                    speaker = event.content.speaker
                    if speaker == "_Group_Tool_Executor":
                        continue
                    yield _sse(
                        {
                            "type": "STATE_SNAPSHOT",
                            "snapshot": {
                                "active_agent": DISPLAY_NAMES.get(speaker, speaker)
                            },
                            "timestamp": _timestamp(),
                        }
                    )

                elif isinstance(event, ToolCallEvent):
                    for tc in event.content.tool_calls:
                        yield _sse(
                            {
                                "type": "TOOL_CALL_START",
                                "toolCallId": tc.id,
                                "toolCallName": tc.function.name,
                                "timestamp": _timestamp(),
                            }
                        )
                        yield _sse(
                            {
                                "type": "TOOL_CALL_ARGS",
                                "toolCallId": tc.id,
                                "delta": tc.function.arguments or "",
                                "timestamp": _timestamp(),
                            }
                        )

                elif isinstance(event, ExecutedFunctionEvent):
                    yield _sse(
                        {
                            "type": "TOOL_CALL_END",
                            "toolCallId": event.content.call_id,
                            "timestamp": _timestamp(),
                        }
                    )

                elif isinstance(event, InputRequestEvent):
                    global _hitl_respond
                    if _hitl_pending:
                        _hitl_respond = event.content.respond
                        yield _sse(
                            {
                                "type": "INPUT_REQUEST",
                                "prompt": event.content.prompt,
                                "timestamp": _timestamp(),
                            }
                        )
                    else:
                        # Pipeline done — respond with exit to stop the chat loop
                        await event.content.respond("exit")

                elif isinstance(event, TextEvent):
                    content = (
                        str(event.content.content) if event.content.content else ""
                    )
                    if content:
                        yield _sse(
                            {
                                "type": "TEXT_MESSAGE_CHUNK",
                                "messageId": str(uuid4()),
                                "delta": content,
                                "timestamp": _timestamp(),
                            }
                        )

                elif isinstance(event, RunCompletionEvent):
                    # Extract orchestration LLM cost from the final summary
                    cost_data = event.content.cost or {}
                    usage = cost_data.get("usage_excluding_cached_inference", {})
                    orchestration_cost = sum(
                        model.get("cost", 0)
                        for model in usage.values()
                        if isinstance(model, dict)
                    )
                    if orchestration_cost > 0:
                        await _stream_adapter.emit(
                            {
                                "type": "cost",
                                "data": {
                                    "total_cost": f"${orchestration_cost:.4f}",
                                    "label": "orchestration",
                                },
                            }
                        )

        except Exception as e:
            yield _sse(
                {
                    "type": "RUN_ERROR",
                    "message": repr(e),
                    "timestamp": _timestamp(),
                }
            )

        yield _sse(
            {
                "type": "RUN_FINISHED",
                "threadId": thread_id,
                "runId": run_id,
                "timestamp": _timestamp(),
            }
        )
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/research/respond")
async def respond_endpoint(request: Request):
    """Accept human feedback and resume the paused pipeline."""
    global _hitl_respond
    body = await request.json()
    if _hitl_respond is None:
        return {"status": "error", "message": "No pending input request"}
    global _hitl_pending
    respond_fn = _hitl_respond
    _hitl_respond = None
    _hitl_pending = False
    await respond_fn(body["response"])
    return {"status": "ok"}


@app.get("/")
async def serve_frontend() -> FileResponse:
    return FileResponse("frontend.html")


@app.get("/assets/{filename}")
async def serve_asset(filename: str) -> FileResponse:
    return FileResponse(f"assets/{filename}")


@app.get("/logs")
async def logs_stream():
    """SSE endpoint for gpt-researcher streaming and pipeline state updates."""

    async def generate():
        while True:
            try:
                msg = await asyncio.wait_for(_stream_adapter.queue.get(), timeout=300)
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                break
            if msg is None:
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                break
            yield f"data: {json.dumps(msg)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8457)
