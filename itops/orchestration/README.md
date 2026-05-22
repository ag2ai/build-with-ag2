# IT-Ops orchestration core

The AG2 core of the IT-Ops Triage demo: a custom `ParallelWorkflowAdapter` on
the AG2 Beta agent network, the two-stage incident pipeline (`run_demo.py`), the
file-backed ticket store, the mock world, and the test suite. It runs standalone
as a CLI, and the [`it_ops_app/`](../it_ops_app) backend wraps it live over a
WebSocket — it does not reimplement it.

## What's here

| File | What it is |
|---|---|
| `parallel_workflow.py`      | The custom `ParallelWorkflowAdapter`, its `ParallelWorkflowState`, and two transition targets (`ParallelAgentsTarget`, `DynamicParallelTarget`). Standalone module. |
| `run_demo.py`               | The two-stage orchestration (diagnosis → remediation), the `Ticket` and file-backed `TicketStore`, every agent and its tools, and the CLI entry point. |
| `mock_world.py`             | The **only** mock data: monitored systems, ambient log lines, the canned results the agents' probe tools return, and the injectable incidents. |
| `test_parallel_workflow.py` | 17 unit/state tests that drive the adapter directly, including the WAL-replay charter. |
| `test_e2e_workflow.py`      | 2 end-to-end tests on a real `Hub` with `TestConfig`-scripted agents (no LLM). |
| `mockup.html`               | Static visual reference for the React frontend. Open in any browser. |
| `.env.example`              | Template for the Gemini key. |

## Quickstart

From the repo root (`itops/`), with the project venv created by `uv sync` and a
Gemini key in `itops/.env` (`GEMINI_API_KEY` or `GOOGLE_API_KEY`):

```bash
cd orchestration

# Tests — no API key needed (uses TestConfig). Expect 19 passed.
../.venv/bin/python -m pytest -q

# The demo against real Gemini. Prints every envelope flowing through both stages.
../.venv/bin/python run_demo.py                          # full pipeline (web_5xx)
../.venv/bin/python run_demo.py --incident storage_io_error   # dedup short-circuit

# The frontend visual target.
open mockup.html
```

All agents use `gemini-3.5-flash` (set once in `run_demo.py`; per-agent overrides
are easy).

## A custom adapter is the whole point

AG2 Beta's agent network is built around a swappable adapter seam. Every channel
type is an implementation of the `ChannelAdapter` protocol
(`autogen.beta.network.adapters.base`), registered on the `Hub` with
`hub.register_adapter(...)`. The shipped adapters — `consulting`, `conversation`,
`discussion`, `workflow` — are peers, not a closed set: the design lets you add
your own channel type and have it behave like a first-class citizen of the
network.

This reference design does exactly that. `ParallelWorkflowAdapter` implements the
`ChannelAdapter` protocol, registers a new `"parallel_workflow"` channel type
(`PARALLEL_WORKFLOW_TYPE`), and reuses the built-in `workflow` adapter's
routing/projection helpers — layering on the one thing the built-ins don't do: a
parallel fan-out / fan-in phase. Both the CLI (`run_demo.py`) and the backend
(`it_ops_app/server.py`) wire it in the same way:

```python
hub.register_adapter(ParallelWorkflowAdapter())
channel = await ticketbot.open(type=PARALLEL_WORKFLOW_TYPE, knobs={"graph": ...})
```

## How the adapter works

`ParallelWorkflowAdapter` adds a parallel fan-out / fan-in phase to an otherwise
declarative `TransitionGraph`:

- **Fan-out.** When Triage calls `assign_specialists(...)` (or RemTriage calls
  `assign_fixers(...)`), `DynamicParallelTarget` reads the tool's arguments and
  activates exactly those specialists as a parallel band — they all run
  concurrently, in whatever order their LLM calls finish, not in graph order.
- **Join.** A downstream node (RCA, Resolver) is suppressed until **every**
  member of the band has posted. It fires exactly once, when the last one lands
  — so RCA synthesises over the complete set of findings, never a partial one.
- **Human as a parallel participant.** In remediation, the human operator is
  just another member of the band: the autonomous fixers proceed while the
  operator's sign-off is pending, and the join waits for the operator's reply.

### The WAL-replay invariant

The headline test, `test_wal_replay_charter`, drives a representative
fan-out/fan-in scenario through the adapter, snapshots the live state at every
step, then **independently** re-folds an empty initial state over the same
write-ahead log and asserts byte-equivalence at every step. This is the gate
that proves the WAL is the single source of truth: if any change ever smuggles
in hidden state outside the WAL, this test fails immediately. (It's also why the
adapter's state is byte-stable — e.g. `pending_speakers` is a sorted
`tuple[str, ...]`, not a `set`.)

## Design notes worth carrying forward

### Force a gather-then-decide step structurally, not by prompt

Originally Intake was a single agent with three tools (`list_recent_tickets`,
`mark_as_duplicate`, `proceed_to_triage`) and a prompt telling it to look up
recent tickets first. Real Gemini repeatedly **skipped the lookup** and went
straight to `proceed_to_triage`, hallucinating "no recent matches". Prompt
strengthening did not fix it.

The fix that worked is structural — split Intake into two graph nodes with
disjoint toolsets:

- **`IntakeLookup`** — `tools=[list_recent_tickets]` only. With nothing else
  available, the LLM has no choice but to call it.
- **`IntakeDecide`** — `tools=[proceed_to_triage, mark_as_duplicate]` only. It
  receives the lookup result via the channel transcript and routes.
- A transition `ToolCalled("list_recent_tickets") → AgentTarget(IntakeDecide)`
  connects them, with no path that bypasses the lookup.

"Procedure-step and judgement-step as separate nodes with disjoint toolsets" is
a reusable primitive: any time an agent **must** gather X before deciding Y,
splitting X and Y across nodes is structurally enforceable where a prompt is not.

### `_resolve_routing` doesn't propagate `tool_args`

AG2's `_resolve_routing` populates `routing` with `kind` / `tool` / `reason` /
`target` / `summary` — but not `tool_args`, which `DynamicParallelTarget` needs
to know **which** specialists to activate. `ParallelWorkflowAdapter.build_round_envelope`
therefore walks the `ToolCallEvent`s alongside `_resolve_routing` and attaches
the matched call's parsed arguments to `routing["tool_args"]`, so they ride on
the WAL like everything else. Covered by `test_build_round_envelope_attaches_tool_args`.

### Other gotchas

- **Real Gemini skips optional steps.** If a step matters to the narrative, make
  it structural (its own node, no other tools), not prompt-only.
- **Tool turns are two LLM calls under AG2's tool loop.** When scripting agents
  with `TestConfig`, each tool-calling turn needs two events — the
  `ToolCallEvent` and a trailing string for the post-tool completion.
- **The stuck-channel sweeper checks `expected_next_speaker`,** which is `None`
  during the parallel phase — so parallel-phase turn timeouts aren't enforced.
- **`.env` is loaded from four candidate paths** (script dir, cwd, parent of
  script dir, `$DOTENV_PATH`). If the Gemini key isn't found, the error lists
  them — don't guess.
