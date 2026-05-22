"""FastAPI + WebSocket backend for the IT-Ops Triage demo.

Wraps the proven two-stage orchestration in
``orchestration/run_demo.py`` (diagnosis → remediation, with the
``ParallelWorkflowAdapter`` and the human-as-parallel-participant HITL) and
exposes it over a WebSocket so a React frontend can drive it live.

  ┌─ AG2 orchestration core (run_demo.run_diagnosis / run_remediation)
  │     • one persistent Hub + ParallelWorkflowAdapter
  │     • emits domain events (channel_opened, ticket_created/status)
  │     • envelope activity captured by a Hub listener
  │     • operator sign-off supplied by an injected `decide` provider
  ▼
  FastAPI service (this file)
     WS  /ws        bidirectional:
                      server → client : {"type", "payload", "ts"} events
                      client → server : {"type":"inject", "scenario": "full"|"duplicate"}
                                        {"type":"hitl_response", "channel_id", "decision"}
                                        {"type":"ping"}
     GET /healthz    liveness
     GET /snapshot   current tickets (for a freshly-loaded client)
  ▼
  React app (separate; connects to ws://<host>/ws)

Run (from this folder, with the project venv):

    uvicorn server:app --reload --port 8000

The WebSocket event contract is documented in README.md.
"""

from __future__ import annotations

import asyncio
import random
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace

# Make the orchestration folder importable so we can reuse the proven
# orchestration and the custom adapter without copying anything.
_CORE = Path(__file__).resolve().parent.parent / "orchestration"
sys.path.insert(0, str(_CORE))

import mock_world as mw  # the only mock data  # noqa: E402
import run_demo as core  # the orchestration core  # noqa: E402
from autogen.beta.knowledge import MemoryKnowledgeStore  # noqa: E402
from autogen.beta.network import (  # noqa: E402
    EV_PACKET,
    EV_TEXT,
    BaseHubListener,
    Hub,
    LocalLink,
)
from fastapi import FastAPI, WebSocket, WebSocketDisconnect  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from parallel_workflow import ParallelWorkflowAdapter  # noqa: E402

# ─── Shared mutable server state ────────────────────────────────────────
# Populated in the lifespan handler; referenced by the WS endpoint.
# Bound simultaneous flows + a short debounce. The debounce only swallows a
# rapid burst of duplicate inject messages (e.g. an accidental double-click or
# a glitch); every *deliberate* inject — including repeats of the same incident
# — creates its own ticket. Flows that block at the HITL still count toward the
# cap, so the cap is generous.
MAX_CONCURRENT_FLOWS = 6
INJECT_DEBOUNCE_SECONDS = 1.5

S = SimpleNamespace(
    hub=None,
    link=None,
    store=None,
    id_to_name=None,
    event_queue=None,
    clients={},  # websocket -> cursor (count of event_log entries already delivered)
    pending_hitl={},  # channel_id -> asyncio.Future[str | None]
    flows=set(),  # in-flight _run_flow asyncio.Tasks (cap + reset cancellation)
    last_inject={},  # incident key -> last inject timestamp (rapid-dupe debounce)
    event_log=[],  # chronological events, replayed to (re)connecting clients
    sim_running=False,  # is the simulation "live" (broadcast so all clients agree)
    broadcaster=None,  # asyncio.Task
    ambient_task=None,  # asyncio.Task generating the backend-owned ambient log stream
)


# ─── Event helpers ──────────────────────────────────────────────────────


def emit(kind: str, payload: dict) -> None:
    """Append an event to the log and wake the broadcaster. Delivery is
    cursor-based off the log (see _broadcast_loop), so every client — including
    one that just connected mid-flight — receives every event exactly once, in
    order, with no gap and no duplicate. Sync + non-blocking, safe to call from
    inside the orchestration."""
    S.event_log.append({"type": kind, "payload": payload, "ts": time.time()})
    if len(S.event_log) > 4000:
        drop = len(S.event_log) - 4000
        del S.event_log[:drop]
        for ws in list(S.clients):  # keep cursors aligned with the trimmed log
            S.clients[ws] = max(0, S.clients[ws] - drop)
    if S.event_queue is not None:
        S.event_queue.put_nowait(1)  # wake signal; payload unused


def _ticket_json(t: core.Ticket) -> dict:
    return {
        "id": t.id,
        "system": t.system,
        "issue": t.issue,
        "sev": t.sev,
        "status": t.status,
        "rca": t.rca,
        "confidence": t.confidence,
        "recommendations": list(t.recommendations),
        "parent": t.parent,
        "resolution": t.resolution,
        "history": list(t.history),
        "needs_human": t.needs_human,
        "human_prompt": t.human_prompt,
        "created_at": t.created_at,
    }


class EmittingTicketStore(core.TicketStore):
    """File-backed ticket store that also emits an event on every create /
    update / status / human-flag change, so the UI sees the lifecycle live."""

    def create(self, ticket: core.Ticket) -> core.Ticket:
        t = super().create(ticket)
        emit("ticket_created", _ticket_json(t))
        return t

    def update(self, ticket_id: str, **changes):
        t = super().update(ticket_id, **changes)
        if t is not None:
            emit("ticket_status", _ticket_json(t))
        return t

    def set_status(self, ticket_id: str, status: str, note: str = ""):
        t = super().set_status(ticket_id, status, note)
        if t is not None:
            emit("ticket_status", _ticket_json(t))
        return t

    def set_needs_human(self, ticket_id: str, needs: bool, prompt: str = ""):
        t = super().set_needs_human(ticket_id, needs, prompt)
        if t is not None:
            emit("ticket_status", _ticket_json(t))
        return t


class WSListener(BaseHubListener):
    """Forwards every accepted envelope (and channel close) to the UI as a
    structured event. Names resolve through the shared id→name map that
    the orchestration populates as it registers agents."""

    def __init__(self, id_to_name: dict[str, str]) -> None:
        self.id_to_name = id_to_name

    async def on_envelope_posted(self, envelope, metadata) -> None:
        routing = (
            (envelope.event_data.get("routing") or {})
            if envelope.event_type == EV_PACKET
            else {}
        )
        emit(
            "envelope",
            {
                "channel_id": envelope.channel_id,
                "sender_id": envelope.sender_id,
                "sender": self.id_to_name.get(envelope.sender_id, envelope.sender_id),
                "event_type": envelope.event_type,
                "text": (
                    envelope.event_data.get("text")
                    if envelope.event_type == EV_TEXT
                    else None
                ),
                "tool": routing.get("tool"),
                "tool_args": routing.get("tool_args"),
                "body": envelope.event_data.get("body"),
            },
        )

    async def on_channel_event(self, channel_id, kind, payload) -> None:
        if kind == "closed":
            emit(
                "channel_closed",
                {
                    "channel_id": channel_id,
                    "reason": payload.get("reason"),
                },
            )


# ─── HITL provider injected into the orchestration ──────────────────────


async def web_decide(ctx: dict) -> str | None:
    """Operator-decision provider for the web service.

    Surfaces the escalation to the UI (``hitl_requested``) and awaits the
    operator's response, delivered by a ``hitl_response`` WS message. The
    workflow's join blocks on the operator's reply, so the channel stays
    open — with the autonomous fixers still working — until this resolves.
    """
    channel_id = ctx["channel_id"]
    ticket_id = ctx.get("ticket_id")
    loop = asyncio.get_event_loop()
    fut: asyncio.Future = loop.create_future()
    S.pending_hitl[channel_id] = fut
    # Flag the ticket as needing human input (persisted + broadcast for the UI).
    if ticket_id:
        recs = ctx.get("recommendations") or []
        prompt = "Human sign-off required for the disruptive remediation step."
        if recs:
            prompt += " Recommended: " + "; ".join(recs)
        S.store.set_needs_human(ticket_id, True, prompt)
    emit("hitl_requested", ctx)
    try:
        decision = await asyncio.wait_for(fut, timeout=900.0)
    except TimeoutError:
        decision = None
    finally:
        S.pending_hitl.pop(channel_id, None)
        if ticket_id:
            S.store.set_needs_human(ticket_id, False)
    emit("hitl_resolved", {"channel_id": channel_id, "decision": decision})
    return decision


# ─── Incident flow (one inject → diagnosis → maybe remediation) ─────────


async def _run_flow(incident_key: str) -> None:
    """Run a full incident flow on the shared hub. Fire-and-forget task."""
    try:
        inc = mw.incident(incident_key)
        diag = await core.run_diagnosis(
            S.hub,
            S.link,
            S.id_to_name,
            S.store,
            inc,
            emit=emit,
        )
        if diag["reason"] == "remediation_recommended":
            await core.run_remediation(
                S.hub,
                S.link,
                S.id_to_name,
                S.store,
                diag["ticket_id"],
                decide=web_decide,
                emit=emit,
            )
    except Exception as exc:  # surface, never crash the server
        emit("error", {"where": "flow", "detail": repr(exc)})


async def _reset() -> None:
    """Reset to a clean slate — used by 'Start Simulation' so every run starts
    from scratch. Cancels in-flight flows, clears tickets/tracking, resets the
    ticket numbering, and tells every client to clear its view."""
    for task in list(S.flows):
        task.cancel()
    if S.flows:
        await asyncio.gather(*S.flows, return_exceptions=True)
    S.flows.clear()
    # Unblock any pending operator sign-off so nothing hangs.
    for fut in list(S.pending_hitl.values()):
        if not fut.done():
            fut.set_result(None)
    S.pending_hitl.clear()
    S.last_inject.clear()
    # Fresh application state — delete the persisted ticket files so the board
    # is clean and numbering restarts at INC-007.
    S.store.clear()
    S.id_to_name.clear()
    S.event_log.clear()  # so reconnecting clients don't replay the old run
    for ws in list(S.clients):  # rewind cursors to match the cleared log
        S.clients[ws] = 0
    emit("reset", {})


# ─── Broadcaster ────────────────────────────────────────────────────────


async def _broadcast_loop() -> None:
    """Single delivery point. On each wake, send every client the slice of the
    event log past its cursor — so a fresh connect (cursor 0 → full backlog) and
    live streaming flow through the exact same ordered path. No replay race, no
    gaps, no duplicates, no out-of-order."""
    while True:
        await S.event_queue.get()
        # Coalesce any other pending wake signals into this single pass.
        try:
            while True:
                S.event_queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
        log_len = len(S.event_log)
        for ws, cursor in list(S.clients.items()):
            if cursor >= log_len:
                continue
            try:
                for event in S.event_log[cursor:log_len]:
                    await ws.send_json(event)
                S.clients[ws] = log_len
            except Exception:
                S.clients.pop(ws, None)


# ─── Backend-owned log stream ───────────────────────────────────────────
# The log stream is generated and owned by the backend (not the browser), so
# every client sees the SAME stream and it survives reload/reconnect via the
# event-log replay — exactly like tickets. 'log' events carry the timestamp in
# their envelope `ts`, so replayed lines keep their original time.


def _emit_log(service: str, message: str, level: str = "info") -> None:
    emit("log", {"service": service, "message": message, "level": level})


async def _ambient_logs_loop() -> None:
    """While the sim is live, emit one random healthy log line ~every 1.5s."""
    services = list(mw.AMBIENT_LOGS)
    while True:
        await asyncio.sleep(1.5)
        if not S.sim_running or not services:
            continue
        service = random.choice(services)
        lines = mw.AMBIENT_LOGS.get(service) or []
        if lines:
            _emit_log(service, random.choice(lines), "info")


# ─── App lifespan: stand up / tear down the hub ─────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    S.hub = await Hub.open(
        MemoryKnowledgeStore(),
        ttl_sweep_interval=0,
        expectation_sweep_interval=0,
    )
    S.hub.register_adapter(ParallelWorkflowAdapter())
    S.link = LocalLink(S.hub)
    S.id_to_name = {}
    S.store = EmittingTicketStore()
    S.event_queue = asyncio.Queue()
    S.hub.register_listener(WSListener(S.id_to_name))
    S.broadcaster = asyncio.create_task(_broadcast_loop())
    S.ambient_task = asyncio.create_task(_ambient_logs_loop())
    try:
        yield
    finally:
        for task in (S.broadcaster, S.ambient_task):
            if task is not None:
                task.cancel()
        try:
            await S.hub.close()
        except Exception:
            pass


app = FastAPI(title="IT-Ops Triage demo backend", lifespan=lifespan)

# Permissive CORS for local React dev (Vite default :5173, CRA :3000, …).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True, "clients": len(S.clients), "tickets": len(S.store.all())}


@app.get("/snapshot")
async def snapshot() -> dict:
    return {"tickets": [_ticket_json(t) for t in S.store.all()]}


@app.get("/world")
async def world() -> dict:
    """The mock-world setup the frontend renders: the monitored systems,
    ambient (healthy) log lines, and the catalog of injectable incidents
    (with their error log lines). Tickets / agents / evidence / RCA / HITL
    are NOT here — those are produced live and arrive over the WebSocket."""
    return {
        "systems": mw.SYSTEMS,
        "ambient_logs": mw.AMBIENT_LOGS,
        "incidents": [
            {k: v for k, v in inc.items() if k != "kickoff"} for inc in mw.INCIDENTS
        ],
    }


@app.websocket("/ws")
async def ws(websocket: WebSocket) -> None:
    await websocket.accept()
    # Register at cursor 0 and wake the broadcaster. It will deliver the full
    # backlog (rebuilding tickets, in-flight channels, agents, evidence, HITL)
    # and then every live event from the same ordered path — airtight, no race.
    S.clients[websocket] = 0
    if S.event_queue is not None:
        S.event_queue.put_nowait(1)
    try:
        while True:
            msg = await websocket.receive_json()
            kind = msg.get("type")
            if kind == "inject":
                incident_key = msg.get("incident") or mw.incident_keys()[0]
                if incident_key not in mw.incident_keys():
                    incident_key = mw.incident_keys()[0]
                now = time.time()
                if now - S.last_inject.get(incident_key, 0) < INJECT_DEBOUNCE_SECONDS:
                    emit(
                        "inject_ignored",
                        {
                            "incident": incident_key,
                            "reason": "debounced — injected a moment ago",
                        },
                    )
                elif len(S.flows) >= MAX_CONCURRENT_FLOWS:
                    emit(
                        "inject_ignored",
                        {"incident": incident_key, "reason": "at concurrency cap"},
                    )
                else:
                    S.last_inject[incident_key] = now
                    # Splice the incident's error lines into the log stream.
                    inc = mw.incident(incident_key)
                    for line in inc.get("error_logs", []):
                        _emit_log(inc["system"], line, "error")
                    task = asyncio.create_task(_run_flow(incident_key))
                    S.flows.add(task)
                    task.add_done_callback(S.flows.discard)
            elif kind == "start":
                # Start = clean slate + go live; broadcast so every client agrees.
                await _reset()
                S.sim_running = True
                emit("sim_state", {"running": True})
            elif kind == "stop":
                S.sim_running = False
                emit("sim_state", {"running": False})
            elif kind == "reset":
                await _reset()
            elif kind == "hitl_response":
                fut = S.pending_hitl.get(msg.get("channel_id"))
                if fut is not None and not fut.done():
                    fut.set_result(msg.get("decision"))
            elif kind == "ping":
                await websocket.send_json({"type": "pong", "ts": time.time()})
    except WebSocketDisconnect:
        pass
    finally:
        S.clients.pop(websocket, None)
