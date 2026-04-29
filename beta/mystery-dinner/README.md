# Mystery Dinner — a multi-agent demo for AG2

A live, browser-rendered murder-mystery game built on
[`autogen.beta`](https://github.com/ag2ai/ag2). A **detective** Agent
interrogates six **suspect** Agents while a **commentator** Agent
narrates the action, all streamed to the browser through the AG-UI
event protocol.

It's a working example of:

- Three roles, three independent `Agent`s with their own LLM configs
  and prompts.
- One Agent calling another via a `@tool` that wraps
  `await suspect.ask(...)`.
- A shared `CASE_MEMORY` with a tiny pub/sub hook driving the live
  notebook and the commentary feed.
- `AGUIStream` exposing every Agent as an ASGI route the browser can
  consume directly.
- `GameMaster` + `GameClock` wrapping the rules and the 10-minute
  timer.

The home page ships with a built-in **"AG2 — Behind the Scenes"** tour
that walks new readers through the architecture in six pages, ending
with a one-page system diagram.

## Quick start

```bash
# 1. clone + venv
python -m venv .venv
source .venv/bin/activate

# 2. install
pip install -r requirements.txt

# 3. set up your API key (Gemini is the default for all three agents)
cp .env.example .env
# then edit .env and paste your key

# 4. run
python -m app.server
# open http://127.0.0.1:8000
```

Click any of the four directive cards on the splash to start a run, or
hit **AG2 — Behind the Scenes** to read the architecture tour first.

## Configuration

All knobs live in [`app/config.py`](app/config.py):

```python
GAME_DURATION_SECONDS = 10 * 60   # length of one run
WITHDRAWALS_ALLOWED   = 1         # bad-evidence retries before loss

def detective_llm_config():    return GeminiConfig(model="…", streaming=True)
def suspect_llm_config():      return GeminiConfig(model="…", streaming=True)
def commentator_llm_config():  return GeminiConfig(model="…", streaming=True)
```

Swap any factory for `OpenAIConfig`, `VertexAIConfig`, etc. — every
Agent that uses it picks up the change on the next server restart.

## Project layout

```
app/
├── server.py              # Starlette ASGI app + AG-UI / SSE routes
├── config.py              # ★ Single source of truth — LLM + game knobs
├── game_master.py         # Verdict logic, withdrawals, end of game
├── clock.py               # 10-minute game clock with freeze-on-verdict
├── memory.py              # CASE_MEMORY — pub/sub fact + turn store
├── commentary.py          # CommentaryEngine (memory observer → Agent)
├── agents/
│   ├── detective.py       # Detective Agent + 4 tools
│   ├── suspect.py         # Suspect Agent builder (one per profile)
│   ├── commentator.py     # Commentator Agent + 2 read-only peek tools
│   └── eleanor.py         # Tiny example of a single suspect builder
├── cases/
│   └── blackwood_estate.py  # Case data: profiles, dossiers, killer, window
└── static/                # Vanilla JS / CSS / HTML — no framework
Images/                    # Suspect portraits, location art, avatars
requirements.txt
.pre-commit-config.yaml    # ruff (+ format) and basic hooks
```

## How a turn flows

The Behind-the-Scenes tour shows a diagram of this, but in short:

1. The user clicks a directive. The browser POSTs it to
   `/agent/detective`.
2. `AGUIStream` runs the detective Agent; its first tool call is
   `ask_suspect("eleanor", "...")`.
3. Inside that tool, `await suspect.ask(question)` runs Eleanor's
   Agent. Her LLM sees an *invoked* question and calls
   `query_dossier`.
4. The detective's tool walks Eleanor's event history and writes a
   `VerifiedFact` into `CASE_MEMORY`.
5. The memory pub/sub wakes the `CommentaryEngine`; the commentator
   Agent emits a one-liner to the SSE feed.
6. Three browser streams — AG-UI events, notebook SSE, commentary
   SSE — update the UI live.
7. Eventually the detective calls `accuse(...)`.
   `GameMaster.finalize()` freezes the clock and stamps the elapsed
   time on the verdict.

## Where to start reading

- **`app/agents/detective.py`** — the orchestrating Agent. Shows how a
  tool can wrap `await other_agent.ask(...)` and harvest events.
- **`app/agents/suspect.py`** — the per-character Agent builder, plus
  the `query_dossier` `@tool` that closes over each suspect's private
  records.
- **`app/memory.py`** — the shared notebook. Two dataclasses + a
  10-line pub/sub.
- **`app/server.py`** — Starlette wiring; one
  `AGUIStream(agent).build_asgi()` per Agent route.

## Notes on auth

The default config uses Google's Gemini. Two ways to authenticate
(pick one):

1. **API key** — get one at https://aistudio.google.com/apikey, put it
   in `.env` as `GOOGLE_API_KEY=...`. Easiest path.
2. **Vertex AI / ADC** — `gcloud auth application-default login`
   instead. Useful if your org provides Vertex access.

If you swap to OpenAI / Anthropic in `app/config.py`, set the
matching env var (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) in `.env`.

## Dev loop

```bash
pre-commit install      # one-time, optional
pre-commit run --all-files
```

`ruff` + `ruff-format` are wired up to keep the Python tidy.
