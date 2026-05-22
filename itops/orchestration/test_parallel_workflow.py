"""Tests for ParallelWorkflowAdapter.

Strategy: drive the adapter directly (validate_send / fold / on_accepted)
rather than spinning up a full Hub. Each test constructs the envelopes
a real workflow would have produced — same EV_PACKET shape, same
routing dict.

The headline test is ``test_wal_replay_charter``: drive a complete
fan-out/fan-in run, capture the resulting WAL, then independently
re-fold an empty initial state over that WAL and assert byte-equivalence
with the live state at every step. This is the gate that proves the
WAL-as-source-of-truth invariant holds.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from autogen.beta.network import (
    AgentTarget,
    ChannelState,
    Envelope,
    FromSpeaker,
    Participant,
    ParticipantRole,
    TerminateTarget,
    ToolCalled,
    Transition,
    TransitionGraph,
)
from autogen.beta.network.adapters.base import (
    ChannelMetadata,
)
from parallel_workflow import (
    DynamicParallelTarget,
    ParallelAgentsTarget,
    ParallelWorkflowAdapter,
    ParallelWorkflowState,
)

# ─── Helpers ────────────────────────────────────────────────────────────

EV_PACKET = "ag2.packet"


def make_participants(*agent_ids: str) -> list[Participant]:
    """Build a Participant list. First entry is the INITIATOR."""
    out: list[Participant] = []
    for i, aid in enumerate(agent_ids):
        role = ParticipantRole.INITIATOR if i == 0 else ParticipantRole.PARTICIPANT
        out.append(
            Participant(
                agent_id=aid,
                role=role,
                order=i,
                joined_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            )
        )
    return out


def make_metadata(
    adapter: ParallelWorkflowAdapter, agent_ids: list[str], graph: TransitionGraph
) -> ChannelMetadata:
    participants = make_participants(*agent_ids)
    return ChannelMetadata(
        channel_id="ch-test",
        manifest=adapter.manifest,
        creator_id=agent_ids[0],
        participants=participants,
        state=ChannelState.ACTIVE,
        created_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        knobs={"graph": graph.to_dict()},
    )


def packet(
    sender_id: str,
    *,
    channel_id: str = "ch-test",
    envelope_id: str = "",
    kind: str = "handoff",
    tool: str | None = None,
    tool_args: dict | None = None,
    body: str = "",
) -> Envelope:
    """Construct an EV_PACKET envelope that mimics what build_round_envelope
    would have produced after an LLM turn."""
    routing: dict = {"kind": kind}
    if tool is not None:
        routing["tool"] = tool
    if tool_args is not None:
        routing["tool_args"] = tool_args
    return Envelope(
        channel_id=channel_id,
        sender_id=sender_id,
        audience=None,
        event_type=EV_PACKET,
        event_data={
            "routing": routing,
            "context_updates": {"set": {}, "delete": []},
            "body": body,
        },
        envelope_id=envelope_id or f"env-{sender_id}-{tool or 'text'}",
    )


def state_snapshot(state: ParallelWorkflowState) -> dict:
    """Convert a state to a byte-stable dict for equality comparison."""
    return {
        "participant_order": list(state.participant_order),
        "expected_next_speaker": state.expected_next_speaker,
        "pending_speakers": list(state.pending_speakers),  # tuple → list for JSON
        "last_speaker_id": state.last_speaker_id,
        "last_envelope_id": state.last_envelope_id,
        "turn_count": state.turn_count,
        "pending_close_reason": state.pending_close_reason,
        "creator_id": state.creator_id,
        "graph_data": state.graph_data,
        "context_vars": state.context_vars,
    }


# ─── The IT-ops triage graph ────────────────────────────────────────────

TICKETBOT = "agent-ticketbot"
INTAKE = "agent-intake"
TRIAGE = "agent-triage"
NET = "agent-net"
STOR = "agent-stor"
WEB = "agent-web"
RCA = "agent-rca"
REMEDIATION = "agent-remediation"

ALL_AGENTS = [TICKETBOT, INTAKE, TRIAGE, NET, STOR, WEB, RCA, REMEDIATION]


def make_triage_graph() -> TransitionGraph:
    """Build the exact graph from §6.2 of the design doc."""
    return TransitionGraph(
        initial_speaker=TICKETBOT,
        transitions=[
            # L0 dedup terminals
            Transition(
                when=ToolCalled("mark_as_duplicate"),
                then=TerminateTarget("duplicate"),
            ),
            Transition(
                when=ToolCalled("proceed_to_triage"),
                then=AgentTarget(TRIAGE),
            ),
            # L1 triage fans out
            Transition(
                when=ToolCalled("assign_specialists"),
                then=DynamicParallelTarget(
                    from_tool_arg="specialists",
                    nickname_to_agent_id={
                        "network": NET,
                        "storage": STOR,
                        "web": WEB,
                    },
                ),
            ),
            # L2 specialist submission → joins to RCA
            Transition(
                when=ToolCalled("submit_findings"),
                then=AgentTarget(RCA),
            ),
            # L3 → L4
            Transition(
                when=ToolCalled("submit_rca"),
                then=AgentTarget(REMEDIATION),
            ),
            Transition(
                when=ToolCalled("post_recommendations"),
                then=TerminateTarget("resolved"),
            ),
            # Kickoff: TicketBot → Intake
            Transition(
                when=FromSpeaker(TICKETBOT),
                then=AgentTarget(INTAKE),
            ),
        ],
        default_target=TerminateTarget("no_match"),
        max_turns=22,
    )


# ─── Unit tests ─────────────────────────────────────────────────────────


def test_initial_state_starts_with_scalar_speaker():
    adapter = ParallelWorkflowAdapter()
    graph = make_triage_graph()
    metadata = make_metadata(adapter, ALL_AGENTS, graph)

    state = adapter.initial_state(metadata)

    assert state.expected_next_speaker == TICKETBOT
    assert state.pending_speakers == ()
    assert state.turn_count == 0
    assert state.creator_id == TICKETBOT


def test_normal_handoff_advances_scalar_speaker():
    adapter = ParallelWorkflowAdapter()
    graph = make_triage_graph()
    metadata = make_metadata(adapter, ALL_AGENTS, graph)
    state = adapter.initial_state(metadata)

    # TicketBot speaks → graph routes to Intake via FromSpeaker rule.
    env = packet(TICKETBOT, kind="text", body="INC-001: web 5xx burst")
    new = adapter.fold(env, state)

    assert new.expected_next_speaker == INTAKE
    assert new.pending_speakers == ()
    assert new.turn_count == 1
    assert new.last_speaker_id == TICKETBOT


def test_intake_proceeds_to_triage():
    adapter = ParallelWorkflowAdapter()
    graph = make_triage_graph()
    metadata = make_metadata(adapter, ALL_AGENTS, graph)
    state = adapter.initial_state(metadata)

    # Walk to Intake
    s1 = adapter.fold(packet(TICKETBOT, kind="text", body="INC-001"), state)
    assert s1.expected_next_speaker == INTAKE

    # Intake calls proceed_to_triage → routes to Triage
    s2 = adapter.fold(packet(INTAKE, tool="proceed_to_triage"), s1)
    assert s2.expected_next_speaker == TRIAGE
    assert s2.pending_speakers == ()


def test_intake_mark_as_duplicate_terminates():
    adapter = ParallelWorkflowAdapter()
    graph = make_triage_graph()
    metadata = make_metadata(adapter, ALL_AGENTS, graph)
    state = adapter.initial_state(metadata)
    s1 = adapter.fold(packet(TICKETBOT, kind="text"), state)
    s2 = adapter.fold(packet(INTAKE, tool="mark_as_duplicate"), s1)

    assert s2.expected_next_speaker is None
    assert s2.pending_speakers == ()
    assert s2.pending_close_reason == "duplicate"

    result = adapter.on_accepted(metadata, packet(INTAKE, tool="mark_as_duplicate"), s2)
    assert result.next_state == ChannelState.CLOSED
    assert result.auto_close_reason == "duplicate"


def test_dynamic_parallel_target_populates_pending_set():
    """Triage calls assign_specialists(["network", "storage"]) → fan-out."""
    adapter = ParallelWorkflowAdapter()
    graph = make_triage_graph()
    metadata = make_metadata(adapter, ALL_AGENTS, graph)
    state = adapter.initial_state(metadata)

    s1 = adapter.fold(packet(TICKETBOT, kind="text"), state)
    s2 = adapter.fold(packet(INTAKE, tool="proceed_to_triage"), s1)
    s3 = adapter.fold(
        packet(
            TRIAGE,
            tool="assign_specialists",
            tool_args={"specialists": ["network", "storage"]},
        ),
        s2,
    )

    assert s3.expected_next_speaker is None
    # sorted: agent-net < agent-stor lexicographically
    assert s3.pending_speakers == tuple(sorted([NET, STOR]))


def test_dynamic_parallel_with_three_specialists():
    adapter = ParallelWorkflowAdapter()
    graph = make_triage_graph()
    metadata = make_metadata(adapter, ALL_AGENTS, graph)
    state = adapter.initial_state(metadata)
    s1 = adapter.fold(packet(TICKETBOT, kind="text"), state)
    s2 = adapter.fold(packet(INTAKE, tool="proceed_to_triage"), s1)
    s3 = adapter.fold(
        packet(
            TRIAGE,
            tool="assign_specialists",
            tool_args={"specialists": ["network", "storage", "web"]},
        ),
        s2,
    )
    assert s3.pending_speakers == tuple(sorted([NET, STOR, WEB]))


def test_dynamic_parallel_rejects_unknown_nickname():
    adapter = ParallelWorkflowAdapter()
    graph = make_triage_graph()
    metadata = make_metadata(adapter, ALL_AGENTS, graph)
    state = adapter.initial_state(metadata)
    s1 = adapter.fold(packet(TICKETBOT, kind="text"), state)
    s2 = adapter.fold(packet(INTAKE, tool="proceed_to_triage"), s1)
    with pytest.raises(Exception, match="unknown nickname"):
        adapter.fold(
            packet(
                TRIAGE,
                tool="assign_specialists",
                tool_args={"specialists": ["network", "BOGUS"]},
            ),
            s2,
        )


def test_first_specialist_submit_does_NOT_route_to_rca():
    """The join transition is suppressed while pending_speakers is non-empty.

    This is the critical correctness test for parallel mode.
    """
    adapter = ParallelWorkflowAdapter()
    graph = make_triage_graph()
    metadata = make_metadata(adapter, ALL_AGENTS, graph)
    state = adapter.initial_state(metadata)
    s1 = adapter.fold(packet(TICKETBOT, kind="text"), state)
    s2 = adapter.fold(packet(INTAKE, tool="proceed_to_triage"), s1)
    s3 = adapter.fold(
        packet(
            TRIAGE,
            tool="assign_specialists",
            tool_args={"specialists": ["network", "storage"]},
        ),
        s2,
    )
    # First specialist submits — should NOT advance to RCA.
    s4 = adapter.fold(packet(NET, tool="submit_findings"), s3)

    assert s4.expected_next_speaker is None, (
        "RCA must not yet be the expected next speaker — Storage hasn't submitted"
    )
    assert s4.pending_speakers == (STOR,), "Only Storage should remain pending"


def test_last_specialist_submit_releases_to_rca():
    """When the last pending speaker submits, the join fires."""
    adapter = ParallelWorkflowAdapter()
    graph = make_triage_graph()
    metadata = make_metadata(adapter, ALL_AGENTS, graph)
    state = adapter.initial_state(metadata)
    s1 = adapter.fold(packet(TICKETBOT, kind="text"), state)
    s2 = adapter.fold(packet(INTAKE, tool="proceed_to_triage"), s1)
    s3 = adapter.fold(
        packet(
            TRIAGE,
            tool="assign_specialists",
            tool_args={"specialists": ["network", "storage"]},
        ),
        s2,
    )
    s4 = adapter.fold(packet(NET, tool="submit_findings"), s3)
    s5 = adapter.fold(packet(STOR, tool="submit_findings"), s4)

    assert s5.expected_next_speaker == RCA, (
        "Join should release to RCA after the last pending speaker"
    )
    assert s5.pending_speakers == ()


def test_validate_send_gate_in_parallel_mode():
    adapter = ParallelWorkflowAdapter()
    graph = make_triage_graph()
    metadata = make_metadata(adapter, ALL_AGENTS, graph)
    state = adapter.initial_state(metadata)
    s1 = adapter.fold(packet(TICKETBOT, kind="text"), state)
    s2 = adapter.fold(packet(INTAKE, tool="proceed_to_triage"), s1)
    s3 = adapter.fold(
        packet(
            TRIAGE,
            tool="assign_specialists",
            tool_args={"specialists": ["network", "storage"]},
        ),
        s2,
    )
    # Any pending speaker may post.
    adapter.validate_send(metadata, packet(NET, tool="submit_findings"), s3)
    adapter.validate_send(metadata, packet(STOR, tool="submit_findings"), s3)
    # Non-pending sender is rejected.
    with pytest.raises(Exception, match="expects one of"):
        adapter.validate_send(metadata, packet(WEB, tool="submit_findings"), s3)
    # Triage is also rejected (already spoke, no longer pending).
    with pytest.raises(Exception, match="expects one of"):
        adapter.validate_send(metadata, packet(TRIAGE, tool="anything"), s3)


def test_validate_send_gate_in_scalar_mode():
    adapter = ParallelWorkflowAdapter()
    graph = make_triage_graph()
    metadata = make_metadata(adapter, ALL_AGENTS, graph)
    state = adapter.initial_state(metadata)

    # Initial speaker is TicketBot; everyone else should be rejected.
    adapter.validate_send(metadata, packet(TICKETBOT, kind="text"), state)
    with pytest.raises(Exception, match="expects"):
        adapter.validate_send(metadata, packet(INTAKE, kind="text"), state)


def test_resolved_flow_terminates():
    adapter = ParallelWorkflowAdapter()
    graph = make_triage_graph()
    metadata = make_metadata(adapter, ALL_AGENTS, graph)
    state = adapter.initial_state(metadata)
    s1 = adapter.fold(packet(TICKETBOT, kind="text"), state)
    s2 = adapter.fold(packet(INTAKE, tool="proceed_to_triage"), s1)
    s3 = adapter.fold(
        packet(
            TRIAGE,
            tool="assign_specialists",
            tool_args={"specialists": ["network"]},
        ),
        s2,
    )
    # Single-specialist fan-out — that's still a "parallel" target,
    # exercises the degenerate-set case.
    assert s3.pending_speakers == (NET,)
    s4 = adapter.fold(packet(NET, tool="submit_findings"), s3)
    assert s4.expected_next_speaker == RCA
    s5 = adapter.fold(packet(RCA, tool="submit_rca"), s4)
    assert s5.expected_next_speaker == REMEDIATION
    s6 = adapter.fold(packet(REMEDIATION, tool="post_recommendations"), s5)
    assert s6.expected_next_speaker is None
    assert s6.pending_close_reason == "resolved"

    result = adapter.on_accepted(
        metadata,
        packet(REMEDIATION, tool="post_recommendations"),
        s6,
    )
    assert result.next_state == ChannelState.CLOSED
    assert result.auto_close_reason == "resolved"


# ─── The headline test: WAL-replay charter ─────────────────────────────


def test_wal_replay_charter():
    """Drive a representative fan-out/fan-in scenario; capture the WAL;
    independently re-fold the WAL from scratch and assert byte-equivalence
    with the live state at every step.

    This is THE test that proves the WAL-as-source-of-truth invariant.
    If anything in the adapter relies on hidden state outside the WAL
    or the channel manifest, this test will fail.
    """
    adapter = ParallelWorkflowAdapter()
    graph = make_triage_graph()
    metadata = make_metadata(adapter, ALL_AGENTS, graph)

    # ── Live drive: produce the WAL ─────────────────────────────────
    live_state = adapter.initial_state(metadata)
    initial_state_dict = state_snapshot(live_state)

    # Representative scenario: not a duplicate; triage picks Network +
    # Storage (Network submits first, then Storage); RCA + Remediation
    # close it out.
    wal: list[Envelope] = [
        packet(TICKETBOT, kind="text", body="INC-007: web 5xx burst, also high storage latency"),
        packet(INTAKE, tool="proceed_to_triage", body="No recent matches"),
        packet(
            TRIAGE,
            tool="assign_specialists",
            tool_args={"specialists": ["network", "storage"]},
            body="Ambiguous — both could be culprit",
        ),
        packet(NET, tool="submit_findings", body="Routes healthy"),
        packet(STOR, tool="submit_findings", body="Disk smart errors on storage-node-04"),
        packet(RCA, tool="submit_rca", body="Disk failure on storage-node-04"),
        packet(REMEDIATION, tool="post_recommendations", body="Failover, replace disk, ..."),
    ]

    # Validate, fold, snapshot at each step.
    live_snapshots = [initial_state_dict]
    for env in wal:
        adapter.validate_send(metadata, env, live_state)
        live_state = adapter.fold(env, live_state)
        live_snapshots.append(state_snapshot(live_state))

    # Sanity: live drive terminated correctly.
    assert live_state.expected_next_speaker is None
    assert live_state.pending_close_reason == "resolved"
    assert live_state.turn_count == len(wal)

    # ── Independent replay: fold from initial state over the WAL ────
    #
    # This is the WAL-replay charter. We reconstruct an empty state
    # from the same metadata, then re-apply every envelope in WAL
    # order, and assert each intermediate state matches the live drive.

    replay_state = adapter.initial_state(metadata)
    replay_snapshots = [state_snapshot(replay_state)]
    for env in wal:
        replay_state = adapter.fold(env, replay_state)
        replay_snapshots.append(state_snapshot(replay_state))

    # Byte-equivalence at every step. If any state diverges, we have
    # hidden state somewhere.
    for i, (live, replay) in enumerate(zip(live_snapshots, replay_snapshots, strict=True)):
        # JSON-encode both for a deterministic byte comparison.
        live_bytes = json.dumps(live, sort_keys=True).encode("utf-8")
        replay_bytes = json.dumps(replay, sort_keys=True).encode("utf-8")
        assert live_bytes == replay_bytes, (
            f"WAL replay diverged at step {i}\n  live   = {live}\n  replay = {replay}"
        )

    # Also assert: a completely fresh adapter instance (no shared state
    # with the one used for the live drive) can replay correctly too.
    # This catches any state accidentally stored on the adapter
    # instance rather than in ParallelWorkflowState.
    fresh_adapter = ParallelWorkflowAdapter()
    fresh_state = fresh_adapter.initial_state(metadata)
    for env in wal:
        fresh_state = fresh_adapter.fold(env, fresh_state)
    fresh_final = state_snapshot(fresh_state)
    live_final = live_snapshots[-1]
    assert json.dumps(fresh_final, sort_keys=True) == json.dumps(live_final, sort_keys=True), (
        "Fresh-adapter replay diverged from live drive"
    )


def test_wal_replay_with_duplicate_path():
    """Same charter, but the dedup path: workflow terminates at Intake."""
    adapter = ParallelWorkflowAdapter()
    graph = make_triage_graph()
    metadata = make_metadata(adapter, ALL_AGENTS, graph)

    live_state = adapter.initial_state(metadata)
    wal = [
        packet(TICKETBOT, kind="text", body="INC-008: same as INC-007 from 2 min ago"),
        packet(INTAKE, tool="mark_as_duplicate", body="dup of INC-007"),
    ]
    for env in wal:
        adapter.validate_send(metadata, env, live_state)
        live_state = adapter.fold(env, live_state)

    assert live_state.pending_close_reason == "duplicate"

    # Replay
    replay_state = adapter.initial_state(metadata)
    for env in wal:
        replay_state = adapter.fold(env, replay_state)

    assert json.dumps(state_snapshot(live_state), sort_keys=True) == json.dumps(
        state_snapshot(replay_state), sort_keys=True
    )


def test_graph_serialisation_round_trip():
    """The graph itself must round-trip through JSON without losing
    any field of the new transition targets. This is what makes the
    WAL invariant hold in the face of dynamic routing."""
    g = make_triage_graph()
    encoded = json.dumps(g.to_dict())
    decoded = json.loads(encoded)
    g2 = TransitionGraph.loads(decoded)

    # Find the DynamicParallelTarget in both
    dyn_orig = next(t.then for t in g.transitions if isinstance(t.then, DynamicParallelTarget))
    dyn_loaded = next(t.then for t in g2.transitions if isinstance(t.then, DynamicParallelTarget))
    assert dyn_loaded.from_tool_arg == dyn_orig.from_tool_arg
    assert dyn_loaded.nickname_to_agent_id == dyn_orig.nickname_to_agent_id


def test_static_parallel_agents_target():
    """ParallelAgentsTarget (the static variant) populates pending_speakers
    directly without reading tool args."""
    adapter = ParallelWorkflowAdapter()

    # A minimal graph that uses the static target on triage handoff.
    g = TransitionGraph(
        initial_speaker=TICKETBOT,
        transitions=[
            Transition(
                when=ToolCalled("static_fanout"),
                then=ParallelAgentsTarget(agent_ids=[NET, STOR, WEB]),
            ),
            Transition(
                when=ToolCalled("submit_findings"),
                then=AgentTarget(RCA),
            ),
            Transition(
                when=FromSpeaker(TICKETBOT),
                then=AgentTarget(TRIAGE),
            ),
        ],
        default_target=TerminateTarget("no_match"),
        max_turns=10,
    )
    metadata = make_metadata(
        adapter,
        [TICKETBOT, TRIAGE, NET, STOR, WEB, RCA],
        g,
    )
    state = adapter.initial_state(metadata)
    s1 = adapter.fold(packet(TICKETBOT, kind="text"), state)
    s2 = adapter.fold(packet(TRIAGE, tool="static_fanout"), s1)
    assert s2.pending_speakers == tuple(sorted([NET, STOR, WEB]))


def test_build_round_envelope_attaches_tool_args():
    """Regression test for an issue surfaced by running real code:
    `_resolve_routing` in AG2 main does NOT populate `tool_args` on
    the routing dict — it only carries `kind`/`tool`/`reason`/`target`.
    Without our adapter's enrichment, `DynamicParallelTarget` would
    never see the fan-out list and parallel mode would never fire
    in the end-to-end flow.

    This test exercises the build_round_envelope path with a real
    ToolCallEvent and confirms `routing.tool_args` is populated.
    """
    from types import SimpleNamespace

    from autogen.beta.network.adapters.workflow import ToolCallEvent

    adapter = ParallelWorkflowAdapter()
    graph = make_triage_graph()
    metadata = make_metadata(adapter, ALL_AGENTS, graph)
    state = adapter.initial_state(metadata)

    # Walk to Triage's turn
    s1 = adapter.fold(packet(TICKETBOT, kind="text"), state)
    s2 = adapter.fold(packet(INTAKE, tool="proceed_to_triage"), s1)

    # Simulate the Triage agent's stream: one ToolCallEvent for
    # assign_specialists, with JSON-encoded arguments.
    tool_call = ToolCallEvent(
        name="assign_specialists",
        arguments=json.dumps({"specialists": ["network", "storage"], "reason": "ambiguous"}),
    )
    reply = SimpleNamespace(body="Routing investigation")

    # A minimal fake Hub object with the name→id map. build_round_envelope
    # only needs `_name_to_id` from the hub.
    fake_hub = SimpleNamespace(_name_to_id={})

    env = adapter.build_round_envelope(
        metadata=metadata,
        sender_id=TRIAGE,
        reply=reply,
        events=[tool_call],
        state=s2,
        hub=fake_hub,
    )

    assert env is not None, "build_round_envelope returned None unexpectedly"
    routing = env.event_data["routing"]
    assert routing["kind"] == "handoff"
    assert routing["tool"] == "assign_specialists"
    assert routing["tool_args"] == {
        "specialists": ["network", "storage"],
        "reason": "ambiguous",
    }, "tool_args must be enriched onto routing for DynamicParallelTarget"

    # End-to-end: fold the produced envelope and confirm fan-out fires.
    s3 = adapter.fold(env, s2)
    assert s3.pending_speakers == tuple(sorted([NET, STOR]))
    assert s3.expected_next_speaker is None


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
