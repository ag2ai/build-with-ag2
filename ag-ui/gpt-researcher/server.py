"""
Web UI mode: run the GPT Researcher pipeline with a live AG-UI frontend.

Start the server:
    python -m server

Then open http://localhost:8457 in your browser.

The frontend shows which pipeline stage is active and streams the final report.
STATE_SNAPSHOT events (emitted automatically by AGUIStream whenever context_variables
change) drive the pipeline progress panel in the UI.

Same prerequisites as main.py — multi_agents_ag2 must be on PYTHONPATH.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse

from autogen import ConversableAgent, LLMConfig
from autogen.ag_ui import AGUIStream

load_dotenv()


def load_task() -> dict:
    return json.loads(Path("task.json").read_text())


async def run_research(
    query: Annotated[str, "The research question to investigate"],
    context_variables: dict,
) -> str:
    """Run the full GPT Researcher pipeline and return the completed report.

    context_variables is injected by AG2 and mutated in place. AGUIStream detects
    changes and emits STATE_SNAPSHOT events to the frontend automatically.
    """
    from multi_agents_ag2.agents.orchestrator import ChiefEditorAgent

    task = {**load_task(), "query": query}

    # Signal that research has started. The frontend highlights "Chief Editor"
    # and shows "planning" as the current stage.
    context_variables["stage"] = "planning"
    context_variables["active_agent"] = "Chief Editor"

    # Run the full pipeline. For granular per-agent stage updates (e.g. switching
    # to "Researcher", "Reviewer", etc. mid-run), subclass ChiefEditorAgent and
    # call context_variables updates inside each stage method.
    chief_editor = ChiefEditorAgent(task)
    result = await chief_editor.run_research_task()

    context_variables["stage"] = "complete"
    context_variables["active_agent"] = "Publisher"

    return result.get("report", "")


# The orchestrator is a standard ConversableAgent. run_research is registered
# as a tool — AG2 injects context_variables when it calls the function.
orchestrator = ConversableAgent(
    name="research_orchestrator",
    system_message=(
        "You are a research coordinator. When given a research topic, "
        "call run_research and return the completed report to the user."
    ),
    llm_config=LLMConfig({"model": "gpt-4o", "stream": True}),
    functions=[run_research],
)

# AGUIStream wraps the agent and translates its activity into AG-UI SSE events.
stream = AGUIStream(orchestrator)

app = FastAPI()
app.mount("/research", stream.build_asgi())


@app.get("/")
async def serve_frontend() -> FileResponse:
    return FileResponse("frontend.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8457)
