"""
Web UI mode: run GPT Researcher with a live AG-UI frontend.

Start the server:
    python server.py

Then open http://localhost:8457 in your browser.

Each of the 7 pipeline agents is a separate tool call. AGUIStream emits a
STATE_SNAPSHOT event between turns, so the frontend panel advances in real time.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from gpt_researcher import GPTResearcher

from autogen import ConversableAgent, LLMConfig
from autogen.ag_ui import AGUIStream
from autogen.agentchat.group import ContextVariables, ReplyResult

load_dotenv()


def load_task() -> dict:
    return json.loads(Path("task.json").read_text())


# Module-level state shared across tool calls within a single research run.
# The report is stored here rather than in context_variables to avoid bloating
# STATE_SNAPSHOT payloads sent to the frontend.
_researcher: GPTResearcher | None = None
_supplementary_researcher: GPTResearcher | None = None
_report: str = ""

agent = ConversableAgent(
    name="research_orchestrator",
    system_message=(
        "You are the Chief Editor coordinating a 7-step research pipeline. "
        "Execute ALL steps in order, calling ONE tool per turn:\n"
        "1. start_research    — initialize the task\n"
        "2. plan_research     — outline 3-5 key sections to cover\n"
        "3. conduct_research  — gather sources and information from the web\n"
        "4. review_research   — score quality (1-10) and identify gaps\n"
        "5. revise_research   — address gaps with a supplementary query, or pass 'none'\n"
        "6. write_report      — compile the final report\n"
        "7. publish_report    — finalize and display the report\n\n"
        "After publish_report completes, tell the user the report is ready."
    ),
    llm_config=LLMConfig({"model": "gpt-4o", "stream": True}),
)


@agent.register_for_execution()
@agent.register_for_llm(description=(
    "Step 1 — Chief Editor: Initialize and oversee the research task. Call this first."
))
async def start_research(
    query: Annotated[str, "The research question to investigate"],
    context_variables: ContextVariables,
) -> ReplyResult:
    """Chief Editor: assigns the task and stands up the research pipeline."""
    global _researcher, _supplementary_researcher, _report
    task = load_task()
    _researcher = GPTResearcher(query=query, report_type=task.get("report_type", "research_report"))
    _supplementary_researcher = None
    _report = ""
    context_variables["stage"] = "planning"
    context_variables["active_agent"] = "Chief Editor"
    context_variables["query"] = query
    return ReplyResult(
        message=f"Task initialized for: '{query}'. Call plan_research with 3-5 key sections to cover.",
        context_variables=context_variables,
    )


@agent.register_for_execution()
@agent.register_for_llm(description=(
    "Step 2 — Editor: Plan the research outline. "
    "Decide which sections the report should cover and pass them as a comma-separated list."
))
def plan_research(
    sections: Annotated[str, "Comma-separated list of 3-5 report sections, e.g. 'Background, Current State, Challenges, Outlook, Conclusion'"],
    context_variables: ContextVariables,
) -> ReplyResult:
    """Editor: defines the report structure before research begins."""
    context_variables["active_agent"] = "Editor"
    context_variables["sections"] = sections
    return ReplyResult(
        message=f"Outline: {sections}. Call conduct_research to gather information.",
        context_variables=context_variables,
    )


@agent.register_for_execution()
@agent.register_for_llm(description=(
    "Step 3 — Researcher: Search the web and collect sources on the research topic."
))
async def conduct_research(
    context_variables: ContextVariables,
) -> ReplyResult:
    """Researcher: runs GPTResearcher's web search and source collection."""
    context_variables["stage"] = "researching"
    context_variables["active_agent"] = "Researcher"
    await _researcher.conduct_research()
    sources = _researcher.get_source_urls()
    context = _researcher.get_research_context()
    context_variables["sources_count"] = len(sources)
    return ReplyResult(
        message=(
            f"Research complete. Collected {len(sources)} sources.\n\n"
            f"Findings summary:\n{context[:3000] if context else 'No context returned.'}\n\n"
            f"Top sources: {', '.join(sources[:5])}{'...' if len(sources) > 5 else ''}\n\n"
            "Call review_research with a quality score (1-10) and any gaps you notice."
        ),
        context_variables=context_variables,
    )


@agent.register_for_execution()
@agent.register_for_llm(description=(
    "Step 4 — Reviewer: Validate the research findings. "
    "Read the findings summary carefully, then score quality and identify gaps."
))
def review_research(
    quality_score: Annotated[int, "Research quality score from 1 (poor) to 10 (excellent)"],
    gaps: Annotated[str, "Specific topics or angles that are missing, or 'none' if research is comprehensive"],
    context_variables: ContextVariables,
) -> ReplyResult:
    """Reviewer: validates correctness and completeness of gathered research."""
    context_variables["active_agent"] = "Reviewer"
    context_variables["review_score"] = quality_score
    has_gaps = gaps.strip().lower() not in ("none", "")
    msg = f"Review complete. Quality: {quality_score}/10. "
    if has_gaps:
        msg += f"Gaps identified: {gaps}. Call revise_research with a focused supplementary query."
    else:
        msg += "Research is comprehensive. Call revise_research with supplementary_query='none'."
    return ReplyResult(message=msg, context_variables=context_variables)


@agent.register_for_execution()
@agent.register_for_llm(description=(
    "Step 5 — Revisor: Address research gaps with a supplementary search, "
    "or confirm research is complete by passing 'none'."
))
async def revise_research(
    supplementary_query: Annotated[str, "A focused query to fill identified gaps, or 'none' if no revision is needed"],
    context_variables: ContextVariables,
) -> ReplyResult:
    """Revisor: runs a targeted supplementary search if the Reviewer found gaps."""
    global _supplementary_researcher
    context_variables["active_agent"] = "Revisor"
    if supplementary_query.strip().lower() != "none":
        task = load_task()
        _supplementary_researcher = GPTResearcher(
            query=supplementary_query,
            report_type="resource_report",
        )
        await _supplementary_researcher.conduct_research()
        extra = _supplementary_researcher.get_source_urls()
        context_variables["supplementary_sources_count"] = len(extra)
        return ReplyResult(
            message=f"Supplementary research complete — {len(extra)} additional sources gathered. Call write_report.",
            context_variables=context_variables,
        )
    return ReplyResult(
        message="Research confirmed complete. Call write_report.",
        context_variables=context_variables,
    )


@agent.register_for_execution()
@agent.register_for_llm(description=(
    "Step 6 — Writer: Compile and write the final research report."
))
async def write_report(
    context_variables: ContextVariables,
) -> ReplyResult:
    """Writer: calls GPTResearcher.write_report() to produce the full report."""
    global _report
    context_variables["stage"] = "writing"
    context_variables["active_agent"] = "Writer"
    _report = await _researcher.write_report()
    # Store report in context_variables so the frontend receives it via STATE_SNAPSHOT.
    # The LLM never needs to output the full report text.
    context_variables["report"] = _report
    return ReplyResult(
        message="Report written. Call publish_report to finalize.",
        context_variables=context_variables,
    )


@agent.register_for_execution()
@agent.register_for_llm(description=(
    "Step 7 — Publisher: Finalize and publish the research report. Call this last."
))
def publish_report(
    context_variables: ContextVariables,
) -> ReplyResult:
    """Publisher: stamps the report with metadata and returns the final output."""
    context_variables["stage"] = "complete"
    context_variables["active_agent"] = "Publisher"
    sources_count = context_variables.get("sources_count", 0)
    supplementary = context_variables.get("supplementary_sources_count", 0)
    total = sources_count + supplementary
    metadata = (
        f"\n\n---\n"
        f"*{total} sources · {datetime.now().strftime('%B %d, %Y')}*"
    )
    # Append metadata to the report in context_variables; the frontend renders it
    # from STATE_SNAPSHOT so the LLM doesn't need to output the full text.
    context_variables["report"] = _report + metadata
    return ReplyResult(
        message=f"Report published. {total} sources, {len(_report)} characters.",
        context_variables=context_variables,
    )


# AGUIStream wraps the agent and translates its activity into AG-UI SSE events.
stream = AGUIStream(agent)

app = FastAPI()
app.mount("/research", stream.build_asgi())


@app.get("/")
async def serve_frontend() -> FileResponse:
    return FileResponse("frontend.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8457)
