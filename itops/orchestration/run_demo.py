"""Runnable end-to-end demo of the IT-ops triage + remediation pipeline.

Drives BOTH workflows against real Gemini, with the custom
``ParallelWorkflowAdapter`` powering the parallel fan-out / fan-in in each:

  ── Stage 1 · Diagnosis ──────────────────────────────────────────────
  TicketBot (seeds incident) → Intake (dedup) → Triage (fans out) →
    {Network, Storage, Web specialists in parallel} → RCA → Remediation
  The Remediation agent posts recommendations; the workflow closes with
  reason ``remediation_recommended`` and the ticket is updated with the
  RCA + recommended fixes.

  ── Stage 2 · Remediation ────────────────────────────────────────────
  A NEW workflow is spawned for the Remediation_Recommended ticket:
  RemBot (seeds the ticket) → RemTriage (fans out fixers) →
    {Infra, Storage, Config fixers + a Human operator, all in parallel}
    → Resolver → close
  The technical fixers apply the recommended changes autonomously while
  the Human operator signs off on the disruptive step (the "human as a
  parallel participant" HITL model). The join — and therefore the
  Resolver — only fires once every fixer has submitted AND the operator
  has responded; the unblocked fixers keep working while the operator is
  pending. The Resolver writes up the resolution and sets the final
  ticket status.

Each LLM-driven agent uses ``GeminiConfig`` with ``gemini-3.5-flash``.
API keys are loaded from ``.env`` via ``python-dotenv``.

Quickstart (from the repo root, `itops/`):

    uv sync                       # creates .venv with ag2 (git main) + deps

    # Put your key in itops/.env:
    #   GEMINI_API_KEY=your-real-key-here

    cd orchestration
    ../.venv/bin/python run_demo.py                          # full two-stage pipeline (web_5xx)
    ../.venv/bin/python run_demo.py --incident storage_io_error  # dedup short-circuit (stage 1 only)

The script prints every envelope flowing through both channels so you can
watch the parallel bands fire, the diagnosis hand off to remediation, and
the operator gate the close.

NOTE ON THE HITL NARRATIVE: the frontend mockup depicts the escalation as
originating from the Storage *fixer* mid-work. The runnable proof instead
has RemTriage route the operator into the parallel band up front (policy:
remediation requires human sign-off), because *adding* a participant to an
already-active pending set would require an adapter change. The observable
behaviour is identical: the human is a concurrent pending speaker, the
autonomous fixers proceed without waiting, and the join blocks on the human.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from autogen.beta import Agent, tool
from autogen.beta.config import GeminiConfig
from autogen.beta.knowledge import MemoryKnowledgeStore
from autogen.beta.network import (
    EV_CHANNEL_CLOSED,
    EV_PACKET,
    EV_TEXT,
    AgentTarget,
    BaseHubListener,
    FromSpeaker,
    Hub,
    HubClient,
    LocalLink,
    Passport,
    Resume,
    TerminateTarget,
    ToolCalled,
    Transition,
    TransitionGraph,
)
from dotenv import load_dotenv
from mock_world import (
    incident as get_incident,
)
from mock_world import (
    incident_keys,
    tool_response,
)
from parallel_workflow import (
    PARALLEL_WORKFLOW_TYPE,
    DynamicParallelTarget,
    ParallelWorkflowAdapter,
)

# ─── Bootstrap ──────────────────────────────────────────────────────────

# Load environment variables. Look in three sensible places so this
# works whether the user runs from the script's directory, from the
# AG2 repo root, or with a custom .env path via the DOTENV_PATH env var.
_DOTENV_CANDIDATES = [
    Path(os.environ["DOTENV_PATH"]) if "DOTENV_PATH" in os.environ else None,
    Path(__file__).parent / ".env",
    Path.cwd() / ".env",
    Path(__file__).parent.parent / ".env",  # repo-root fallback
]
_loaded_from: Path | None = None
for candidate in _DOTENV_CANDIDATES:
    if candidate is not None and candidate.is_file():
        load_dotenv(candidate, override=False)
        _loaded_from = _loaded_from or candidate
# Also do an unscoped pass (python-dotenv walks up from cwd) so anything
# we haven't already covered still gets picked up.
load_dotenv(override=False)

if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
    checked = "\n".join(f"  - {c}" for c in _DOTENV_CANDIDATES if c is not None)
    print(
        "ERROR: no Gemini API key found in env.\n"
        "Set GEMINI_API_KEY (or GOOGLE_API_KEY) either by exporting it\n"
        "in your shell, or by creating a .env file at one of:\n"
        f"{checked}\n"
        "with the contents:\n"
        "    GEMINI_API_KEY=your-key-here\n",
        file=sys.stderr,
    )
    sys.exit(2)

if _loaded_from is not None:
    print(f"(loaded environment from {_loaded_from})", file=sys.stderr)


# Single shared model config. Per-agent overrides can flip temperature
# etc. if needed; defaults are fine for a triage workflow.
GEMINI = GeminiConfig(model="gemini-3.5-flash")


# ─── Persisted ticket store (real application state, file-backed) ───────
#
# Tickets are real, persisted records — one JSON file per ticket under
# TICKETS_DIR. The store supports create / get / update / list and a REAL
# duplicate lookup against actual tickets (no faked history). The WAL stays
# the source of truth for the *workflow*; the ticket is the durable record the
# orchestration creates and updates in response to workflow outcomes.

TICKETS_DIR = Path(__file__).parent / "tickets"

# The active store, set by run_diagnosis so the list_recent_tickets tool can
# query real tickets for dedup. (One shared store per process — server or CLI.)
_STORE: TicketStore | None = None


@dataclass
class Ticket:
    id: str
    system: str
    issue: str
    sev: str
    status: str = "New"
    rca: str = ""
    confidence: str = ""
    recommendations: list[str] = field(default_factory=list)
    parent: str | None = None
    resolution: str = ""
    history: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    needs_human: bool = False  # set while a human sign-off is pending
    human_prompt: str = ""  # what the human is being asked

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Ticket:
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in d.items() if k in known})


class TicketStore:
    """File-backed ticket store — one ``INC-NNN.json`` per ticket in
    ``TICKETS_DIR``. Persists across restarts."""

    def __init__(self, dir_path: Path = TICKETS_DIR) -> None:
        self.dir = Path(dir_path)
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, ticket_id: str) -> Path:
        return self.dir / f"{ticket_id}.json"

    def _write(self, t: Ticket) -> Ticket:
        self._path(t.id).write_text(json.dumps(t.to_dict(), indent=2))
        return t

    def new_id(self) -> str:
        nums = []
        for p in self.dir.glob("INC-*.json"):
            try:
                nums.append(int(p.stem.split("-")[1]))
            except (IndexError, ValueError):
                pass
        return f"INC-{(max(nums) + 1) if nums else 7:03d}"

    def create(self, ticket: Ticket) -> Ticket:
        if not ticket.history:
            ticket.history.append(f"created · {ticket.status}")
        return self._write(ticket)

    def get(self, ticket_id: str) -> Ticket | None:
        p = self._path(ticket_id)
        if not p.exists():
            return None
        return Ticket.from_dict(json.loads(p.read_text()))

    def update(self, ticket_id: str, **changes) -> Ticket | None:
        t = self.get(ticket_id)
        if t is None:
            return None
        for key, value in changes.items():
            setattr(t, key, value)
        return self._write(t)

    def set_status(self, ticket_id: str, status: str, note: str = "") -> Ticket | None:
        t = self.get(ticket_id)
        if t is None:
            return None
        t.status = status
        t.history.append(status + (f" · {note}" if note else ""))
        return self._write(t)

    def set_needs_human(self, ticket_id: str, needs: bool, prompt: str = "") -> Ticket | None:
        t = self.get(ticket_id)
        if t is None:
            return None
        t.needs_human = needs
        t.human_prompt = prompt if needs else ""
        return self._write(t)

    def all(self) -> list[Ticket]:
        out = []
        for p in self.dir.glob("INC-*.json"):
            try:
                out.append(Ticket.from_dict(json.loads(p.read_text())))
            except Exception:
                pass
        return sorted(out, key=lambda t: t.created_at)

    def matching(self, system: str, issue: str, lookback_minutes: int) -> list[Ticket]:
        """REAL duplicate lookup: non-duplicate tickets for the same system +
        issue created within the lookback window, oldest first."""
        now = time.time()
        return [
            t
            for t in self.all()
            if t.system == system
            and t.issue == issue
            and t.status != "Duplicate"
            and (now - t.created_at) <= lookback_minutes * 60
        ]

    def clear(self) -> None:
        for p in self.dir.glob("INC-*.json"):
            try:
                p.unlink()
            except OSError:
                pass


# ─── Stage 1 · Diagnosis ────────────────────────────────────────────────
#
# All tools are ``@tool``-decorated async functions. Routing tools
# (``proceed_to_triage``, ``mark_as_duplicate``, ``assign_specialists``,
# ``submit_findings``, ``submit_rca``, ``post_recommendations``) trigger
# graph transitions via the ``ToolCalled`` rules below. Investigative
# tools (``ping_host``, ``get_disk_status``, etc.) are non-routing —
# specialists call them to gather evidence before submitting findings.


# ── Intake (L0) tools ──


@tool
async def list_recent_tickets(system: str, issue_type: str, lookback_minutes: int = 15) -> str:
    """REQUIRED FIRST STEP for the Intake Agent. Returns recent tickets
    matching this system + issue_type opened in the last N minutes,
    including their resolution status and any findings/recommendations.

    The Intake Agent MUST call this before making any routing decision —
    it is the ONLY source of truth for whether a recent duplicate exists.
    Returning "No recent matches." is a valid and common result; that
    itself is the evidence Intake needs to call proceed_to_triage."""
    # REAL dedup against the persisted ticket store. The current incident's own
    # ticket is the newest match (it was just created), so a duplicate exists
    # only if there is also an EARLIER ticket for the same system + issue type.
    if _STORE is not None:
        matches = _STORE.matching(system, issue_type, lookback_minutes)
        if len(matches) >= 2:
            parent = matches[0]  # the original (oldest) occurrence
            age_min = max(0, int((time.time() - parent.created_at) / 60))
            extra = ""
            if parent.rca:
                extra += f", root_cause='{parent.rca}'"
            if parent.recommendations:
                extra += f", recommendations={parent.recommendations}"
            return (
                f"Found 1 recent ticket: {parent.id} opened ~{age_min} min ago — "
                f"{parent.issue} on {parent.system}, status={parent.status}{extra}. "
                f"Same system and issue type as the current incident."
            )
    return "No recent matches."


@tool
async def proceed_to_triage(reason: str) -> str:
    """Confirm this is not a duplicate; hand off to Triage."""
    return f"Proceeded to triage: {reason}"


@tool
async def mark_as_duplicate(parent_ticket_id: str, reason: str) -> str:
    """Mark this ticket as a duplicate of an existing resolved ticket.
    The workflow terminates immediately; the new ticket inherits the
    parent's findings, RCA and recommendations."""
    return f"Marked as duplicate of {parent_ticket_id}: {reason}"


# ── Triage (L1) tool ──


@tool
async def assign_specialists(specialists: list[str], reason: str) -> str:
    """Dispatch the ticket to the listed specialists. ``specialists``
    must contain 1–3 of ``"network"``, ``"storage"``, ``"web"``. All
    listed specialists will investigate concurrently, then RCA will
    synthesise their findings."""
    return f"Assigned to {specialists}: {reason}"


# ── Specialist (L2) investigative tools ──


@tool
async def ping_host(host: str) -> str:
    """Network specialist: ICMP ping a host."""
    return tool_response("ping_host", host)


@tool
async def check_dns(host: str) -> str:
    """Network specialist: forward DNS lookup."""
    return tool_response("check_dns", host)


@tool
async def get_network_routes(host: str) -> str:
    """Network specialist: show routing table to a host."""
    return tool_response("get_network_routes", host)


@tool
async def get_disk_status(host: str) -> str:
    """Storage specialist: list disk health on a host."""
    return tool_response("get_disk_status", host)


@tool
async def get_pool_health(pool: str) -> str:
    """Storage specialist: ZFS pool status."""
    return tool_response("get_pool_health", pool)


@tool
async def get_smart_data(disk: str) -> str:
    """Storage specialist: SMART attributes for a disk."""
    return tool_response("get_smart_data", disk)


@tool
async def get_recent_5xx(host: str) -> str:
    """Web specialist: count of 5xx responses in last 5 min."""
    return tool_response("get_recent_5xx", host)


@tool
async def get_upstream_latency(host: str) -> str:
    """Web specialist: upstream latency to backing services."""
    return tool_response("get_upstream_latency", host)


@tool
async def get_active_connections(host: str) -> str:
    """Web specialist: active connection count."""
    return tool_response("get_active_connections", host)


@tool
async def submit_findings(summary: str, evidence: str) -> str:
    """Each specialist submits its independent findings after
    investigation. Once all assigned specialists have called this,
    the workflow joins to RCA."""
    return f"Findings recorded: {summary}"


# ── RCA (L3) tool ──


@tool
async def submit_rca(root_cause: str, confidence: str) -> str:
    """Submit the synthesised root cause analysis. ``confidence`` is
    one of ``"low"``, ``"medium"``, ``"high"``."""
    return f"RCA recorded ({confidence}): {root_cause}"


# ── Remediation (L4) tool — recommends, does not apply ──


@tool
async def post_recommendations(steps: list[str]) -> str:
    """Post 3–5 concrete remediation steps to the ticket. This closes the
    diagnosis workflow and moves the ticket to Remediation_Recommended —
    a separate remediation workflow will apply these steps."""
    return f"Posted {len(steps)} recommendation step(s)."


# ─── Stage 2 · Remediation ──────────────────────────────────────────────
#
# A new set of fixer roles that ACT on the recommendations (rather than
# investigate). Each has domain action tools plus the shared routing tool
# ``submit_fix``. ``assign_fixers`` fans out (DynamicParallelTarget); the
# Resolver's ``close_ticket`` terminates.


# ── RemTriage tool ──


@tool
async def assign_fixers(fixers: list[str], reason: str) -> str:
    """Dispatch the remediation to a set of fixers, who work concurrently.
    Valid fixers: ``"infra"`` (failover/restart), ``"storage"`` (pools,
    disks), ``"config"`` (nginx/app config), and ``"human"`` (an operator
    who signs off on disruptive or irreversible actions). Per change
    policy you MUST include ``"human"`` for sign-off on any remediation
    that has a disruptive step."""
    return f"Assigned fixers {fixers}: {reason}"


# ── Infra fixer tools ──


@tool
async def failover_to_standby(node: str) -> str:
    """Infra fixer: shift traffic from a node to its standby."""
    return f"{node}: traffic drained to {node}-standby; primary now idle. OK."


@tool
async def restart_service(service: str, host: str) -> str:
    """Infra fixer: restart a service on a host."""
    return f"{service} on {host}: restarted, health check green."


# ── Storage fixer tools ──


@tool
async def start_pool_scrub(pool: str) -> str:
    """Storage fixer: start a scrub/repair on a ZFS pool."""
    return f"pool {pool}: scrub started, repairing 14 errors, ETA ~12m."


@tool
async def prepare_disk_replacement(slot: str) -> str:
    """Storage fixer: stage a failing disk for replacement. The physical
    hot-swap is DISRUPTIVE and requires operator sign-off before it runs."""
    return (
        f"slot {slot}: failing disk staged for hot-swap; "
        "AWAITING OPERATOR APPROVAL before pulling the disk."
    )


# ── Config fixer tools ──


@tool
async def set_upstream_timeout(seconds: int) -> str:
    """Config fixer: adjust the nginx upstream timeout and reload."""
    return f"nginx upstream timeout set to {seconds}s; config reloaded, no errors."


@tool
async def add_health_check(target: str) -> str:
    """Config fixer: add an upstream health check."""
    return f"health check added for {target}; unhealthy upstreams will be ejected."


# ── Shared fixer routing tool ──


@tool
async def submit_fix(summary: str, status: str) -> str:
    """Each fixer submits the outcome of its work. ``status`` is one of
    ``"applied"`` (done), ``"partial"`` (some steps pending), or
    ``"blocked_pending_approval"``. Once every assigned fixer has called
    this AND the operator has signed off, the workflow joins to the
    Resolver."""
    return f"Fix recorded ({status}): {summary}"


# ── Resolver tool ──


@tool
async def close_ticket(status: str, summary: str) -> str:
    """Resolver: write the final resolution to the ticket and set its
    status. ``status`` is one of ``"resolved"`` (fully remediated),
    ``"partially_resolved"``, or ``"needs_followup"``. This closes the
    remediation workflow."""
    return f"Ticket closed ({status}): {summary}"


# ─── Agent prompts ──────────────────────────────────────────────────────

INTAKE_LOOKUP_PROMPT = """\
You are the L0 Intake Lookup agent. You have exactly ONE job and ONE
tool, and the graph will not advance until you do it.

Your job: extract the `system` and `issue_type` from the incoming
ticket and call `list_recent_tickets(system=..., issue_type=...)`
exactly once. Pass the values EXACTLY as they appear in the ticket —
do not paraphrase them, do not guess.

After the tool returns, write a single brief sentence summarising
what was returned. Do NOT make any routing decision yourself — the
next agent (Intake Decider) handles that based on what you found.

Available tools: list_recent_tickets (REQUIRED, call it once).
"""


INTAKE_DECIDE_PROMPT = """\
You are the L0 Intake Decider. The previous agent (Intake Lookup)
just queried `list_recent_tickets` for you — its result is in the
transcript above. Read that result first.

Now call EXACTLY ONE of these two routing tools:

  • mark_as_duplicate(parent_ticket_id, reason) — if the lookup
    returned a recent ticket for the SAME system and SAME issue type
    opened within the last 15 minutes. It does NOT matter whether that
    parent is already resolved or still being worked — the same incident
    reported again is a duplicate either way; the new ticket inherits the
    parent's investigation/outcome rather than redundantly re-running it.
    Use the parent_ticket_id reported by the lookup.

  • proceed_to_triage(reason) — in every other case, including when
    the lookup returned "No recent matches." (the common outcome).

Be conservative on dedup — when in doubt, proceed to triage. False
duplicates are worse than redundant investigations.

Available tools: mark_as_duplicate, proceed_to_triage.
"""

TRIAGE_PROMPT = """\
You are the L1 Triage Coordinator. You receive a ticket that Intake
has confirmed is NOT a duplicate, and you must decide which
specialists should investigate.

Available specialists:
  - "network" — routing, DNS, connectivity
  - "storage" — disks, ZFS pools, SMART data
  - "web"     — HTTP 5xx, upstream latency, connection counts

Choose ALL specialists who might plausibly hold a piece of the answer.
Many incidents implicate more than one domain — for example, a 5xx
burst on a web server might be caused by a failing storage backend,
in which case BOTH "web" and "storage" should investigate.

Call exactly one tool: assign_specialists(specialists=[...], reason=...)
with a list of 1–3 specialists and a one-sentence rationale.
"""

NETWORK_PROMPT = """\
You are the Network Specialist. Triage assigned you to investigate
the network angle of this ticket.

Use your tools — ping_host, check_dns, get_network_routes — to gather
evidence. Call at least one investigative tool before reporting.

Once you have enough evidence, call submit_findings(summary, evidence)
with:
  - summary: under 50 words, what you found
  - evidence: brief list of the tool outputs that support your summary

You may be running in parallel with other specialists. Do NOT wait
for them or reference their findings — focus only on your own domain.
"""

STORAGE_PROMPT = """\
You are the Storage Specialist. Triage assigned you to investigate
the storage angle of this ticket.

Use your tools — get_disk_status, get_pool_health, get_smart_data —
to gather evidence. Call at least one investigative tool before
reporting.

Once you have enough evidence, call submit_findings(summary, evidence)
with:
  - summary: under 50 words, what you found
  - evidence: brief list of the tool outputs that support your summary

You may be running in parallel with other specialists. Do NOT wait
for them or reference their findings.
"""

WEB_PROMPT = """\
You are the Web Specialist. Triage assigned you to investigate the
web/HTTP angle of this ticket.

Use your tools — get_recent_5xx, get_upstream_latency,
get_active_connections — to gather evidence. Call at least one
investigative tool before reporting.

Once you have enough evidence, call submit_findings(summary, evidence)
with:
  - summary: under 50 words, what you found
  - evidence: brief list of the tool outputs that support your summary

You may be running in parallel with other specialists. Do NOT wait
for them or reference their findings.
"""

RCA_PROMPT = """\
You are the Root Cause Analyst. You will see the findings from one
or more specialists (Network, Storage, and/or Web) who investigated
the same ticket in parallel.

Read all of their findings together. Identify the most likely root
cause in 2–3 sentences. If the specialists' findings disagree, or if
one specialist's findings rule out a hypothesis the others raised,
say so explicitly.

Call submit_rca(root_cause, confidence) where confidence is one of
"low", "medium", or "high".
"""

REMEDIATION_PROMPT = """\
You are the Remediation Advisor. Given the root cause analysis from
the RCA agent, propose 3–5 concrete remediation steps that an on-call
engineer can execute.

Steps must be SPECIFIC — actual commands, actual config changes,
actual escalations to actual teams. Avoid generic advice like
"investigate further" or "monitor the system". At least one step will
typically be disruptive (a failover, restart, disk replacement, or
deploy rollback) — include it; the remediation workflow will obtain
sign-off for it.

Call post_recommendations(steps=[...]) with a list of strings.
"""

# ── Stage 2 prompts ──

REMTRIAGE_PROMPT = """\
You are the Remediation Triage Coordinator. You receive a ticket that
already has an RCA and a list of recommended remediation steps. Your
job is to dispatch the right fixers to APPLY those steps concurrently.

Available fixers:
  - "infra"   — failover to standby, restart services
  - "storage" — ZFS pool scrub/repair, stage failing disks for replacement
  - "config"  — nginx/app config (timeouts, health checks)
  - "human"   — an on-call OPERATOR who signs off on disruptive or
                irreversible actions (failover, disk hot-swap, restart,
                deploy rollback)

Pick every technical fixer whose domain matches a recommended step.
Per change-management policy you MUST ALSO include "human" so the
operator signs off on the disruptive step(s) — the fixers proceed in
parallel while the operator reviews.

Call exactly one tool: assign_fixers(fixers=[...], reason=...) with the
list of fixers (always including "human") and a one-sentence rationale.
"""

INFRA_FIX_PROMPT = """\
You are the Infra Fixer. RemTriage assigned you to apply the
infrastructure-related remediation steps (failover, service restarts).

Use your tools — failover_to_standby, restart_service — to apply the
relevant steps from the ticket's recommendations. Call at least one
action tool before reporting.

Then call submit_fix(summary, status) where status is "applied" (done),
"partial", or "blocked_pending_approval". You run in parallel with the
other fixers and the operator — do NOT wait for them.
"""

STORAGE_FIX_PROMPT = """\
You are the Storage Fixer. RemTriage assigned you to apply the
storage-related remediation steps.

Use your tools — start_pool_scrub (safe, do it now) and
prepare_disk_replacement (DISRUPTIVE — stages the disk but the physical
hot-swap needs the operator's sign-off). Apply what you safely can now.

Then call submit_fix(summary, status). If the disk hot-swap is staged
but not yet executed, use status="partial" and say it is awaiting
operator approval. You run in parallel with the other fixers and the
operator — do NOT wait for them.
"""

CONFIG_FIX_PROMPT = """\
You are the Config Fixer. RemTriage assigned you to apply the
configuration-related remediation steps (nginx timeouts, health checks).

Use your tools — set_upstream_timeout, add_health_check — to apply the
relevant steps. Call at least one action tool before reporting.

Then call submit_fix(summary, status), typically status="applied". You
run in parallel with the other fixers and the operator — do NOT wait.
"""

RESOLVER_PROMPT = """\
You are the Resolver. Every fixer has submitted its outcome and the human
reviewer has responded to the sign-off request — find their "Human sign-off:"
message in the transcript above (it will say APPROVED, DEFERRED, or REJECTED).

Prepare the ticket's resolution: a concise summary of what each fixer did and
how the human responded, in 2–4 sentences. Then set the ticket's final status
by calling close_ticket(status, summary), choosing based on the human's
decision AND the fixers' outcomes:
  - "resolved" — the human APPROVED and every recommended step (including the
    disruptive one) was applied; the incident is addressed.
  - "partially_resolved" — the human APPROVED or DEFERRED but some steps
    remain (e.g. the disruptive step is deferred to a maintenance window while
    the non-disruptive fixes are already in place), or a fixer left work pending.
  - "needs_followup" — the human REJECTED the recommended remediation, OR a
    fixer reported it could not complete. The disruptive step was NOT applied;
    only the non-disruptive fixes (if any) stand, and the incident needs a
    human-led follow-up plan.

Call close_ticket(status, summary) exactly once.
"""


# ─── Listener — prints live activity to the console ────────────────────


class _ConsolePrinter(BaseHubListener):
    """Emit a one-line summary of each envelope as it's accepted.

    Holds a *reference* to a shared id→name dict so names registered
    later (e.g. the stage-2 agents) resolve without re-registering the
    listener.
    """

    def __init__(self, id_to_name: dict[str, str]) -> None:
        self.id_to_name = id_to_name
        self.t0 = datetime.now(UTC)

    def _stamp(self) -> str:
        dt = datetime.now(UTC) - self.t0
        return f"[+{dt.total_seconds():6.1f}s]"

    async def on_envelope_posted(self, envelope, metadata) -> None:
        sender = self.id_to_name.get(envelope.sender_id, envelope.sender_id)
        if envelope.event_type == EV_TEXT:
            text = envelope.event_data.get("text", "")
            if len(text) > 88:
                text = text[:85] + "..."
            print(f"{self._stamp()} {sender:>12}  TEXT  {text!r}")
        elif envelope.event_type == EV_PACKET:
            routing = envelope.event_data.get("routing", {}) or {}
            kind = routing.get("kind", "?")
            tool_name = routing.get("tool")
            args = routing.get("tool_args") or {}
            body = (envelope.event_data.get("body") or "").strip().splitlines()
            body_preview = body[0] if body else ""
            if len(body_preview) > 80:
                body_preview = body_preview[:77] + "..."
            if tool_name:
                args_preview = ", ".join(f"{k}={v!r}" for k, v in args.items()) if args else ""
                if len(args_preview) > 80:
                    args_preview = args_preview[:77] + "..."
                print(f"{self._stamp()} {sender:>12}  CALL  {tool_name}({args_preview})")
                if body_preview:
                    print(f"{'':>24}      └─ body: {body_preview}")
            else:
                print(f"{self._stamp()} {sender:>12}  {kind.upper():>5}  {body_preview}")

    async def on_channel_event(self, channel_id, kind, payload) -> None:
        if kind == "closed":
            reason = payload.get("reason", "?")
            print(f"{self._stamp()} {'channel':>12}  CLOSE reason={reason!r}")


# ─── Helpers ────────────────────────────────────────────────────────────


def _wal_tool_args(wal, tool_name: str) -> dict:
    """First EV_PACKET in the WAL whose routing matched ``tool_name`` —
    return its parsed tool arguments (enriched by the adapter), or {}."""
    for env in wal:
        if env.event_type == EV_PACKET:
            routing = env.event_data.get("routing") or {}
            if routing.get("tool") == tool_name:
                return routing.get("tool_args") or {}
    return {}


def _banner(title: str, subtitle: str = "") -> None:
    print("=" * 76)
    print(f"  {title}")
    if subtitle:
        print(f"  {subtitle}")
    print("=" * 76)


# ─── Stage 1 · Diagnosis workflow ───────────────────────────────────────


async def run_diagnosis(
    hub: Hub,
    link: LocalLink,
    id_to_name: dict[str, str],
    store: TicketStore,
    incident: dict,
    *,
    emit=None,
) -> dict:
    """Drive one ticket through the diagnosis workflow end-to-end.

    ``incident`` is a ``mock_world.INCIDENTS`` entry (system / issue / sev /
    kickoff). Returns a dict with ``reason`` (the close reason) and
    ``ticket_id``. On the ``remediation_recommended`` path the ticket is
    updated with the RCA + recommendations ready for stage 2.
    """

    global _STORE
    _STORE = store  # so the list_recent_tickets tool can query real tickets

    ticket_id = store.new_id()
    # Unique per-flow suffix: every flow on the shared hub must register agents
    # under distinct Passport names, or the hub's name→id registry collides and
    # dispatch breaks for the 2nd+ concurrent/sequential flow.
    tok = uuid.uuid4().hex[:8]
    ticket = store.create(
        Ticket(
            id=ticket_id,
            system=incident["system"],
            issue=incident["issue"],
            sev=incident["sev"],
            status="Diagnosing",
        )
    )
    kickoff = incident["kickoff"].format(id=ticket_id)

    hc = {
        name: HubClient(link, hub=hub)
        for name in (
            "ticketbot",
            "intake_lookup",
            "intake_decide",
            "triage",
            "network",
            "storage",
            "web",
            "rca",
            "remediation",
        )
    }

    try:
        intake_lookup_agent = Agent(
            "IntakeLookup", prompt=INTAKE_LOOKUP_PROMPT, config=GEMINI, tools=[list_recent_tickets]
        )
        intake_decide_agent = Agent(
            "IntakeDecide",
            prompt=INTAKE_DECIDE_PROMPT,
            config=GEMINI,
            tools=[proceed_to_triage, mark_as_duplicate],
        )
        triage_agent = Agent(
            "Triage", prompt=TRIAGE_PROMPT, config=GEMINI, tools=[assign_specialists]
        )
        network_agent = Agent(
            "Network",
            prompt=NETWORK_PROMPT,
            config=GEMINI,
            tools=[ping_host, check_dns, get_network_routes, submit_findings],
        )
        storage_agent = Agent(
            "Storage",
            prompt=STORAGE_PROMPT,
            config=GEMINI,
            tools=[get_disk_status, get_pool_health, get_smart_data, submit_findings],
        )
        web_agent = Agent(
            "Web",
            prompt=WEB_PROMPT,
            config=GEMINI,
            tools=[get_recent_5xx, get_upstream_latency, get_active_connections, submit_findings],
        )
        rca_agent = Agent("RCA", prompt=RCA_PROMPT, config=GEMINI, tools=[submit_rca])
        remediation_agent = Agent(
            "Remediation", prompt=REMEDIATION_PROMPT, config=GEMINI, tools=[post_recommendations]
        )

        ticketbot = await hc["ticketbot"].register_human(
            Passport(name=f"TicketBot-{tok}", kind="human")
        )
        intake_lookup = await hc["intake_lookup"].register(
            intake_lookup_agent, Passport(name=f"IntakeLookup-{tok}"), Resume(), attach_plugin=False
        )
        intake_decide = await hc["intake_decide"].register(
            intake_decide_agent, Passport(name=f"IntakeDecide-{tok}"), Resume(), attach_plugin=False
        )
        triage = await hc["triage"].register(
            triage_agent, Passport(name=f"Triage-{tok}"), Resume(), attach_plugin=False
        )
        network = await hc["network"].register(
            network_agent, Passport(name=f"Network-{tok}"), Resume(), attach_plugin=False
        )
        storage = await hc["storage"].register(
            storage_agent, Passport(name=f"Storage-{tok}"), Resume(), attach_plugin=False
        )
        web = await hc["web"].register(
            web_agent, Passport(name=f"Web-{tok}"), Resume(), attach_plugin=False
        )
        rca = await hc["rca"].register(
            rca_agent, Passport(name=f"RCA-{tok}"), Resume(), attach_plugin=False
        )
        remediation = await hc["remediation"].register(
            remediation_agent, Passport(name=f"Remediation-{tok}"), Resume(), attach_plugin=False
        )

        id_to_name.update(
            {
                ticketbot.agent_id: "TicketBot",
                intake_lookup.agent_id: "IntakeLookup",
                intake_decide.agent_id: "IntakeDecide",
                triage.agent_id: "Triage",
                network.agent_id: "Network",
                storage.agent_id: "Storage",
                web.agent_id: "Web",
                rca.agent_id: "RCA",
                remediation.agent_id: "Remediation",
            }
        )

        graph = TransitionGraph(
            initial_speaker=ticketbot.agent_id,
            transitions=[
                Transition(
                    when=ToolCalled("list_recent_tickets"), then=AgentTarget(intake_decide.agent_id)
                ),
                Transition(when=ToolCalled("mark_as_duplicate"), then=TerminateTarget("duplicate")),
                Transition(when=ToolCalled("proceed_to_triage"), then=AgentTarget(triage.agent_id)),
                Transition(
                    when=ToolCalled("assign_specialists"),
                    then=DynamicParallelTarget(
                        from_tool_arg="specialists",
                        nickname_to_agent_id={
                            "network": network.agent_id,
                            "storage": storage.agent_id,
                            "web": web.agent_id,
                        },
                    ),
                ),
                Transition(when=ToolCalled("submit_findings"), then=AgentTarget(rca.agent_id)),
                Transition(when=ToolCalled("submit_rca"), then=AgentTarget(remediation.agent_id)),
                # Diagnosis terminates by *recommending* remediation — a
                # separate workflow applies it.
                Transition(
                    when=ToolCalled("post_recommendations"),
                    then=TerminateTarget("remediation_recommended"),
                ),
                Transition(
                    when=FromSpeaker(ticketbot.agent_id), then=AgentTarget(intake_lookup.agent_id)
                ),
            ],
            default_target=TerminateTarget("no_match"),
            max_turns=25,
        )

        channel = await ticketbot.open(
            type=PARALLEL_WORKFLOW_TYPE,
            target=[
                intake_lookup.agent_id,
                intake_decide.agent_id,
                triage.agent_id,
                network.agent_id,
                storage.agent_id,
                web.agent_id,
                rca.agent_id,
                remediation.agent_id,
            ],
            knobs={"graph": graph.to_dict()},
        )

        if emit is not None:
            emit(
                "channel_opened",
                {
                    "channel_id": channel.channel_id,
                    "ticket_id": ticket.id,
                    "stage": "diagnosis",
                },
            )

        _banner("STAGE 1 · DIAGNOSIS", f"{ticket.id} · {ticket.issue} on {ticket.system}")
        await ticketbot.send(channel.channel_id, kickoff)

        close_env = await ticketbot.next_envelope(
            predicate=lambda e: (
                e.channel_id == channel.channel_id and e.event_type == EV_CHANNEL_CLOSED
            ),
            timeout=180.0,
        )
        reason = close_env.event_data.get("reason")

        # ── Apply workflow outcome to the persisted ticket ──
        wal = await hub.read_wal(channel.channel_id)
        if reason == "duplicate":
            dup = _wal_tool_args(wal, "mark_as_duplicate")
            store.update(ticket_id, parent=dup.get("parent_ticket_id"))
            store.set_status(ticket_id, "Duplicate", f"of {dup.get('parent_ticket_id')}")
        elif reason == "remediation_recommended":
            rca_args = _wal_tool_args(wal, "submit_rca")
            rec_args = _wal_tool_args(wal, "post_recommendations")
            steps = list(rec_args.get("steps", []) or [])
            store.update(
                ticket_id,
                rca=rca_args.get("root_cause", ""),
                confidence=rca_args.get("confidence", ""),
                recommendations=steps,
            )
            store.set_status(ticket_id, "Remediation_Recommended", f"{len(steps)} step(s)")

        latest = store.get(ticket_id)
        status = latest.status if latest else "?"
        print(f"\n  Stage 1 closed: reason={reason!r} → ticket {ticket_id} is now {status}\n")
        return {"reason": reason, "ticket_id": ticket_id}

    finally:
        for client in hc.values():
            try:
                await client.close()
            except Exception:
                pass


# ─── Stage 2 · Remediation workflow ─────────────────────────────────────


async def _console_decide(ctx: dict) -> str:
    """Default operator-decision provider for the CLI: deliberate briefly
    (while the unblocked fixers keep working), then approve.

    The web service injects its own provider that surfaces the escalation
    in the UI and awaits the operator's real response. ``ctx`` carries
    ``channel_id``, ``ticket_id``, ``fixers`` and the ticket's ``rca`` /
    ``recommendations`` so a UI can render a meaningful approval prompt.
    """
    await asyncio.sleep(2.5)
    print("\n   🧑  HUMAN responds to the escalation: approving the disruptive step\n")
    return (
        "Human sign-off: APPROVED. Proceed with the recommended remediation, "
        "including the disruptive step (failover / disk hot-swap), during the "
        "current change window. Standby capacity confirmed and rollback plan "
        "acknowledged."
    )


async def _operator_respond(operator, channel_id: str, ticket: Ticket, decide) -> None:
    """Wait until RemTriage routes the 'human' into the fan-out (so the
    operator is a valid pending speaker), obtain the operator's decision
    from the injected ``decide`` provider, and post it into the channel.

    The workflow's join blocks on this post, so the channel cannot close
    until the operator responds — while the autonomous fixers proceed.
    """
    try:
        env = await operator.next_envelope(
            predicate=lambda e: (
                e.channel_id == channel_id
                and e.event_type == EV_PACKET
                and (e.event_data.get("routing") or {}).get("tool") == "assign_fixers"
            ),
            timeout=180.0,
        )
    except Exception:
        return  # never fanned out — nothing to sign off

    fixers = ((env.event_data.get("routing") or {}).get("tool_args") or {}).get("fixers") or []
    if "human" not in fixers:
        return  # operator wasn't routed in; posting now would be rejected

    ctx = {
        "channel_id": channel_id,
        "ticket_id": ticket.id,
        "fixers": fixers,
        "rca": ticket.rca,
        "recommendations": list(ticket.recommendations),
    }
    try:
        decision = await decide(ctx)
    except Exception as exc:
        print(f"   (operator decide failed: {exc})")
        return
    if not decision:
        return  # operator declined / timed out
    try:
        await operator.send(channel_id, decision)
    except Exception as exc:
        print(f"   (operator send failed: {exc})")


async def run_remediation(
    hub: Hub,
    link: LocalLink,
    id_to_name: dict[str, str],
    store: TicketStore,
    ticket_id: str,
    *,
    decide=_console_decide,
    emit=None,
) -> dict:
    """Spawn and drive the remediation workflow for one
    Remediation_Recommended ticket. Returns {'reason', 'status'}.

    ``decide`` is the operator-decision provider (defaults to the CLI's
    auto-approve; the web service injects a UI-backed one). ``emit`` is an
    optional ``emit(kind, data)`` sink for domain events.
    """

    ticket = store.get(ticket_id)
    if ticket is None:
        raise ValueError(f"run_remediation: ticket {ticket_id!r} not found")
    tok = uuid.uuid4().hex[:8]  # unique per-flow suffix (see run_diagnosis)

    hc = {
        name: HubClient(link, hub=hub)
        for name in (
            "rembot",
            "operator",
            "remtriage",
            "infra",
            "storage",
            "config",
            "resolver",
        )
    }

    operator_task: asyncio.Task | None = None
    try:
        remtriage_agent = Agent(
            "RemTriage", prompt=REMTRIAGE_PROMPT, config=GEMINI, tools=[assign_fixers]
        )
        infra_agent = Agent(
            "Infra",
            prompt=INFRA_FIX_PROMPT,
            config=GEMINI,
            tools=[failover_to_standby, restart_service, submit_fix],
        )
        storage_agent = Agent(
            "StorageFix",
            prompt=STORAGE_FIX_PROMPT,
            config=GEMINI,
            tools=[start_pool_scrub, prepare_disk_replacement, submit_fix],
        )
        config_agent = Agent(
            "ConfigFix",
            prompt=CONFIG_FIX_PROMPT,
            config=GEMINI,
            tools=[set_upstream_timeout, add_health_check, submit_fix],
        )
        resolver_agent = Agent(
            "Resolver", prompt=RESOLVER_PROMPT, config=GEMINI, tools=[close_ticket]
        )

        rembot = await hc["rembot"].register_human(Passport(name=f"RemBot-{tok}", kind="human"))
        operator = await hc["operator"].register_human(
            Passport(name=f"Operator-{tok}", kind="human")
        )
        remtriage = await hc["remtriage"].register(
            remtriage_agent, Passport(name=f"RemTriage-{tok}"), Resume(), attach_plugin=False
        )
        infra = await hc["infra"].register(
            infra_agent, Passport(name=f"Infra-{tok}"), Resume(), attach_plugin=False
        )
        storage = await hc["storage"].register(
            storage_agent, Passport(name=f"StorageFix-{tok}"), Resume(), attach_plugin=False
        )
        config = await hc["config"].register(
            config_agent, Passport(name=f"ConfigFix-{tok}"), Resume(), attach_plugin=False
        )
        resolver = await hc["resolver"].register(
            resolver_agent, Passport(name=f"Resolver-{tok}"), Resume(), attach_plugin=False
        )

        id_to_name.update(
            {
                rembot.agent_id: "RemBot",
                operator.agent_id: "Human",
                remtriage.agent_id: "RemTriage",
                infra.agent_id: "Infra",
                storage.agent_id: "StorageFix",
                config.agent_id: "ConfigFix",
                resolver.agent_id: "Resolver",
            }
        )

        graph = TransitionGraph(
            initial_speaker=rembot.agent_id,
            transitions=[
                # Kickoff → RemTriage
                Transition(when=FromSpeaker(rembot.agent_id), then=AgentTarget(remtriage.agent_id)),
                # RemTriage fans out fixers + the human operator, in parallel
                Transition(
                    when=ToolCalled("assign_fixers"),
                    then=DynamicParallelTarget(
                        from_tool_arg="fixers",
                        nickname_to_agent_id={
                            "infra": infra.agent_id,
                            "storage": storage.agent_id,
                            "config": config.agent_id,
                            "human": operator.agent_id,
                        },
                    ),
                ),
                # Join → Resolver. The last pending speaker to post triggers
                # the join: it is either a fixer (submit_fix) or the operator
                # (a plain text sign-off) — cover both so order doesn't matter.
                Transition(when=ToolCalled("submit_fix"), then=AgentTarget(resolver.agent_id)),
                Transition(
                    when=FromSpeaker(operator.agent_id), then=AgentTarget(resolver.agent_id)
                ),
                # Resolver closes the ticket
                Transition(when=ToolCalled("close_ticket"), then=TerminateTarget("resolved")),
            ],
            default_target=TerminateTarget("no_match"),
            max_turns=30,
        )

        channel = await rembot.open(
            type=PARALLEL_WORKFLOW_TYPE,
            target=[
                remtriage.agent_id,
                infra.agent_id,
                storage.agent_id,
                config.agent_id,
                operator.agent_id,
                resolver.agent_id,
            ],
            knobs={"graph": graph.to_dict()},
        )
        if emit is not None:
            emit(
                "channel_opened",
                {
                    "channel_id": channel.channel_id,
                    "ticket_id": ticket.id,
                    "stage": "remediation",
                },
            )
        store.set_status(ticket_id, "Remediating", "stage-2 workflow spawned")

        recs = "\n".join(f"  - {s}" for s in ticket.recommendations) or "  (none recorded)"
        kickoff = (
            f"{ticket.id} ({ticket.sev}): {ticket.issue} on {ticket.system}.\n"
            f"RCA: {ticket.rca} (confidence={ticket.confidence}).\n"
            f"Recommended remediation steps:\n{recs}\n"
            "Apply these steps. Disruptive/irreversible steps require operator sign-off."
        )

        _banner("STAGE 2 · REMEDIATION", f"{ticket.id} · spawned from Remediation_Recommended")
        await rembot.send(channel.channel_id, kickoff)

        # The operator runs concurrently with the autonomous fixers.
        operator_task = asyncio.create_task(
            _operator_respond(operator, channel.channel_id, ticket, decide)
        )

        close_env = await rembot.next_envelope(
            predicate=lambda e: (
                e.channel_id == channel.channel_id and e.event_type == EV_CHANNEL_CLOSED
            ),
            timeout=240.0,
        )
        reason = close_env.event_data.get("reason")

        # ── Apply outcome to the persisted ticket ──
        wal = await hub.read_wal(channel.channel_id)
        close_args = _wal_tool_args(wal, "close_ticket")
        final_status = close_args.get("status") or "resolved"
        # Normalise e.g. "partially_resolved" → "Partially Resolved"
        nice_status = final_status.replace("_", " ").title()
        store.update(ticket_id, resolution=close_args.get("summary", ""))
        store.set_status(ticket_id, nice_status, "stage-2 complete")

        print(f"\n  Stage 2 closed: reason={reason!r} → ticket {ticket_id} is now {nice_status}\n")
        return {"reason": reason, "status": nice_status}

    finally:
        if operator_task is not None and not operator_task.done():
            operator_task.cancel()
            try:
                await operator_task
            except (asyncio.CancelledError, Exception):
                pass
        for client in hc.values():
            try:
                await client.close()
            except Exception:
                pass


# ─── Ticket lifecycle summary ───────────────────────────────────────────


def print_ticket_summary(store: TicketStore) -> None:
    _banner("TICKET LIFECYCLE")
    for ticket in store.all():
        print(f"  {ticket.id}  [{ticket.sev}]  {ticket.issue} on {ticket.system}")
        print(f"      status:  {ticket.status}")
        if ticket.parent:
            print(f"      parent:  {ticket.parent} (duplicate)")
        if ticket.rca:
            print(f"      RCA:     {ticket.rca}  (confidence={ticket.confidence})")
        if ticket.recommendations:
            print("      recommended remediation:")
            for step in ticket.recommendations:
                print(f"        - {step}")
        if ticket.resolution:
            print(f"      resolution: {ticket.resolution}")
        print(f"      history: {'  →  '.join(ticket.history)}")
        print()


# ─── Main ──────────────────────────────────────────────────────────────


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the IT-ops triage + remediation pipeline against real Gemini.",
    )
    parser.add_argument(
        "--incident",
        choices=incident_keys(),
        default=incident_keys()[0],
        help=(
            "Which incident from mock_world.INCIDENTS to inject. Either one runs "
            "the full TWO-stage pipeline on a fresh ticket — diagnosis (Intake → "
            "Triage → parallel specialists → RCA → recommended remediation) hands "
            "off to a remediation workflow (parallel fixers + a human operator "
            "sign-off → Resolver → resolved). Run the SAME incident again within "
            "15 minutes and Intake detects it as a real duplicate of the prior "
            "ticket (querying the persisted ticket store) and terminates early."
        ),
    )
    args = parser.parse_args()

    hub = await Hub.open(
        MemoryKnowledgeStore(),
        ttl_sweep_interval=0,
        expectation_sweep_interval=0,
    )
    # Structural ChannelAdapter; ag2's generic params are contravariant.
    hub.register_adapter(ParallelWorkflowAdapter())  # type: ignore[arg-type]
    link = LocalLink(hub)

    # Shared id→name map (the listener holds a reference; both stages add
    # their agents to it) and a shared ticket store.
    id_to_name: dict[str, str] = {}
    store = TicketStore()
    hub.register_listener(_ConsolePrinter(id_to_name))

    try:
        diagnosis = await run_diagnosis(hub, link, id_to_name, store, get_incident(args.incident))

        if diagnosis["reason"] == "remediation_recommended":
            await run_remediation(hub, link, id_to_name, store, diagnosis["ticket_id"])
        elif diagnosis["reason"] == "duplicate":
            print("  Diagnosis short-circuited as a duplicate — no remediation workflow spawned.\n")

        print_ticket_summary(store)

    finally:
        await hub.close()


if __name__ == "__main__":
    asyncio.run(main())
