# GPT Researcher + AG2

Integrates the [GPT Researcher](https://github.com/assafelovic/gpt-researcher) multi-agent pipeline with AG2 and exposes it via the [AG-UI protocol](https://docs.ag2.ai/latest/docs/user-guide/ag-ui/). A single orchestrator agent wraps the GPT Researcher `ChiefEditorAgent` as a tool and streams pipeline progress and the final report to a browser frontend in real time.

Comes with two run modes:

- **`main.py`** — terminal mode, runs the pipeline and prints the report
- **`server.py`** — web UI mode, serves `frontend.html` with live pipeline stage updates and streamed report output

The frontend is a single HTML file (no React, no build step) that reads `STATE_SNAPSHOT` events over SSE to highlight which pipeline agent is currently active.

## AG2 Features

- [AG-UI Protocol](https://docs.ag2.ai/latest/docs/user-guide/ag-ui/) — streaming typed events to a browser frontend
- [ConversableAgent](https://docs.ag2.ai/latest/docs/user-guide/agentchat-user-guide/basics/conversable-agent/) — orchestrator agent with a single research tool
- [Tool Use / Function Calling](https://docs.ag2.ai/latest/docs/user-guide/agentchat-user-guide/basics/tools/) — `run_research` wraps the full GPT Researcher pipeline
- [Context Variables](https://docs.ag2.ai/latest/docs/user-guide/advanced-concepts/orchestration/group-chat/context-variables/) — `stage` and `active_agent` updated during execution; `AGUIStream` emits `STATE_SNAPSHOT` events automatically

## TAGS

TAGS: ag-ui, gpt-researcher, multi-agent, streaming, tool-use, context-variables, sse, fastapi, research

## File Structure

| File | Description |
|---|---|
| `main.py` | Terminal mode — loads `task.json`, runs GPT Researcher, prints the report |
| `server.py` | Web UI mode — FastAPI server with `AGUIStream`, serves the frontend |
| `frontend.html` | Two-panel UI (report output + pipeline progress panel) |
| `requirements.txt` | Python dependencies |
| `task.json` | Default research task configuration |

## Prerequisites

This example depends on `multi_agents_ag2` from the GPT Researcher repository. Clone it and install its dependencies first:

```bash
git clone https://github.com/assafelovic/gpt-researcher.git
cd gpt-researcher
pip install -r requirements.txt
pip install -r multi_agents_ag2/requirements.txt
```

Then install this example's dependencies:

```bash
pip install -r /path/to/ag-ui/gpt-researcher/requirements.txt
```

Copy (or symlink) the example files into the `gpt-researcher` directory, since `multi_agents_ag2` must be importable at runtime:

```bash
cp /path/to/ag-ui/gpt-researcher/{main.py,server.py,frontend.html,task.json} .
```

## Configuration

Set your OpenAI API key:

```bash
export OPENAI_API_KEY="sk-..."
```

Or create a `.env` file:

```
OPENAI_API_KEY=sk-...
```

Edit `task.json` to change the default research query and settings:

```json
{
  "query": "Is AI in a hype cycle?",
  "max_sections": 3,
  "max_revisions": 3,
  "publish_formats": { "markdown": true },
  "model": "gpt-4o"
}
```

## Running the Code

### Terminal mode

```bash
python -m main
```

### Web UI mode

```bash
python -m server
```

Open http://localhost:8457 in your browser. Enter a research question and click **Research**. The right panel highlights each pipeline agent as it becomes active; the report streams into the left panel when complete.

## How Pipeline State Reaches the Frontend

`run_research` mutates `context_variables` at two points — when research starts and when it completes — and `AGUIStream` automatically detects the changes and emits `STATE_SNAPSHOT` events:

```python
context_variables["stage"] = "planning"
context_variables["active_agent"] = "Chief Editor"
# ... run pipeline ...
context_variables["stage"] = "complete"
context_variables["active_agent"] = "Publisher"
```

The frontend listens for `STATE_SNAPSHOT` and updates the progress panel accordingly — no polling, no extra wiring.

For finer-grained per-agent updates (highlighting Researcher, Reviewer, etc. mid-run), subclass `ChiefEditorAgent` and add `context_variables` mutations inside each stage method.

## Contact

- AG2 Documentation: https://docs.ag2.ai/docs/Home
- AG2 GitHub: https://github.com/ag2ai/ag2
- GPT Researcher: https://github.com/assafelovic/gpt-researcher
- Discord: https://discord.gg/pAbnFJrkgZ

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](../../LICENSE) for details.
