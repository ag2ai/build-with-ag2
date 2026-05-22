# IT-Ops Triage — AG2 multi-agent demo

A live demonstration of AG2 OSS workflow design for IT operations: an **agentic,
two-stage incident pipeline** with parallel specialists, human-in-the-loop
sign-off, persisted tickets, and a real-time React UI.

```
inject incident
   │
   ▼  Stage 1 · Diagnosis            Stage 2 · Remediation (auto-spawned)
   ┌──────────────────────────┐      ┌──────────────────────────────────────┐
   │ Intake (dedup) > Triage  │      │ RemTriage → Infra / Storage / Config │
   │ > Network . Storage . Web│  >   │  fixers  .  Operator (human sign-off)│ >  Resolved
   │ > RCA → Recommend        │      │ → Resolver                           │
   └──────────────────────────┘      └──────────────────────────────────────┘
        ticket: Remediation_Recommended            ticket: Resolved / Partially Resolved
```

The parallel fan-out / fan-in (and the "human as a parallel participant" HITL)
isn't built into AG2 — it's added by a **custom channel adapter**, and that's the
point of this reference design. AG2 Beta's agent network is built around a
swappable `ChannelAdapter` seam: the shipped channel types (`consulting`,
`conversation`, `discussion`, `workflow`) are each an implementation of that one
protocol, and you can register your own. This design ships one —
`ParallelWorkflowAdapter`, a new `parallel_workflow` channel type registered on
the `Hub` — to get parallel orchestration the built-in adapters don't provide.
See [`orchestration/`](orchestration/) for how it plugs in.

## Repo layout

| Folder | What it is |
|---|---|
| `orchestration/` | The AG2 core: the custom `ParallelWorkflowAdapter`, the two-stage orchestration (`run_demo.py`), the **persisted file-backed ticket store**, `mock_world.py` (the *only* mock data), and the test suite. Runs standalone as a CLI. |
| `it_ops_app/` | FastAPI + WebSocket service that wraps the orchestration and streams it live (`server.py`). WebSocket contract: [`it_ops_app/README.md`](it_ops_app/README.md). |
| `frontend/` | React (Vite) UI that connects to the backend over WebSocket. |

## Prerequisites

- **Python 3.12** + [`uv`](https://docs.astral.sh/uv/)
- **Node 18+** / `npm`
- A **Google Gemini API key** (all agents use `gemini-3.5-flash`)

## Setup

1. **API key** — create `.env` in this repo root:
   ```
   GEMINI_API_KEY=your-key-here    # GOOGLE_API_KEY also works
   ```
2. **Python deps** (creates `.venv` with ag2 + fastapi + uvicorn):
   ```bash
   uv sync
   ```
3. **Frontend deps:**
   ```bash
   cd frontend && npm install
   ```

## Run the full app (backend + frontend)

**Terminal 1 — backend** (FastAPI + WebSocket on :8000):
```bash
cd it_ops_app
../.venv/bin/python -m uvicorn server:app --host 127.0.0.1 --port 8000
```

**Terminal 2 — frontend** (Vite dev server on :5173):
```bash
cd frontend
npm run dev
```

Open **http://localhost:5173**, then:
1. Click **Start Simulation** (top-right) — this resets to a clean slate and goes live.
2. On **Monitoring**, click an **Inject** button (e.g. *HTTP 502 burst*) to open a ticket and kick off a diagnosis workflow.
3. Watch it on **Live Investigation** (Diagnosis → Remediation). When a fixer needs sign-off, the ticket is flagged **needs human input**; click **Approve remediation** to let it finish.
4. **Investigations** lists every ticket and its status.

Inject the *same* incident twice → the second is detected as a real **duplicate**
of the first (dedup runs against the actual persisted tickets).

## Run the CLI proof (no UI — just the agents, against real Gemini)

```bash
cd orchestration
../.venv/bin/python run_demo.py                          # full two-stage pipeline (web_5xx)
../.venv/bin/python run_demo.py --incident storage_io_error
```
It prints every envelope flowing through both workflows.

## Tests

```bash
cd orchestration
../.venv/bin/python -m pytest -q          # adapter + end-to-end (no LLM, uses TestConfig)
```
(19 tests, including a WAL-replay charter that proves the adapter's state is
reconstructible from the write-ahead log.)

## How it works (in brief)

- **Tickets are real & persisted** — one JSON file per ticket under `orchestration/tickets/` (created on inject, updated through the lifecycle). Dedup queries these real tickets — nothing is faked.
- **Stage 1 (Diagnosis):** Intake dedups, Triage fans out to Network/Storage/Web specialists in parallel, RCA synthesises, Remediation recommends fixes → ticket becomes `Remediation_Recommended`.
- **Stage 2 (Remediation):** auto-spawned per recommended ticket. RemTriage fans out Infra/Storage/Config fixers **plus a human operator** in parallel; the autonomous fixers proceed while the operator's sign-off is pending (the ticket shows `needs_human`); the Resolver writes up the outcome → `Resolved` / `Partially Resolved`.
- **Start Simulation** = clean slate (deletes the ticket files). Tickets otherwise persist across backend restarts.
- The **only mock data** is `orchestration/mock_world.py` (monitored systems, ambient logs, the canned results the agents' probe tools return, and the injectable incidents). Tickets, agent activity, evidence, RCA, and HITL are all produced live.

## Notes

- **Model:** all agents use Gemini `gemini-3.5-flash` (set once in `run_demo.py`; per-agent overrides are easy).
- The backend re-uses the proven orchestration in `orchestration/` — it does not reimplement it.
- For the live event/control contract the frontend builds against, see [`it_ops_app/README.md`](it_ops_app/README.md).
