# Ask the Web (AG2 Beta)

Citation-backed web Q&A with a clean chat UI. Ask anything answerable from the public web — the agent searches with **Tavily**, reads the best 1–3 sources, and streams back an answer with inline `[n]` citations and live source cards on the right.

## What it does

- **Streaming chat** — answer text appears as it's written
- **Live source cards** — every URL the agent fetches shows up in the right rail as it happens, with title, domain, and snippet
- **Inline citations** — `[1]`, `[2]`, `[3]` in the answer are clickable and highlight the matching card on hover
- **Multi-turn** — follow-up questions reuse already-cited sources when they answer the question; otherwise a fresh search kicks off
- **Stops when it's not sure** — the prompt instructs the agent to say "not enough information" rather than speculate

Sample prompts:

- What is Model Context Protocol and who supports it?
- Compare Supabase and Firebase for a small startup in 2026.
- What's new in Claude Sonnet 4.6?
- Is Python 3.14 out? What changed?

## AG2 Beta features used

| Beta primitive | Role |
|---|---|
| [`autogen.beta.Agent`](https://docs.ag2.ai/docs/beta/agents) | The single research agent |
| [`@tool`](https://docs.ag2.ai/docs/beta/tools/tools) | `tavily_search`, `fetch_url` |
| [`autogen.beta.ag_ui.AGUIStream`](https://docs.ag2.ai/docs/beta/ag-ui/) | Mounts the agent at an ASGI endpoint that emits AG-UI protocol events (streaming text, tool call lifecycle) |
| [`GeminiConfig`](https://docs.ag2.ai/docs/beta/model_configuration) / [`OpenAIConfig`](https://docs.ag2.ai/docs/beta/model_configuration) | Env-switchable LLM provider (default: Gemini) |

The entire backend is ~130 lines (`backend.py`). The frontend is a single `frontend.html` with vanilla JS — no build step.

## Stack

| Component | Role |
| --- | --- |
| **AG2 Beta** (`autogen.beta`) | Agent + tools + AG-UI endpoint |
| **Tavily** | Web search + content extraction (uses hackathon credits) |
| **Gemini / OpenAI** | LLM (defaults to `gemini-2.5-pro`) |
| **FastAPI + Uvicorn** | Serves the ASGI endpoint and the static frontend |

## Installation

Requires Python >= 3.11.

### 1. Install dependencies

```bash
uv sync
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Fill in:

| Variable | Where to get it |
|---|---|
| `TAVILY_API_KEY` | [app.tavily.com](https://app.tavily.com) — free 1000/mo |
| `GEMINI_API_KEY` (default provider) | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| `OPENAI_API_KEY` (if `LLM_PROVIDER=openai`) | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |

Optional:

| Variable | Default |
|---|---|
| `LLM_PROVIDER` | `gemini` (set to `openai` to use OpenAI) |
| `MODEL` | `gemini-2.5-pro` for gemini, `gpt-4o` for openai |
| `PORT` | `8765` |

## Running the app

```bash
uv run python backend.py
```

Open http://localhost:8765 in your browser.

Type a question in the input at the bottom. Press **⌘/Ctrl + Enter** or click **Send**. Watch sources appear on the right as the agent works, then the answer stream in with inline citations.

## How it's built

`backend.py` is ~130 lines:

1. Two `@tool` functions: `tavily_search` (Tavily search API) and `fetch_url` (Tavily extract API).
2. An `Agent` with a prompt that forces it to search → fetch → cite, and to refuse to speculate.
3. `AGUIStream(agent)` wraps the agent and exposes it as an ASGI endpoint via `stream.build_asgi()`, mounted at `/chat`.
4. FastAPI serves the frontend at `/`.

`frontend.html` is ~450 lines (mostly CSS):

1. POST the conversation history to `/chat` as an AG-UI `RunAgentInput`.
2. Consume the SSE stream; dispatch on event `type`:
   - `TEXT_MESSAGE_CONTENT` / `TEXT_MESSAGE_CHUNK` → append to the streaming bubble
   - `TOOL_CALL_START` / `TOOL_CALL_ARGS` / `TOOL_CALL_RESULT` → build live source cards from `tavily_search` results and mark cards as `✓ fetched` when `fetch_url` completes
3. Re-render inline `[n]` citations as hover-linked `<cite>` spans that highlight the matching card.

## Why this is only clean on Beta

`autogen.beta.ag_ui.AGUIStream` makes the whole event translation from agent → browser a single-line mount. In classic AG2 the equivalent requires ~200 lines of hand-rolled SSE event translation (see `ag-ui/gpt-researcher/server.py` elsewhere in this repo).

## Hackathon

Built for the [AG2 Hackathon @ Fordham Gabelli](https://luma.com/42lzgbrz) (May 3). Uses sponsor credits for **Tavily** and **Gemini / OpenAI**.

## Links

- [AG2 Beta — Motivation](https://docs.ag2.ai/docs/beta/motivation)
- [AG2 Beta — AG-UI integration](https://docs.ag2.ai/docs/beta/ag-ui/)
- [AG-UI Protocol](https://docs.ag-ui.com/introduction)
- [Tavily Python SDK](https://docs.tavily.com/)

## License

Apache License 2.0. See the repository [LICENSE](../../LICENSE).
