# GPT Researcher + AG2

Integrates [GPT Researcher](https://github.com/assafelovic/gpt-researcher) with AG2 and provides a realtime UI using the [AG-UI protocol](https://docs.ag2.ai/latest/docs/user-guide/ag-ui/). A single orchestrator agent wraps GPT Researcher as a tool and streams pipeline stage updates and the final report to a browser frontend in real time.

Comes with two run modes:

- **`main.py`** — terminal mode, runs the pipeline and prints the report
- **`server.py`** — web UI mode, serves `frontend.html` with live stage updates and streamed report output

The frontend is a single HTML file (no React, no build step) that reads `STATE_SNAPSHOT` events over SSE to highlight which pipeline stage is currently active.

## AG2 Features

- [AG-UI Protocol](https://docs.ag2.ai/latest/docs/user-guide/ag-ui/) — streaming typed events to a browser frontend
- [ConversableAgent](https://docs.ag2.ai/latest/docs/user-guide/agentchat-user-guide/basics/conversable-agent/) — orchestrator agent with a single research tool
- [Tool Use / Function Calling](https://docs.ag2.ai/latest/docs/user-guide/agentchat-user-guide/basics/tools/) — `run_research` wraps `GPTResearcher.conduct_research()` and `write_report()`
- [Context Variables](https://docs.ag2.ai/latest/docs/user-guide/advanced-concepts/orchestration/group-chat/context-variables/) — `stage` and `active_agent` updated between phases; `AGUIStream` emits `STATE_SNAPSHOT` events automatically

## TAGS

TAGS: ag-ui, gpt-researcher, research, streaming, tool-use, context-variables, sse, fastapi

## File Structure

| File | Description |
|---|---|
| `main.py` | Terminal mode — loads `task.json`, runs GPT Researcher, prints the report |
| `server.py` | Web UI mode — FastAPI server with `AGUIStream`, serves the frontend |
| `frontend.html` | Two-panel UI (report output + pipeline progress panel) |
| `requirements.txt` | Python dependencies |
| `task.json` | Default research task configuration |

## Installation

1. Clone and navigate to the folder:

   ```bash
   git clone https://github.com/ag2ai/build-with-ag2.git
   cd build-with-ag2/ag-ui/gpt-researcher
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set your API keys. GPT Researcher uses Tavily for web search by default:

   ```bash
   export OPENAI_API_KEY="sk-..."
   export TAVILY_API_KEY="tvly-..."
   ```

   Or create a `.env` file:

   ```
   OPENAI_API_KEY=sk-...
   TAVILY_API_KEY=tvly-...
   ```

   Get a free Tavily key at https://tavily.com. Alternatively, set `RETRIEVER=bing`, `RETRIEVER=google`, or another [supported retriever](https://docs.gptr.dev/docs/gpt-researcher/search-engines/retrievers) and supply the corresponding API key.

## Running the Code

### Terminal mode

```bash
python main.py
```

### Web UI mode

```bash
python server.py
```

Open http://localhost:8457 in your browser. Enter a research question and click **Research**. The right panel highlights each pipeline agent as it becomes active; the report streams into the left panel when complete.

## How Pipeline State Reaches the Frontend

AGUIStream emits `STATE_SNAPSHOT` events *between* agent turns, not during a single long-running tool call. To make each pipeline stage visible in the UI, the work is split across three tools that the LLM calls in sequence:

| Tool | Agent | Work done |
|---|---|---|
| `start_research` | Chief Editor | Initializes `GPTResearcher`, oversees the pipeline |
| `plan_research` | Editor | LLM plans 3–5 report sections; stores the outline |
| `conduct_research` | Researcher | Calls `researcher.conduct_research()`, returns source list and findings summary |
| `review_research` | Reviewer | LLM scores research quality and identifies gaps |
| `revise_research` | Revisor | Runs a supplementary `GPTResearcher` search for gaps, or confirms research is complete |
| `write_report` | Writer | Calls `researcher.write_report()` to compile the full report |
| `publish_report` | Publisher | Stamps the report with source count and date, returns final output |

After each tool returns a `ReplyResult` with updated `context_variables`, AGUIStream compares the new context to the previous snapshot and emits a `STATE_SNAPSHOT` event before the LLM's next turn:

```python
# Each tool sets context_variables and returns a ReplyResult.
# AGUIStream detects the change and sends STATE_SNAPSHOT to the frontend
# before the LLM decides to call the next tool.

context_variables["stage"] = "researching"
context_variables["active_agent"] = "Researcher"
await _researcher.conduct_research()
return ReplyResult(message="Research complete. Call write_report next.",
                   context_variables=context_variables)
```

The frontend listens for `STATE_SNAPSHOT` and updates the progress panel — no polling, no extra wiring.

## Contact

- AG2 Documentation: https://docs.ag2.ai/docs/Home
- AG2 GitHub: https://github.com/ag2ai/ag2
- GPT Researcher: https://github.com/assafelovic/gpt-researcher
- Discord: https://discord.gg/pAbnFJrkgZ

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](../../LICENSE) for details.
