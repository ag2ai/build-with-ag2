# IT-Ops Triage — backend service

FastAPI + WebSocket backend that drives the two-stage IT-ops pipeline live,
for a React frontend to render. It wraps the **proven** orchestration in
`../orchestration/run_demo.py` (diagnosis → remediation, the custom
`ParallelWorkflowAdapter`, and the human-as-parallel-participant HITL) — it
does not reimplement it.

```
React app  ──ws──►  server.py  ──►  run_demo.run_diagnosis / run_remediation
   ▲                   │                 (one persistent Hub + adapter)
   └──── events ───────┘
```

## Run

From this folder, with the project venv (FastAPI + uvicorn are installed in it):

```bash
../.venv/bin/python -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload
```

Smoke-test it headlessly (injects an incident, answers the HITL, asserts the
ticket reaches a terminal status):

```bash
../.venv/bin/python smoke_client.py
```

Requires a Gemini key (`GEMINI_API_KEY` or `GOOGLE_API_KEY`) — loaded from the
repo-root `.env`, same as the CLI demo.

## HTTP endpoints

| Method | Path        | Returns |
|--------|-------------|---------|
| GET    | `/healthz`  | `{ ok, clients, tickets }` |
| GET    | `/snapshot` | `{ tickets: [Ticket, …] }` — current state for a fresh client |

## WebSocket `/ws`

Bidirectional. On connect, the server immediately sends one `snapshot` event.
Every message in both directions is JSON. Server→client events are always
`{ "type": <string>, "payload": <object>, "ts": <epoch seconds> }`.

### Client → server

| `type`           | fields | effect |
|------------------|--------|--------|
| `inject`         | `scenario`: `"full"` \| `"duplicate"` | Start an incident flow. `full` runs both stages (and triggers a HITL escalation); `duplicate` short-circuits in diagnosis. |
| `hitl_response`  | `channel_id`, `decision`: string \| null | Deliver the operator's sign-off for a pending `hitl_requested`. A null/empty `decision` declines (the operator effectively times out). |
| `ping`           | — | Server replies `pong`. |

> Custom incidents (arbitrary system/issue) are a planned extension; today
> `inject` selects one of the two canned scenarios the orchestration ships.

### Server → client events

| `type`            | payload | when |
|-------------------|---------|------|
| `snapshot`        | `{ tickets: [Ticket] }` | once, on connect |
| `ticket_created`  | `Ticket` | a ticket is opened (start of diagnosis) |
| `ticket_status`   | `Ticket` | any status transition |
| `channel_opened`  | `{ channel_id, ticket_id, stage }` | a workflow channel opens — **use this to map a channel to its ticket & stage** |
| `envelope`        | `{ channel_id, sender_id, sender, event_type, text, tool, tool_args, body }` | every accepted envelope — drives the live pipeline animation |
| `hitl_requested`  | `{ channel_id, ticket_id, fixers, rca, recommendations }` | a remediation workflow needs the operator's sign-off — render the HITL box |
| `hitl_resolved`   | `{ channel_id, decision }` | the operator responded (or timed out → `decision: null`) |
| `channel_closed`  | `{ channel_id, reason }` | a workflow ends |
| `pong`            | — | reply to `ping` |
| `error`           | `{ where, detail }` | a flow raised; surfaced rather than crashing |

`stage` ∈ `"diagnosis"`, `"remediation"`.
`channel_closed.reason` ∈ `"remediation_recommended"`, `"duplicate"`, `"resolved"`, `"no_match"`.

#### `envelope.event_type`

Raw AG2 wire constants — the two the UI cares about:

- `ag2.msg.text` — a text post (the kickoff, or the operator's sign-off). Use `text`.
- `ag2.packet` — a tool/routing post. Use `tool`, `tool_args` (e.g. `assign_specialists` → `{specialists:[…]}`, `assign_fixers` → `{fixers:[…]}`), and `body` (the agent's natural-language line).

`ag2.channel.invite` / `ag2.channel.opened` lifecycle frames also arrive on the
`envelope` stream; the UI can ignore them and rely on `channel_opened` instead.

### Ticket shape

```ts
type Ticket = {
  id: string;            // "INC-007"
  system: string;        // "web-edge-01"
  issue: string;         // "web_5xx"
  sev: string;           // "sev1" | "sev2" | "sev3"
  status: string;        // see below
  rca: string;           // populated when diagnosis completes
  confidence: string;    // "low" | "medium" | "high"
  recommendations: string[];
  parent: string | null; // set when status is Duplicate
  resolution: string;    // populated when remediation closes
  history: string[];     // human-readable status trail
};
```

Status lifecycle: `Diagnosing → Remediation_Recommended → Remediating → Resolved`
(or `Partially Resolved` / `Needs Followup`), with `Duplicate` as the
short-circuit branch out of diagnosis.

## Typical event sequence (`inject: full`)

```
ticket_created    INC-007 (Diagnosing)
channel_opened    diagnosis · INC-007
envelope ×N       Intake → Triage → web/storage/network (parallel) → RCA → Remediation
channel_closed    remediation_recommended
ticket_status     INC-007 → Remediation_Recommended
channel_opened    remediation · INC-007
ticket_status     INC-007 → Remediating
envelope          RemTriage assign_fixers({fixers:[storage, config, human]})
hitl_requested    channel … fixers=[…]          ← render the HITL box
   (client sends hitl_response)
hitl_resolved     channel …
envelope          Operator (text), fixers submit_fix, Resolver close_ticket
channel_closed    resolved
ticket_status     INC-007 → Partially Resolved
```

## Mapping to the UI

The mockup at `../orchestration/mockup.html` is the **visual
reference** for the React components. The event stream maps onto it:

- **Diagnosis tab** — `channel_opened(stage=diagnosis)` + `envelope`s drive the
  pipeline rail; `ticket_created` / `ticket_status` drive the ticket table.
- **Remediation tab** — `channel_opened(stage=remediation)` + `envelope`s drive
  the fixer band; `hitl_requested` opens the on-screen response box, whose
  submit sends `hitl_response`; the **active-workflow tab counters** are just
  the count of opened-but-not-closed channels per stage.
