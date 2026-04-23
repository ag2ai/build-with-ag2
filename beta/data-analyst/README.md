# Data Analyst (AG2 Beta × Daytona)

An AG2 Beta agent that analyses your CSVs by writing Python, running it inside a **[Daytona](https://daytona.io) sandbox**, and streaming code, stdout, and plots into a browser UI as it works.

## What it does

- **Upload any CSV** (or click the bundled Titanic sample) — the file is copied into a fresh Daytona sandbox.
- **Ask a question in plain English.** The agent:
  1. Loads the dataset, prints `df.info()` + `df.head()`.
  2. Iterates: hypothesis → writes ≤40 lines of Python → `run_python` in the sandbox → reads stdout → refines.
  3. Saves plots under `/home/daytona/artifacts/*.png` and calls `get_artifact` so the UI can render them inline.
  4. Writes a markdown report with **Findings** (concrete numbers) + **Caveats**.
- **Live timeline** on the right shows every tool call as a card — code blocks, stdout, base64-decoded plots — so judges (and you) can actually watch the agent think.

## Why Daytona matters

The agent writes code that did not exist when the process started. Running it inline would be a supply-chain hand grenade. Daytona gives us:

- A throwaway isolated VM per session with pandas/numpy/matplotlib/seaborn preinstalled.
- Real `stdout`/`stderr`/`exit_code` — the agent can see and fix its own tracebacks.
- A filesystem we can `fs.upload_file` the dataset into and `fs.download_file` plots out of.
- No Docker on the user's laptop, no `use_docker=False` footgun, no "let's pip install requests in my main venv".

## AG2 Beta features

| Beta primitive | Role |
|---|---|
| [`autogen.beta.Agent`](https://docs.ag2.ai/docs/beta/agents) | Single data-analyst agent |
| [`@tool`](https://docs.ag2.ai/docs/beta/tools/tools) | `get_loaded_dataset`, `run_python`, `list_files`, `read_text_file`, `get_artifact` |
| [`AGUIStream`](https://docs.ag2.ai/docs/beta/advanced/stream) | Mounts the agent as an SSE endpoint; frontend subscribes directly — no protocol glue code |
| Tool results as structured dicts | `run_python` returns `{stdout, new_artifacts, ...}` so the LLM gets structure, not a stringified blob |

## Stack

- **[AG2 Beta](https://docs.ag2.ai/docs/beta/motivation)** (`autogen.beta`) — agent, tools, AG-UI streaming
- **[Daytona](https://daytona.io)** — isolated Python sandbox
- **FastAPI + uvicorn** — serves the chat endpoint, `/upload`, `/sample`, and the single-file frontend
- **Vanilla HTML + SSE** in `frontend.html` — no build step

## Installation

Requires Python ≥ 3.11.

```bash
cd beta/data-analyst
uv sync
cp .env.example .env
```

Fill in `.env`:

| Variable | Where to get it |
|---|---|
| `GEMINI_API_KEY` | https://aistudio.google.com/apikey |
| `DAYTONA_API_KEY` | https://app.daytona.io → API Keys |

To use OpenAI instead, set `LLM_PROVIDER=openai` and provide `OPENAI_API_KEY` ([platform.openai.com/api-keys](https://platform.openai.com/api-keys)).

## Running

```bash
uv run python backend.py
```

Open http://localhost:8766. Click **🚢 sample (Titanic)** for a one-click demo, or drag-upload your own CSV. Then ask a question — try:

- *What factors predicted survival on the Titanic?*
- *Show me a chart of fare by passenger class.*
- *Is there a gender gap in survival rates?*

## Architecture

```
┌──────────────────┐   SSE (AG-UI)    ┌─────────────────────┐
│  frontend.html   │ ◄──────────────  │  FastAPI + AGUI     │
│  · chat          │                  │  · /chat  (agent)   │
│  · timeline      │  multipart       │  · /upload  (CSV)   │
│    (code/stdout/ │ ───────────────► │  · /sample  (demo)  │
│     plots)       │                  └──────────┬──────────┘
└──────────────────┘                             │ tool calls
                                                 ▼
                                    ┌─────────────────────────┐
                                    │  Daytona sandbox        │
                                    │  · pandas/numpy/mpl     │
                                    │  · /home/daytona/data   │
                                    │  · /home/daytona/       │
                                    │      artifacts          │
                                    └─────────────────────────┘
```

The sandbox is created lazily on the first tool call and reused across every turn in the process — so follow-up questions share the loaded dataframe and any prior artifacts.

## TAGS

data-analysis, sandboxed-execution, code-interpreter, daytona, AG2-Beta, AG-UI, pandas, matplotlib, streaming-ui

## Hackathon

Built for the [AG2 Hackathon @ Fordham Gabelli](https://luma.com/42lzgbrz). Uses sponsor credits for **Daytona** and a sponsor LLM (Gemini or OpenAI).

## License

Apache License 2.0. See the repository [LICENSE](../../LICENSE).
