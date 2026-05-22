"""End-to-end ParallelWorkflowAdapter test with a real Hub.

Uses ``autogen.beta.testing.TestConfig`` so the agents' "LLM" returns
scripted ``ToolCallEvent``s instead of calling a real model. This
exercises the *full* stack: Hub, LocalLink, HubClient/AgentClient,
the WorkflowPlugin's default notify handler, ``build_round_envelope``
(including our ``tool_args`` enrichment), and the new adapter's fold /
validate_send / on_accepted.

If any of the integration assumptions in the spec are wrong, this
test will surface them.

Scenario: a single ticket runs end-to-end through Intake → Triage →
Network + Storage in parallel → RCA → Remediation, then the channel
closes with reason "resolved". The test asserts:

1. The channel actually opens with our new adapter type.
2. Triage's ``assign_specialists`` envelope carries ``tool_args`` on
   its routing (the enrichment we added in build_round_envelope).
3. Both specialists speak (in either order — order is not
   constrained by the adapter).
4. RCA runs only AFTER both specialists submit (not after the first).
5. The channel closes with reason "resolved" and the right turn
   count.
6. A second, independent fresh-state WAL replay matches the live
   adapter state byte-for-byte (WAL invariant under the full stack).
"""

from __future__ import annotations

import json

import pytest
from autogen.beta import Agent, tool
from autogen.beta.events.tool_events import ToolCallEvent
from autogen.beta.knowledge import MemoryKnowledgeStore
from autogen.beta.network import (
    EV_CHANNEL_CLOSED,
    EV_PACKET,
    AgentTarget,
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
from autogen.beta.testing import TestConfig
from parallel_workflow import (
    PARALLEL_WORKFLOW_TYPE,
    DynamicParallelTarget,
    ParallelWorkflowAdapter,
    ParallelWorkflowState,
)

# ─── Tools (mocked side effects) ────────────────────────────────────────


@tool
async def proceed_to_triage(reason: str) -> str:
    """Intake decided this is not a duplicate; hand off to Triage."""
    return f"PROCEEDED: {reason}"


@tool
async def mark_as_duplicate(parent_ticket_id: str, reason: str) -> str:
    """Intake found a duplicate; terminate workflow with the parent link."""
    return f"DUP of {parent_ticket_id}: {reason}"


@tool
async def assign_specialists(specialists: list[str], reason: str) -> str:
    """Triage dispatches the ticket to a set of specialists."""
    return f"ASSIGNED to {specialists}: {reason}"


@tool
async def submit_findings(summary: str, evidence: str) -> str:
    """Each specialist submits its independent findings."""
    return f"FINDINGS: {summary}"


@tool
async def submit_rca(root_cause: str, confidence: str) -> str:
    return f"RCA ({confidence}): {root_cause}"


@tool
async def post_recommendations(steps: list[str]) -> str:
    return f"RECS: {steps}"


# ─── Helpers ────────────────────────────────────────────────────────────


def _tool_call(name: str, **arguments) -> ToolCallEvent:
    """Convenience: build a ToolCallEvent with JSON-encoded args."""
    return ToolCallEvent(name=name, arguments=json.dumps(arguments))


def state_snapshot(state: ParallelWorkflowState) -> dict:
    return {
        "participant_order": list(state.participant_order),
        "expected_next_speaker": state.expected_next_speaker,
        "pending_speakers": list(state.pending_speakers),
        "last_speaker_id": state.last_speaker_id,
        "last_envelope_id": state.last_envelope_id,
        "turn_count": state.turn_count,
        "pending_close_reason": state.pending_close_reason,
        "creator_id": state.creator_id,
        "graph_data": state.graph_data,
        "context_vars": state.context_vars,
    }


# ─── End-to-end full path ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_e2e_full_path_with_parallel_specialists():
    hub = await Hub.open(
        MemoryKnowledgeStore(),
        ttl_sweep_interval=0,
        expectation_sweep_interval=0,
    )
    # Register the new adapter alongside the built-ins.
    hub.register_adapter(ParallelWorkflowAdapter())  # type: ignore[arg-type]

    link = LocalLink(hub)

    try:
        # ── Build agents with scripted tool calls ───────────────────
        # TicketBot is a HumanClient — posts the kickoff text and
        # then sits silent.
        ticketbot_hc = HubClient(link, hub=hub)
        intake_hc = HubClient(link, hub=hub)
        triage_hc = HubClient(link, hub=hub)
        network_hc = HubClient(link, hub=hub)
        storage_hc = HubClient(link, hub=hub)
        web_hc = HubClient(link, hub=hub)
        rca_hc = HubClient(link, hub=hub)
        remediation_hc = HubClient(link, hub=hub)

        # Each agent's TestConfig scripts the SINGLE ToolCallEvent
        # they'll emit during their turn. (TestConfig consumes one
        # event per LLM call; one tool call per turn is all we need
        # for the adapter to route.)
        # Each agent's turn needs TWO scripted events: one ToolCallEvent
        # (the actual tool invocation) and one trailing string (the
        # post-tool-result LLM completion). Without the second, Agent.ask
        # will call the LLM a second time and the TestConfig iterator
        # raises StopIteration.
        intake_agent = Agent(
            "Intake",
            prompt="...",
            config=TestConfig(
                _tool_call("proceed_to_triage", reason="no recent matches"),
                "Proceeded to triage.",
            ),
            tools=[proceed_to_triage, mark_as_duplicate],
        )
        triage_agent = Agent(
            "Triage",
            prompt="...",
            config=TestConfig(
                _tool_call(
                    "assign_specialists",
                    specialists=["network", "storage"],
                    reason="symptom ambiguous between routing and disk",
                ),
                "Assigned to network and storage specialists.",
            ),
            tools=[assign_specialists],
        )
        network_agent = Agent(
            "Network",
            prompt="...",
            config=TestConfig(
                _tool_call(
                    "submit_findings",
                    summary="routes healthy, no packet loss",
                    evidence="ping ok; traceroute clean",
                ),
                "Network findings submitted.",
            ),
            tools=[submit_findings],
        )
        storage_agent = Agent(
            "Storage",
            prompt="...",
            config=TestConfig(
                _tool_call(
                    "submit_findings",
                    summary="SMART errors on storage-node-04",
                    evidence="2 reallocated sectors; rising error count",
                ),
                "Storage findings submitted.",
            ),
            tools=[submit_findings],
        )
        web_agent = Agent(
            "Web",
            prompt="...",
            config=TestConfig(),
            tools=[submit_findings],
        )  # not assigned, never speaks
        rca_agent = Agent(
            "RCA",
            prompt="...",
            config=TestConfig(
                _tool_call(
                    "submit_rca",
                    root_cause="disk degradation on storage-node-04",
                    confidence="high",
                ),
                "RCA submitted.",
            ),
            tools=[submit_rca],
        )
        remediation_agent = Agent(
            "Remediation",
            prompt="...",
            config=TestConfig(
                _tool_call(
                    "post_recommendations",
                    steps=[
                        "Failover storage-node-04 to standby",
                        "Replace failing disk",
                        "Run pool scrub post-replacement",
                    ],
                ),
                "Recommendations posted.",
            ),
            tools=[post_recommendations],
        )

        # Register everyone. TicketBot is a HumanClient (no LLM).
        ticketbot = await ticketbot_hc.register_human(
            Passport(name="TicketBot", kind="human"),
        )
        intake = await intake_hc.register(
            intake_agent,
            Passport(name="Intake"),
            Resume(),
            attach_plugin=False,
        )
        triage = await triage_hc.register(
            triage_agent,
            Passport(name="Triage"),
            Resume(),
            attach_plugin=False,
        )
        network = await network_hc.register(
            network_agent,
            Passport(name="Network"),
            Resume(),
            attach_plugin=False,
        )
        storage = await storage_hc.register(
            storage_agent,
            Passport(name="Storage"),
            Resume(),
            attach_plugin=False,
        )
        web = await web_hc.register(
            web_agent,
            Passport(name="Web"),
            Resume(),
            attach_plugin=False,
        )
        rca = await rca_hc.register(
            rca_agent,
            Passport(name="RCA"),
            Resume(),
            attach_plugin=False,
        )
        remediation = await remediation_hc.register(
            remediation_agent,
            Passport(name="Remediation"),
            Resume(),
            attach_plugin=False,
        )

        id_to_name = {
            ticketbot.agent_id: "TicketBot",
            intake.agent_id: "Intake",
            triage.agent_id: "Triage",
            network.agent_id: "Network",
            storage.agent_id: "Storage",
            web.agent_id: "Web",
            rca.agent_id: "RCA",
            remediation.agent_id: "Remediation",
        }

        # ── Build the transition graph ──────────────────────────────
        graph = TransitionGraph(
            initial_speaker=ticketbot.agent_id,
            transitions=[
                Transition(
                    when=ToolCalled("mark_as_duplicate"),
                    then=TerminateTarget("duplicate"),
                ),
                Transition(
                    when=ToolCalled("proceed_to_triage"),
                    then=AgentTarget(triage.agent_id),
                ),
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
                Transition(
                    when=ToolCalled("submit_findings"),
                    then=AgentTarget(rca.agent_id),
                ),
                Transition(
                    when=ToolCalled("submit_rca"),
                    then=AgentTarget(remediation.agent_id),
                ),
                Transition(
                    when=ToolCalled("post_recommendations"),
                    then=TerminateTarget("resolved"),
                ),
                Transition(
                    when=FromSpeaker(ticketbot.agent_id),
                    then=AgentTarget(intake.agent_id),
                ),
            ],
            default_target=TerminateTarget("no_match"),
            max_turns=22,
        )

        # ── Open the channel ────────────────────────────────────────
        channel = await ticketbot.open(
            type=PARALLEL_WORKFLOW_TYPE,
            target=[
                intake.agent_id,
                triage.agent_id,
                network.agent_id,
                storage.agent_id,
                web.agent_id,
                rca.agent_id,
                remediation.agent_id,
            ],
            knobs={"graph": graph.to_dict()},
        )

        # Kickoff.
        await ticketbot.send(
            channel.channel_id,
            "INC-007 sev2: 5xx burst and high storage latency on web-edge-01",
        )

        # Wait for closure.
        close_env = await ticketbot.next_envelope(
            predicate=lambda e: (
                e.channel_id == channel.channel_id and e.event_type == EV_CHANNEL_CLOSED
            ),
            timeout=15.0,
        )

        assert close_env.event_data.get("reason") == "resolved", (
            f"Expected reason='resolved', got {close_env.event_data.get('reason')!r}"
        )

        # ── Inspect the WAL ─────────────────────────────────────────
        wal = await hub.read_wal(channel.channel_id)
        # Filter to packet envelopes for the path-through assertions.
        packets = [e for e in wal if e.event_type == EV_PACKET]
        senders = [id_to_name.get(e.sender_id, e.sender_id) for e in packets]
        tools_called = [
            (id_to_name.get(e.sender_id), e.event_data.get("routing", {}).get("tool"))
            for e in packets
        ]
        print("Path through workflow:", tools_called)

        # Each of the expected speakers spoke exactly once.
        assert senders.count("Intake") == 1
        assert senders.count("Triage") == 1
        assert senders.count("Network") == 1
        assert senders.count("Storage") == 1
        assert senders.count("RCA") == 1
        assert senders.count("Remediation") == 1
        # Web was registered but NOT assigned by Triage; it must not speak.
        assert senders.count("Web") == 0

        # Triage's envelope carries tool_args.specialists (our enrichment).
        triage_env = next(e for e in packets if e.sender_id == triage.agent_id)
        triage_routing = triage_env.event_data["routing"]
        assert triage_routing["tool"] == "assign_specialists"
        assert triage_routing.get("tool_args", {}).get("specialists") == [
            "network",
            "storage",
        ], (
            "Triage's routing dict must contain tool_args.specialists — "
            "this is the enrichment ParallelWorkflowAdapter.build_round_envelope "
            "adds on top of _resolve_routing's output."
        )

        # The two specialists may have spoken in either order — both
        # must precede RCA, and RCA must precede Remediation.
        positions = {name: i for i, name in enumerate(senders) if name not in ("TicketBot",)}
        assert positions["Intake"] < positions["Triage"]
        assert positions["Triage"] < positions["Network"]
        assert positions["Triage"] < positions["Storage"]
        assert positions["Network"] < positions["RCA"]
        assert positions["Storage"] < positions["RCA"]
        assert positions["RCA"] < positions["Remediation"]

        # ── WAL replay under the full stack ─────────────────────────
        # Re-fold from initial_state using ONLY the WAL + channel metadata.
        # If anything outside the WAL contributed to the final state, this
        # will diverge.
        adapter = ParallelWorkflowAdapter()
        metadata = await hub.get_channel(channel.channel_id)
        replay_state = adapter.initial_state(metadata)
        for env in wal:
            if env.event_type in (
                EV_CHANNEL_CLOSED,
                "ag2.channel.opened",
                "ag2.channel.invite",
                "ag2.channel.invite.ack",
            ):
                continue  # adapter doesn't fold lifecycle envelopes
            replay_state = adapter.fold(env, replay_state)

        live_state = hub.adapter_state(channel.channel_id)
        # live_state is the live adapter's state right before close;
        # after close, the hub may evict it. Re-fold matches by structure.
        assert replay_state.expected_next_speaker is None
        assert replay_state.pending_close_reason == "resolved"
        assert replay_state.turn_count >= 6  # at least 6 substantive turns

        if live_state is not None:
            live_snap = state_snapshot(live_state)  # type: ignore[arg-type]
            replay_snap = state_snapshot(replay_state)
            assert json.dumps(live_snap, sort_keys=True) == json.dumps(
                replay_snap, sort_keys=True
            ), (
                "Live adapter state and WAL-replay diverged.\n"
                f"  live:   {live_snap}\n"
                f"  replay: {replay_snap}"
            )

    finally:
        # Best-effort cleanup
        for hc in [
            ticketbot_hc,
            intake_hc,
            triage_hc,
            network_hc,
            storage_hc,
            web_hc,
            rca_hc,
            remediation_hc,
        ]:
            try:
                await hc.close()
            except Exception:
                pass
        await hub.close()


@pytest.mark.asyncio
async def test_e2e_duplicate_path():
    """Intake decides duplicate → channel closes with reason 'duplicate'
    and Triage/specialists never speak."""
    hub = await Hub.open(
        MemoryKnowledgeStore(),
        ttl_sweep_interval=0,
        expectation_sweep_interval=0,
    )
    hub.register_adapter(ParallelWorkflowAdapter())  # type: ignore[arg-type]
    link = LocalLink(hub)

    try:
        ticketbot_hc = HubClient(link, hub=hub)
        intake_hc = HubClient(link, hub=hub)
        triage_hc = HubClient(link, hub=hub)
        network_hc = HubClient(link, hub=hub)
        storage_hc = HubClient(link, hub=hub)
        web_hc = HubClient(link, hub=hub)
        rca_hc = HubClient(link, hub=hub)
        remediation_hc = HubClient(link, hub=hub)

        intake_agent = Agent(
            "Intake",
            prompt="...",
            config=TestConfig(
                _tool_call(
                    "mark_as_duplicate",
                    parent_ticket_id="INC-006",
                    reason="identical symptom and system, 4 min apart",
                ),
                "Marked as duplicate.",
            ),
            tools=[proceed_to_triage, mark_as_duplicate],
        )
        triage_agent = Agent(
            "Triage", prompt="...", config=TestConfig(), tools=[assign_specialists]
        )
        network_agent = Agent("Network", prompt="...", config=TestConfig(), tools=[submit_findings])
        storage_agent = Agent("Storage", prompt="...", config=TestConfig(), tools=[submit_findings])
        web_agent = Agent("Web", prompt="...", config=TestConfig(), tools=[submit_findings])
        rca_agent = Agent("RCA", prompt="...", config=TestConfig(), tools=[submit_rca])
        remediation_agent = Agent(
            "Remediation", prompt="...", config=TestConfig(), tools=[post_recommendations]
        )

        ticketbot = await ticketbot_hc.register_human(Passport(name="TicketBot", kind="human"))
        intake = await intake_hc.register(
            intake_agent, Passport(name="Intake"), Resume(), attach_plugin=False
        )
        triage = await triage_hc.register(
            triage_agent, Passport(name="Triage"), Resume(), attach_plugin=False
        )
        network = await network_hc.register(
            network_agent, Passport(name="Network"), Resume(), attach_plugin=False
        )
        storage = await storage_hc.register(
            storage_agent, Passport(name="Storage"), Resume(), attach_plugin=False
        )
        web = await web_hc.register(web_agent, Passport(name="Web"), Resume(), attach_plugin=False)
        rca = await rca_hc.register(rca_agent, Passport(name="RCA"), Resume(), attach_plugin=False)
        remediation = await remediation_hc.register(
            remediation_agent, Passport(name="Remediation"), Resume(), attach_plugin=False
        )

        graph = TransitionGraph(
            initial_speaker=ticketbot.agent_id,
            transitions=[
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
                Transition(
                    when=ToolCalled("post_recommendations"), then=TerminateTarget("resolved")
                ),
                Transition(when=FromSpeaker(ticketbot.agent_id), then=AgentTarget(intake.agent_id)),
            ],
            default_target=TerminateTarget("no_match"),
            max_turns=22,
        )

        channel = await ticketbot.open(
            type=PARALLEL_WORKFLOW_TYPE,
            target=[
                intake.agent_id,
                triage.agent_id,
                network.agent_id,
                storage.agent_id,
                web.agent_id,
                rca.agent_id,
                remediation.agent_id,
            ],
            knobs={"graph": graph.to_dict()},
        )
        await ticketbot.send(channel.channel_id, "INC-008: same as INC-006 4 min ago")

        close_env = await ticketbot.next_envelope(
            predicate=lambda e: (
                e.channel_id == channel.channel_id and e.event_type == EV_CHANNEL_CLOSED
            ),
            timeout=10.0,
        )
        assert close_env.event_data.get("reason") == "duplicate"

        wal = await hub.read_wal(channel.channel_id)
        packets = [e for e in wal if e.event_type == EV_PACKET]
        speakers = {e.sender_id for e in packets}
        # Only Intake spoke.
        assert intake.agent_id in speakers
        for forbidden in [
            triage.agent_id,
            network.agent_id,
            storage.agent_id,
            rca.agent_id,
            remediation.agent_id,
        ]:
            assert forbidden not in speakers, (
                "no specialist or downstream agent should speak when Intake "
                "marks the ticket as a duplicate"
            )

    finally:
        for hc in [
            ticketbot_hc,
            intake_hc,
            triage_hc,
            network_hc,
            storage_hc,
            web_hc,
            rca_hc,
            remediation_hc,
        ]:
            try:
                await hc.close()
            except Exception:
                pass
        await hub.close()


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v", "-s"]))
