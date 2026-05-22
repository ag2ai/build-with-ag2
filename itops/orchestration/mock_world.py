"""Mock "world" data for the IT-Ops demo — the ONLY mock data in the system.

Everything else (tickets, agent activity, evidence, RCA, recommendations,
HITL, resolutions) is produced LIVE by the agents / orchestration. This module
holds the simulation inputs:

* ``SYSTEMS``        — the monitored nodes (name, kind, status).
* ``AMBIENT_LOGS``   — healthy, non-error background log lines per system
                       (the monitoring stream's ambient noise).
* ``TOOL_RESPONSES`` — the canned results the agents' investigative tools
                       return when they probe a system (keyed by tool + host).
* ``RECENT_TICKETS`` — recent-ticket history Intake dedups against.
* ``INCIDENTS``      — the catalog of injectable incidents (system, issue,
                       severity, the *error* log lines, and the seed prompt).

Backend tools read ``tool_response`` / ``find_recent_ticket``; ``run_demo``
seeds a workflow from an ``INCIDENTS`` entry; the web service serves
``SYSTEMS`` / ``AMBIENT_LOGS`` / ``INCIDENTS`` to the frontend via ``GET /world``.
"""

from __future__ import annotations

# ─── Systems / nodes ────────────────────────────────────────────────────

SYSTEMS = [
    {"id": "web-edge-01", "kind": "web · nginx", "status": "degraded"},
    {"id": "storage-node-04", "kind": "storage · zfs", "status": "degraded"},
    {"id": "api-gateway-02", "kind": "api · envoy", "status": "healthy"},
    {"id": "db-primary-01", "kind": "db · postgres", "status": "healthy"},
]


# ─── Ambient (non-error) log lines per system ───────────────────────────
# The frontend log stream samples these for healthy background noise. Error
# lines are NOT here — they come from the injected incident (see INCIDENTS).

AMBIENT_LOGS = {
    "web-edge-01": [
        "GET /api/v1/orders 200 134ms",
        "GET /api/v1/cart 200 89ms",
        "GET /static/main.css 200 11ms",
        "POST /api/v1/login 200 76ms",
        "GET /healthz 200 2ms",
        "GET /api/v1/products 200 58ms",
    ],
    "storage-node-04": [
        "zfs[884]: pool tank scrub in progress",
        "snapshot tank@auto-hourly created",
        "arc: hit ratio 98.7%",
        "zpool status: pool tank online",
        "nfsd: 0 pending requests",
    ],
    "api-gateway-02": [
        "upstream orders-svc 200 21ms",
        "rate-limit: 0 rejections in last 60s",
        "GET /metrics 200 4ms",
        "health check: all upstreams healthy",
    ],
    "db-primary-01": [
        "SELECT ... 200 3ms",
        "checkpoint complete: wrote 124 buffers",
        "autovacuum: analyzing public.orders",
        "replication lag: 12ms",
    ],
}


# ─── Canned investigative-tool results ──────────────────────────────────
# Keyed by tool name, then by the primary argument (host / pool / disk).
# ``_default`` applies to anything not explicitly listed. ``{arg}`` in a
# template is replaced with the call's argument.

TOOL_RESPONSES = {
    "ping_host": {
        "_default": "{arg}: 4/4 packets received, avg 0.8ms, no loss.",
    },
    "check_dns": {
        "_default": "{arg}: A record resolves to 10.0.4.12 (TTL 300).",
    },
    "get_network_routes": {
        "_default": "{arg}: route via 10.0.0.1 dev eth0 metric 100; reachable.",
    },
    "get_disk_status": {
        "storage-node-04": "{arg}: 3 disks online, 1 disk OFFLINE (slot 2, serial WD-XXX, 4 hours offline).",
        "_default": "{arg}: all disks online.",
    },
    "get_pool_health": {
        "_default": "pool {arg}: DEGRADED — 1 disk faulted, scrub in progress, errors=Read:14 Write:0 Cksum:0.",
    },
    "get_smart_data": {
        "_default": "{arg}: Reallocated_Sector_Ct=42 (threshold 0), Current_Pending_Sector=7, SMART overall-health=FAIL.",
    },
    "get_recent_5xx": {
        "_default": "{arg}: 23 x 502 Bad Gateway, 0 x 5xx other in last 5 min.",
    },
    "get_upstream_latency": {
        "_default": "{arg}: api.example.com p50=124ms, p99=4200ms (degraded); storage-node-04 p50=8200ms, p99=18000ms (CRITICAL).",
    },
    "get_active_connections": {
        "_default": "{arg}: 412 active connections, 14 in waiting state.",
    },
}


def tool_response(tool: str, arg: str) -> str:
    """Canned result for an investigative tool call on ``arg`` (host/pool/disk)."""
    table = TOOL_RESPONSES.get(tool, {})
    template = table.get(arg) or table.get("_default") or "{arg}: nominal."
    return template.replace("{arg}", arg)


# NOTE: duplicate detection is NOT faked here — Intake's list_recent_tickets
# queries the real persisted ticket store (run_demo.TicketStore) for actual
# recent tickets of the same system + issue type.


# ─── Injectable incidents ───────────────────────────────────────────────
# Each is one thing the operator can inject. ``error_logs`` are the lines the
# monitoring stream shows when this fires; ``kickoff`` (a template with {id})
# is the text the seeder posts to start the diagnosis workflow.

INCIDENTS = [
    {
        "key": "web_5xx",
        "system": "web-edge-01",
        "issue": "web_5xx",
        "sev": "sev2",
        "title": "HTTP 502 burst on web-edge-01",
        "error_logs": [
            "GET /api/v1/orders 502 4200ms",
            "upstream timed out: api.example.com",
            "POST /api/v1/checkout 502 4180ms",
            "GET /api/v1/orders 502 4220ms",
        ],
        "kickoff": (
            "{id} sev2: web server returning HTTP 502 in bursts. "
            "System: web-edge-01. issue_type: web_5xx. "
            "Symptom: '502 Bad Gateway, upstream timed out'. "
            "Matched 8 log lines starting 90 seconds ago. "
            "Triage: pick whichever specialists could plausibly be involved — "
            "this looks like it could be web *or* storage (slow backend) *or* "
            "network. Don't assume."
        ),
    },
    {
        "key": "storage_io_error",
        "system": "storage-node-04",
        "issue": "storage_io_error",
        "sev": "sev3",
        "title": "Storage I/O errors on storage-node-04 (possible duplicate)",
        "error_logs": [
            "I/O error on disk 2 (slot 2, serial WD-XXX)",
            "pool tank: I/O error on disk 2",
            "latency=8200ms read pool=tank",
        ],
        "kickoff": (
            "{id} sev3: storage_io_error on storage-node-04. "
            "Symptom: 'pool tank: I/O error on disk 2'. "
            "Matched 4 log lines starting 2 min ago. "
            "Intake: use list_recent_tickets to check whether this duplicates a "
            "recent resolved ticket for the same system + issue type."
        ),
    },
]


def incident(key: str) -> dict:
    """Look up an injectable incident by key (KeyError if unknown)."""
    for inc in INCIDENTS:
        if inc["key"] == key:
            return inc
    raise KeyError(f"unknown incident {key!r}; known: {incident_keys()}")


def incident_keys() -> list[str]:
    return [str(inc["key"]) for inc in INCIDENTS]
