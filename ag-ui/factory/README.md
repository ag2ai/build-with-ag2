# AG-UI Feedback Factory

A multi-stage document creation pipeline built with AG2 and connected to a browser UI via the [AG-UI protocol](https://docs.ag2.ai/latest/docs/user-guide/ag-ui/). A single orchestrator agent drives a feedback loop — plan, draft, review, revise, finalize — using stage-specific tools and `ContextVariables` to track workflow state.

The frontend is a single HTML file (no React, no build step) that consumes AG-UI events over SSE to visualize each pipeline stage, the evolving document, and the conversation log.

## AG2 Features

This project demonstrates the following AG2 features:

- [AG-UI Protocol](https://docs.ag2.ai/latest/docs/user-guide/ag-ui/) — streaming typed events to a browser frontend
- [ConversableAgent](https://docs.ag2.ai/latest/docs/user-guide/agentchat-user-guide/basics/conversable-agent/) — single orchestrator agent with multiple tools
- [Tool Use / Function Calling](https://docs.ag2.ai/latest/docs/user-guide/agentchat-user-guide/basics/tools/) — stage-specific tools (`submit_plan`, `submit_draft`, `submit_review`, `submit_revision`, `submit_final`)
- [Context Variables](https://docs.ag2.ai/latest/docs/user-guide/advanced-concepts/orchestration/group-chat/context-variables/) — shared state tracking pipeline stage, active agent, document content, and feedback

## TAGS

TAGS: ag-ui, multi-agent, document-pipeline, streaming, tool-use, context-variables, sse, fastapi

## File Structure

| File | Description |
|---|---|
| `backend.py` | FastAPI server, orchestrator agent with 5 pipeline tools, AGUIStream integration |
| `frontend.html` | 3-panel UI (agent pipeline, document preview, conversation log) |
| `assets/*.png` | Robot avatars, clouds, sun, roadscape background |

## Installation

1. Clone and navigate to the folder:

   ```bash
   git clone https://github.com/ag2ai/build-with-ag2.git
   cd build-with-ag2/ag-ui/factory
   ```

2. Install dependencies:

   ```bash
   pip install "ag2[openai,ag-ui]" fastapi uvicorn python-dotenv
   ```

3. Set your OpenAI API key (used by the orchestrator agent's LLM):

   ```bash
   export OPENAI_API_KEY="sk-..."
   ```

   Or create a `.env` file in the project directory:

   ```
   OPENAI_API_KEY=sk-...
   ```

## Running the Code

```bash
python backend.py
```

Open http://localhost:8457 in your browser.

Type a document request (e.g. "Write a blog post about AI agents") and watch the orchestrator work through the pipeline: planning, drafting, reviewing, revising, and finalizing.

## How Multi-Agent Visualization Works

AG-UI doesn't natively support multi-agent workflows yet — it sees a single agent on the backend. This demo simulates a multi-agent pipeline using a single `ConversableAgent` with stage-specific tools, and uses `STATE_SNAPSHOT` events to communicate which "agent" is active to the frontend.

### Step 1: Tools set ContextVariables

Each tool function receives `context_variables: ContextVariables` and mutates it to signal the next agent and stage. The updated context is carried back via `ReplyResult`:

```python
def submit_plan(..., context_variables: ContextVariables) -> ReplyResult:
    context_variables["stage"] = "drafting"
    context_variables["active_agent"] = "writer"
    return ReplyResult(message="Plan created. Now write the draft.", context_variables=context_variables)
```

### Step 2: AGUIStream emits STATE_SNAPSHOT automatically

AG2's `AGUIStream` compares the `ContextVariables` after each tool call to the previous snapshot. If anything changed, it serializes the context (dropping non-JSON-serializable values like functions) and emits a `STATE_SNAPSHOT` event over SSE:

```
data: {"type":"STATE_SNAPSHOT","snapshot":{"stage":"drafting","active_agent":"writer","document_plan":"..."},"timestamp":1771292587100}
```

No extra wiring is needed — this is built into `AGUIStream`. Any key you set on `ContextVariables` that is JSON-serializable will automatically appear in the snapshot.

### Step 3: Frontend reads the snapshot

The frontend listens for `STATE_SNAPSHOT` events and reads the active agent and stage directly from the backend state — no need to duplicate transition logic:

```javascript
case 'STATE_SNAPSHOT':
    const state = event.snapshot || {};
    if (state.active_agent !== undefined) setAgentActive(state.active_agent || null);
    if (state.stage) setStage(state.stage);
    if (state.iteration !== undefined) updateIteration(state.iteration);
    break;
```

The `handleToolResult()` function only handles rendering (document content, feedback cards, log entries) — all agent and stage transitions come from the backend as the single source of truth.

## Contact

For more information or any questions, please refer to the documentation or reach out to us!

- AG2 Documentation: https://docs.ag2.ai/docs/Home
- AG2 GitHub: https://github.com/ag2ai/ag2
- Discord: https://discord.gg/pAbnFJrkgZ

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](../../LICENSE) for details.
