"""Demo 2: Feedback Factory - Multi-stage document refinement with AG2.

Uses a single orchestrator agent with stage-specific tools. The agent follows
a feedback loop: plan -> draft -> review -> revise -> review -> finalize.
ContextVariables track the workflow state, and the frontend visualizes each stage.
"""

from typing import Annotated

from ag_ui.core import RunAgentInput
from dotenv import load_dotenv
from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from autogen import ConversableAgent, LLMConfig
from autogen.ag_ui import AGUIStream
from autogen.agentchat.group import ContextVariables, ReplyResult

load_dotenv()

llm_config = LLMConfig({"model": "gpt-4o-mini"})

ORCHESTRATOR_SYSTEM = """You are a document creation orchestrator that follows a strict multi-stage pipeline.
You must work through these stages IN ORDER, calling the appropriate tool at each stage:

STAGE 1 - PLANNING: Call submit_plan with an outline, audience, and tone.
STAGE 2 - DRAFTING: Call submit_draft with the full document based on the plan.
STAGE 3 - REVIEW: Call submit_review with strengths, improvements, and whether revision is needed.
STAGE 4 - REVISION (if needed): Call submit_revision with the revised document.
  -> Then go back to STAGE 3 for another review.
STAGE 5 - FINALIZATION: Call submit_final with the polished final document.

RULES:
- Call exactly ONE tool per turn. Do NOT call multiple tools at once.
- After each tool call, wait for the result before proceeding.
- ALWAYS set needs_revision to true during reviews. The system will automatically move to finalization after 2 revision cycles.
- Each review should find genuine improvements to suggest.
- Write real, substantive content - not placeholders.
- Keep documents concise (300-500 words) for demo purposes.
"""

agent = ConversableAgent(
    name="orchestrator",
    system_message=ORCHESTRATOR_SYSTEM,
    llm_config=llm_config,
)


@agent.register_for_execution()
@agent.register_for_llm(description="Submit the document plan. Call this first.")
def submit_plan(
    outline: Annotated[str, "Structured outline with 3-5 sections and key points"],
    audience: Annotated[str, "Target audience"],
    tone: Annotated[str, "Writing tone (professional, casual, technical)"],
    context_variables: ContextVariables,
) -> ReplyResult:
    plan = f"**Audience:** {audience}\n**Tone:** {tone}\n\n**Outline:**\n{outline}"
    context_variables["document_plan"] = plan
    context_variables["stage"] = "drafting"
    context_variables["active_agent"] = "writer"
    return ReplyResult(
        message=f"[PLANNER] Plan created for {audience} audience. Now write the draft using submit_draft.",
        context_variables=context_variables,
    )


@agent.register_for_execution()
@agent.register_for_llm(description="Submit the document draft based on the plan.")
def submit_draft(
    document: Annotated[str, "Full document draft in markdown"],
    context_variables: ContextVariables,
) -> ReplyResult:
    context_variables["document_draft"] = document
    context_variables["stage"] = "review"
    context_variables["active_agent"] = "reviewer"
    return ReplyResult(
        message="[WRITER] Draft complete. Now review it using submit_review.",
        context_variables=context_variables,
    )


@agent.register_for_execution()
@agent.register_for_llm(description="Submit review feedback on the current draft.")
def submit_review(
    strengths: Annotated[str, "What the document does well"],
    improvements: Annotated[str, "Specific areas needing improvement"],
    needs_revision: Annotated[bool, "Whether revision is needed"],
    context_variables: ContextVariables,
) -> ReplyResult:
    context_variables["feedback"] = (
        f"Strengths: {strengths}\nImprovements: {improvements}"
    )
    context_variables["needs_revision"] = needs_revision

    iteration = context_variables.get("iteration", 0)
    max_iter = context_variables.get("max_iterations", 2)

    if needs_revision and iteration < max_iter:
        context_variables["stage"] = "revision"
        context_variables["active_agent"] = "editor"
        return ReplyResult(
            message=f"[REVIEWER] Iteration {iteration + 1}/{max_iter}: Revisions needed. Use submit_revision.",
            context_variables=context_variables,
        )
    else:
        context_variables["stage"] = "finalization"
        context_variables["active_agent"] = "editor"
        context_variables["needs_revision"] = False
        return ReplyResult(
            message="[REVIEWER] Document approved. Now finalize using submit_final.",
            context_variables=context_variables,
        )


@agent.register_for_execution()
@agent.register_for_llm(
    description="Submit revised document incorporating feedback. Loops back to review."
)
def submit_revision(
    revised_document: Annotated[
        str, "Revised document incorporating reviewer feedback"
    ],
    context_variables: ContextVariables,
) -> ReplyResult:
    context_variables["document_draft"] = revised_document
    context_variables["iteration"] = context_variables.get("iteration", 0) + 1
    context_variables["stage"] = "review"
    context_variables["active_agent"] = "reviewer"
    return ReplyResult(
        message=f"[EDITOR] Revision {context_variables['iteration']} complete. Now review again using submit_review.",
        context_variables=context_variables,
    )


@agent.register_for_execution()
@agent.register_for_llm(
    description="Submit the final polished document. Call this last."
)
def submit_final(
    final_document: Annotated[str, "Finalized document in markdown"],
    context_variables: ContextVariables,
) -> ReplyResult:
    context_variables["final_document"] = final_document
    context_variables["stage"] = "done"
    context_variables["active_agent"] = ""
    return ReplyResult(
        message="[EDITOR] Document finalized and ready!",
        context_variables=context_variables,
    )


stream = AGUIStream(agent)

# ──────────────────────────────────────────────
# FastAPI app
# ──────────────────────────────────────────────
app = FastAPI(title="Feedback Factory Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

assets_dir = Path(__file__).parent / "assets"
app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/")
async def serve_frontend():
    return FileResponse(Path(__file__).parent / "frontend.html")


@app.post("/chat")
async def run_agent(
    message: RunAgentInput,
    accept: str | None = Header(None),
) -> StreamingResponse:
    event_stream = stream.dispatch(message, accept=accept)
    return StreamingResponse(
        event_stream,
        media_type=accept or "text/event-stream",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8457)
