# Parallel Research (AG2 Beta)

Watch three research agents run **in parallel, live in your terminal**.

A lead coordinator decomposes your question into 3 sub-questions and delegates each to a specialist researcher that uses **[Tavily](https://tavily.com)** to search and fetch the web. All three researchers execute concurrently — their progress streams to the terminal as interleaved lanes — then the lead synthesises a single cited report.

## What it does

- Decomposes a user question into **3 disjoint sub-questions**
- Spawns **3 researcher subagents in parallel** (one `task_researcher_N` tool call each, all emitted in the same turn)
- Streams live progress from every subagent via `MemoryStream` subscribers — one lane per researcher
- Produces a synthesised answer with numbered inline citations and a Sources list
- Supports follow-up questions on the same context via `reply.ask()`

### Example output

```
[lead] 🧭 delegate → researcher_1: What is the AG2 framework and its current status?
[lead] 🧭 delegate → researcher_2: How does CrewAI compare on community activity in 2026?
[lead] 🧭 delegate → researcher_3: Where does LangGraph fit in multi-agent orchestration?
[r1  ] 🔍 search('AG2 autogen multi-agent framework 2026')
[r2  ] 🔍 search('CrewAI multi-agent framework GitHub stars 2026')
[r3  ] 🔍 search('LangGraph multi-agent orchestration LangChain 2026')
[r2  ] 📄 fetch(https://github.com/crewAIInc/crewAI)
[r1  ] 📄 fetch(https://github.com/ag2ai/ag2)
[r3  ] 📄 fetch(https://langchain-ai.github.io/langgraph/)
[lead] ✅ researcher_2 done — 412 chars
[lead] ✅ researcher_1 done — 580 chars
[lead] ✅ researcher_3 done — 497 chars

============================================================
REPORT
============================================================
The top 3 open-source multi-agent frameworks in 2026 are …
[1] [2] [3]

**Sources**
[1] https://github.com/ag2ai/ag2
[2] https://github.com/crewAIInc/crewAI
[3] https://langchain-ai.github.io/langgraph/
============================================================
```

## AG2 Beta features

| Beta primitive | Role in this example |
|---|---|
| [`autogen.beta.Agent`](https://docs.ag2.ai/docs/beta/agents) | Lead coordinator + 3 researchers |
| [`@tool`](https://docs.ag2.ai/docs/beta/tools/tools) | `tavily_search`, `fetch_url` |
| [`subagent_tool`](https://docs.ag2.ai/docs/beta/roadmap) | Wraps each researcher as a delegation tool for the lead |
| [`MemoryStream`](https://docs.ag2.ai/docs/beta/advanced/stream) | Parent + per-researcher substreams with live subscribers |
| `reply.ask()` | Follow-up questions reuse prior context and sources |
| [`GeminiConfig`](https://docs.ag2.ai/docs/beta/model_configuration) | Gemini 2.5 Pro (lead) + Flash (researchers) |

## Why it's Beta-only

| Capability | Classic AG2 | This example (Beta) |
|---|---|---|
| N researchers running concurrently | `ThreadPoolExecutor` + `as_completed` | LLM emits N tool calls per turn → runtime parallelises |
| Live per-researcher progress | Manual queue + print lock | `MemoryStream` subscribers via `StreamFactory` |
| Cited synthesis | Regex-extract JSON from chat | Coordinator sees all sub-results as tool results |
| Follow-ups carry context | Separate Q&A loop, re-reads files | `reply.ask()` — native |
| Lines of code | ~700 (see `due-diligence-with-tinyfish/main.py`) | ~230 |

## Stack

| Component | Role |
| --- | --- |
| **AG2 Beta** (`autogen.beta`) | Agents, tools, subagents, streams |
| **Tavily** | Web search + content extraction |
| **Google Gemini** | Gemini 2.5 Pro (lead) + Gemini 2.5 Flash (researchers) |

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

Open `.env` and fill in:

| Variable | Where to get it |
|---|---|
| `GEMINI_API_KEY` | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| `TAVILY_API_KEY` | [app.tavily.com](https://app.tavily.com) (free tier: 1000 searches/month) |

Optional overrides:

| Variable | Default |
|---|---|
| `LEAD_MODEL` | `gemini-2.5-pro` |
| `RESEARCHER_MODEL` | `gemini-2.5-flash` |

## Running the code

```bash
uv run python main.py
```

You will be prompted for a research question. After the first report, you can keep typing follow-ups; each follow-up reuses the same conversation and sources.

Sample prompts:

- `What are the top 3 open-source multi-agent frameworks in 2026?`
- `Compare the three leading vector databases for RAG at scale.`
- `Summarise the state of Model Context Protocol (MCP) adoption across agent frameworks.`

Type `exit`, `quit`, or an empty follow-up to quit.

## How it's built

The full implementation is ~230 lines in [`main.py`](./main.py):

1. **Two `@tool` functions** (`tavily_search`, `fetch_url`) — shared by every researcher.
2. **A researcher factory** creating N identical `Agent`s on Gemini Flash.
3. **A lead agent** on Gemini Pro, with one `subagent_tool(...)` per researcher.
4. **A `LaneRouter`** that subscribes `ToolCallEvent` / `ToolErrorEvent` / `TaskStarted` / `TaskCompleted` handlers to the parent stream and to each child stream (via a `StreamFactory`), tagging log lines with `[lead]`, `[r1]`, `[r2]`, `[r3]`.
5. **A `reply.ask()` loop** for follow-ups — context (including the already-fetched sources) carries forward automatically.

## Hackathon

Built for the [AG2 Hackathon @ Fordham Gabelli](https://luma.com/42lzgbrz) (May 3). Directly targets **Track #2 — Best Multi-Agent Collaboration on the AG2 Network** and uses sponsor credits for **Tavily** and **Gemini**.

## Links

- [AG2 Beta — Motivation](https://docs.ag2.ai/docs/beta/motivation)
- [AG2 Beta — Agents](https://docs.ag2.ai/docs/beta/agents)
- [AG2 Beta — Stream](https://docs.ag2.ai/docs/beta/advanced/stream)
- [AG2 Beta — Roadmap](https://docs.ag2.ai/docs/beta/roadmap)
- [Tavily Python SDK](https://docs.tavily.com/docs/python-sdk/tavily-python/getting-started)

## License

Apache License 2.0. See the repository [LICENSE](../../LICENSE).
