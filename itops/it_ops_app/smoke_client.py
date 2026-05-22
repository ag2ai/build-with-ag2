"""Headless WebSocket smoke test for server.py.

Connects to the running backend, injects the 'full' scenario, prints a
compact event trace, answers the HITL escalation when it arrives, and
asserts the ticket reaches a terminal remediation status.

Usage (with the server already running on :8000):

    python smoke_client.py
"""

from __future__ import annotations

import asyncio
import json
import sys

import websockets

URL = "ws://127.0.0.1:8000/ws"


async def main() -> int:
    async with websockets.connect(URL, max_size=None) as ws:
        await ws.send(json.dumps({"type": "inject", "incident": "web_5xx"}))

        terminal = {"Resolved", "Partially Resolved", "Needs Followup", "Duplicate"}
        final_status: str | None = None
        deadline = asyncio.get_event_loop().time() + 300

        while asyncio.get_event_loop().time() < deadline:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=300)
            except TimeoutError:
                break
            ev = json.loads(raw)
            kind = ev.get("type")
            p = ev.get("payload", {})

            if kind == "envelope":
                tool = f" {p.get('tool')}()" if p.get("tool") else ""
                txt = f" {p['text'][:50]!r}" if p.get("text") else ""
                print(
                    f"  envelope   {p.get('sender'):>12}  {p.get('event_type')}{tool}{txt}"
                )
            elif kind == "channel_opened":
                print(
                    f"  channel    OPENED  stage={p.get('stage')} ticket={p.get('ticket_id')}"
                )
            elif kind == "ticket_status":
                print(f"  ticket     {p.get('id')} → {p.get('status')}")
                if p.get("status") in terminal:
                    final_status = p.get("status")
            elif kind == "hitl_requested":
                print(
                    f"  ⚠ HITL     escalation on {p.get('channel_id')[:8]}… "
                    f"fixers={p.get('fixers')}"
                )
                # Operator answers from the "UI".
                await ws.send(
                    json.dumps(
                        {
                            "type": "hitl_response",
                            "channel_id": p.get("channel_id"),
                            "decision": "APPROVED via smoke client: proceed with the disruptive step.",
                        }
                    )
                )
                print("  → HITL     operator response sent")
            elif kind == "hitl_resolved":
                print(
                    f"  HITL       resolved (decision sent={bool(p.get('decision'))})"
                )
            elif kind == "channel_closed":
                print(f"  channel    CLOSED  reason={p.get('reason')}")
            elif kind == "error":
                print(f"  ERROR      {p}")

            # Resolved status arrives after the remediation channel closes.
            if final_status is not None and kind == "channel_closed":
                # give the final ticket_status a beat if it lands after close
                pass
            if final_status is not None and kind in ("ticket_status",):
                break

        print("\n  final ticket status:", final_status)
        ok = final_status in terminal
        print("  SMOKE:", "PASS" if ok else "FAIL")
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
