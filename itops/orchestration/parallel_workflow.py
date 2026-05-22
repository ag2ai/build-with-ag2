"""ParallelWorkflowAdapter — a new sibling adapter for AG2's beta network.

Supports fan-out / fan-in: a transition can route to multiple agents at
once via ``ParallelAgentsTarget`` (static list) or ``DynamicParallelTarget``
(list read from a tool-call argument and mapped via a JSON dict). All
listed agents may speak in any order; the workflow joins to the next
single speaker only after the last pending agent submits.

Invariants
----------

* **WAL as source of truth.** Every routing decision is a pure function of
  (state, envelope, graph_data). Graph data is JSON; state is JSON-friendly.
  Folding the WAL from ``initial_state(manifest)`` reproduces the live
  state byte-for-byte. No callables in graphs, no hidden registries.

* **No synthetic envelopes.** Adapter never fabricates envelopes that
  weren't posted by a real participant. Roll-ups are a view-policy
  concern, not envelope fabrication.

* **One mode at a time.** Either ``expected_next_speaker`` is set (scalar
  mode) OR ``pending_speakers`` is non-empty (parallel mode), never both.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, ClassVar

from autogen.beta.network.adapters.base import (
    AdapterResult,
    ChannelManifest,
    ChannelMetadata,
    ChannelState,
    Envelope,
    ViewPolicy,
)

# Reuse stable, framework-internal helpers from the workflow adapter module.
# These are routing/projection utilities that have nothing to do with
# scalar-vs-set speaker gating — they're free for any workflow-shaped
# adapter to reuse.
from autogen.beta.network.adapters.workflow import (
    EV_CONTEXT_SET,
    EV_PACKET,
    EV_TEXT,
    Expectation,
    NamedWindowedSummary,
    ParticipantSchema,
    ProtocolError,
    WorkflowGraphError,
    _is_substantive,
    _packet_text,
    _packet_turn_text,
    _resolve_routing,
    default_build_packet_envelope,
    default_build_text_envelope,
    default_render_envelope,
)
from autogen.beta.network.transitions import (
    TransitionDecision,
    TransitionGraph,
    register_target,
)

PARALLEL_WORKFLOW_TYPE = "parallel_workflow"


# ─── State ──────────────────────────────────────────────────────────────


@dataclass
class ParallelWorkflowState:
    """Adapter state for a parallel-capable workflow channel.

    Either ``expected_next_speaker`` is set (scalar mode) or
    ``pending_speakers`` is non-empty (parallel mode). Never both.

    ``pending_speakers`` is a tuple (sorted) rather than a set so the
    state is byte-stable on serialisation — required by the WAL-replay
    invariant.
    """

    participant_order: list[str]
    expected_next_speaker: str | None = None
    pending_speakers: tuple[str, ...] = ()
    last_speaker_id: str | None = None
    last_envelope_id: str | None = None
    turn_count: int = 0
    pending_close_reason: str = ""
    creator_id: str = ""
    graph_data: dict[str, Any] = field(default_factory=dict)
    context_vars: dict[str, Any] = field(default_factory=dict)


# ─── New transition targets ─────────────────────────────────────────────


@dataclass(slots=True)
class ParallelAgentsTarget:
    """Static fan-out target.

    ``agent_ids`` is the set of channel agent ids that must each speak
    exactly once before the workflow proceeds to the next transition.
    The order they speak in is not constrained.

    Stored as ``list[str]`` because TransitionGraph serialisation
    round-trips through JSON; tuple/list/set all collapse to list.
    """

    agent_ids: list[str]
    name: ClassVar[str] = "parallel_agents"

    def resolve(self, state, envelope) -> TransitionDecision:
        # next_speaker=None signals "no single next speaker" — the adapter
        # inspects the matched target object (not the decision) at fold()
        # time to know this is a parallel mode entry.
        return TransitionDecision(next_speaker=None, close_reason="")


@dataclass(slots=True)
class DynamicParallelTarget:
    """Read the fan-out set from a tool-call argument; map via a static dict.

    ``from_tool_arg`` names the tool argument whose value (a list of
    nicknames) carries the participants. ``nickname_to_agent_id`` maps
    each possible nickname to a channel agent id. Both fields are JSON-
    encodable; the entire target round-trips through TransitionGraph.

    No callables anywhere — the mapping is pure data, baked into the
    graph at construction. This is what preserves the WAL-replay
    invariant in the face of dynamic routing.
    """

    from_tool_arg: str
    nickname_to_agent_id: dict[str, str]
    name: ClassVar[str] = "dynamic_parallel"

    def resolve(self, state, envelope) -> TransitionDecision:
        # As with ParallelAgentsTarget — actual fan-out happens in
        # ParallelWorkflowAdapter.fold() which inspects the matched
        # target type. We return next_speaker=None.
        return TransitionDecision(next_speaker=None, close_reason="")


# Register the new targets on the default registry so TransitionGraph
# serialisation/deserialisation finds them.
register_target(ParallelAgentsTarget)
register_target(DynamicParallelTarget)


# ─── Adapter ────────────────────────────────────────────────────────────


class ParallelWorkflowAdapter:
    """Workflow channel adapter with fan-out / fan-in support.

    Same broad shape as ``WorkflowAdapter`` — a ``TransitionGraph`` in
    ``knobs["graph"]`` drives speaker selection — but the state model
    allows multiple agents to be "pending" at once. When a transition's
    target is a parallel target, ``fold()`` populates ``pending_speakers``
    rather than ``expected_next_speaker``. Subsequent envelopes from any
    pending speaker remove that speaker from the set; the join transition
    fires when the set becomes empty.
    """

    def __init__(self) -> None:
        self.manifest = ChannelManifest(
            type=PARALLEL_WORKFLOW_TYPE,
            version=1,
            participants=ParticipantSchema(min=2),
            knobs_schema={"graph": "TransitionGraph"},
            default_view_policy=NamedWindowedSummary.name,
            expectations=[
                Expectation(
                    name="turn_within",
                    on_violation="warn",
                    params={"seconds": 120},
                ),
                Expectation(
                    name="turn_within",
                    on_violation="auto_close",
                    params={"seconds": 600},
                ),
            ],
        )

    # ── ChannelAdapter Protocol ─────────────────────────────────────────

    def initial_state(self, metadata: ChannelMetadata) -> ParallelWorkflowState:
        graph_data = metadata.knobs.get("graph")
        if not isinstance(graph_data, dict):
            raise ProtocolError(
                "parallel_workflow requires knobs['graph'] as a dict — "
                "call TransitionGraph.to_dict() before passing"
            )
        try:
            graph = TransitionGraph.loads(graph_data)
        except WorkflowGraphError as exc:
            raise ProtocolError(f"invalid workflow graph: {exc}") from exc

        order = [
            p.agent_id for p in sorted(metadata.participants, key=lambda p: p.order)
        ]
        if graph.initial_speaker not in order:
            raise ProtocolError(
                f"parallel_workflow initial_speaker {graph.initial_speaker!r} "
                f"not in participants {order!r}"
            )

        initial_context = metadata.knobs.get("context_vars", {})
        if not isinstance(initial_context, dict):
            raise ProtocolError(
                "parallel_workflow knobs['context_vars'] must be a dict if provided"
            )

        return ParallelWorkflowState(
            participant_order=order,
            expected_next_speaker=graph.initial_speaker,
            pending_speakers=(),
            creator_id=metadata.creator_id,
            graph_data=graph_data,
            context_vars=dict(initial_context),
        )

    def validate_create(self, metadata: ChannelMetadata) -> None:
        if len(metadata.participants) < 2:
            raise ProtocolError(
                f"parallel_workflow requires at least 2 participants, got "
                f"{len(metadata.participants)}"
            )
        graph_data = metadata.knobs.get("graph")
        if not isinstance(graph_data, dict):
            raise ProtocolError("parallel_workflow requires knobs['graph'] as a dict")
        try:
            graph = TransitionGraph.loads(graph_data)
        except WorkflowGraphError as exc:
            raise ProtocolError(f"invalid workflow graph: {exc}") from exc
        order = {p.agent_id for p in metadata.participants}
        if graph.initial_speaker not in order:
            raise ProtocolError(
                f"parallel_workflow initial_speaker {graph.initial_speaker!r} "
                f"not in participants {sorted(order)!r}"
            )

    def validate_send(
        self,
        metadata: ChannelMetadata,
        envelope: Envelope,
        state: ParallelWorkflowState,
    ) -> None:
        if envelope.event_type == EV_CONTEXT_SET:
            participant_ids = {p.agent_id for p in metadata.participants}
            if envelope.sender_id not in participant_ids:
                raise ProtocolError(
                    f"parallel_workflow {metadata.channel_id!r} only accepts "
                    f"EV_CONTEXT_SET from participants, got {envelope.sender_id!r}"
                )
            return

        if not _is_substantive(envelope):
            return

        # Parallel mode: any pending speaker may post.
        if state.pending_speakers:
            if envelope.sender_id not in state.pending_speakers:
                raise ProtocolError(
                    f"parallel_workflow {metadata.channel_id!r} expects one of "
                    f"{list(state.pending_speakers)!r} to speak, got "
                    f"{envelope.sender_id!r}"
                )
            return

        # Scalar mode: gate on expected_next_speaker.
        if (
            state.expected_next_speaker
            and envelope.sender_id != state.expected_next_speaker
        ):
            raise ProtocolError(
                f"parallel_workflow {metadata.channel_id!r} expects "
                f"{state.expected_next_speaker!r} to speak, got "
                f"{envelope.sender_id!r}"
            )

    def fold(
        self,
        envelope: Envelope,
        state: ParallelWorkflowState,
    ) -> ParallelWorkflowState:
        # Context-only envelopes update context_vars and nothing else.
        if envelope.event_type == EV_CONTEXT_SET:
            new_vars = dict(state.context_vars)
            for key in envelope.event_data.get("delete", []) or []:
                new_vars.pop(key, None)
            new_vars.update(envelope.event_data.get("set", {}) or {})
            return replace(state, context_vars=new_vars)

        if not _is_substantive(envelope):
            return state

        # Apply context-updates carried on a packet BEFORE routing
        # selection so a same-packet ContextEquals rule can fire on the
        # new value.
        new_context = dict(state.context_vars)
        if envelope.event_type == EV_PACKET:
            updates = envelope.event_data.get("context_updates", {}) or {}
            for key in updates.get("delete", []) or []:
                new_context.pop(key, None)
            new_context.update(updates.get("set", {}) or {})

        # Build the post-envelope state with bookkeeping advanced.
        # Speaker / pending-set selection writes back to this object.
        new_state = ParallelWorkflowState(
            participant_order=state.participant_order,
            expected_next_speaker=state.expected_next_speaker,
            pending_speakers=state.pending_speakers,
            last_speaker_id=envelope.sender_id,
            last_envelope_id=envelope.envelope_id,
            turn_count=state.turn_count + 1,
            pending_close_reason="",
            creator_id=state.creator_id,
            graph_data=state.graph_data,
            context_vars=new_context,
        )

        # ── Parallel-mode branch ─────────────────────────────────────
        # If we entered this envelope mid-fan-out, the suppression rule
        # holds: any matching transition is *not* fired until the last
        # pending speaker has posted.
        if state.pending_speakers:
            remaining = tuple(
                aid for aid in state.pending_speakers if aid != envelope.sender_id
            )
            new_state.pending_speakers = remaining
            if remaining:
                # Still pending more speakers; stay in parallel mode.
                new_state.expected_next_speaker = None
                return new_state
            # Last pending speaker just posted — fall through to normal
            # transition selection on this envelope (the join fires).
            # pending_speakers is now empty.

        # ── Scalar-mode / parallel-just-joined branch ────────────────
        graph = TransitionGraph.loads(state.graph_data)

        # First, give pre-resolved routing (typed Handoff returns or
        # explicit Finish) precedence — same precedence as WorkflowAdapter.
        finish_reason: str | None = None
        pre_resolved: str | None = None
        if envelope.event_type == EV_PACKET:
            routing = envelope.event_data.get("routing", {}) or {}
            if routing.get("kind") == "finish":
                finish_reason = routing.get("reason") or "finished"
            elif routing.get("kind") == "handoff":
                pre_resolved = routing.get("target")

        if finish_reason is not None:
            new_state.expected_next_speaker = None
            new_state.pending_speakers = ()
            new_state.pending_close_reason = finish_reason
            return new_state

        if pre_resolved:
            new_state.expected_next_speaker = pre_resolved
            new_state.pending_speakers = ()
            new_state.pending_close_reason = ""
            return new_state

        # Walk transitions ourselves so we can inspect the matched target
        # type (the TransitionDecision alone doesn't tell us whether the
        # match was a parallel target).
        matched_target = None
        decision: TransitionDecision | None = None
        # ParallelWorkflowState intentionally reuses ag2's TransitionGraph
        # primitives, which are typed against the base WorkflowState; the
        # arg-type ignores below cover that deliberate substitution.
        for tr in sorted(graph.transitions, key=lambda t: t.priority):
            if tr.when.evaluate(state, envelope):  # type: ignore[arg-type]
                matched_target = tr.then
                decision = tr.then.resolve(state, envelope)  # type: ignore[arg-type]
                break
        if decision is None:
            matched_target = graph.default_target
            decision = graph.default_target.resolve(state, envelope)  # type: ignore[arg-type]

        if isinstance(matched_target, ParallelAgentsTarget):
            new_state.pending_speakers = tuple(sorted(matched_target.agent_ids))
            new_state.expected_next_speaker = None
            new_state.pending_close_reason = ""
            return new_state

        if isinstance(matched_target, DynamicParallelTarget):
            tool_args = (
                envelope.event_data.get("routing", {}).get("tool_args", {})
                if envelope.event_type == EV_PACKET
                else {}
            )
            nicknames = tool_args.get(matched_target.from_tool_arg, [])
            if not isinstance(nicknames, list):
                raise ProtocolError(
                    f"parallel_workflow: DynamicParallelTarget expected a list "
                    f"at routing.tool_args[{matched_target.from_tool_arg!r}], "
                    f"got {type(nicknames).__name__}"
                )
            resolved: list[str] = []
            for nick in nicknames:
                if nick not in matched_target.nickname_to_agent_id:
                    raise ProtocolError(
                        f"parallel_workflow: unknown nickname {nick!r} "
                        f"(known: {sorted(matched_target.nickname_to_agent_id)})"
                    )
                resolved.append(matched_target.nickname_to_agent_id[nick])
            new_state.pending_speakers = tuple(sorted(resolved))
            new_state.expected_next_speaker = None
            new_state.pending_close_reason = ""
            return new_state

        # Normal target — defer to its decision.
        new_state.expected_next_speaker = decision.next_speaker
        new_state.pending_speakers = ()
        new_state.pending_close_reason = decision.close_reason
        return new_state

    def on_accepted(
        self,
        metadata: ChannelMetadata,
        envelope: Envelope,
        state: ParallelWorkflowState,
    ) -> AdapterResult:
        if not _is_substantive(envelope):
            return AdapterResult()

        # If pending_speakers is non-empty, we're mid-fan-out — channel
        # stays open, no special action.
        if state.pending_speakers:
            return AdapterResult()

        # No pending speakers and no next speaker → channel is done.
        if state.expected_next_speaker is None:
            reason = state.pending_close_reason or "workflow_terminated"
            return AdapterResult(
                next_state=ChannelState.CLOSED,
                auto_close_reason=reason,
            )

        # max_turns guard.
        graph = TransitionGraph.loads(state.graph_data)
        if graph.max_turns is not None and state.turn_count >= graph.max_turns:
            return AdapterResult(
                next_state=ChannelState.CLOSED,
                auto_close_reason="max_turns",
            )
        return AdapterResult()

    def default_view_policy(
        self,
        metadata: ChannelMetadata,
        participant_id: str,
    ) -> ViewPolicy:
        # Wider window than WorkflowAdapter — parallel fan-out generates
        # several findings envelopes that the join speaker needs to see.
        recent_n = max(len(metadata.participants) * 3, 8)
        return NamedWindowedSummary(recent_n=recent_n)

    def extract_turn_input(self, envelope: Envelope) -> str | None:
        if envelope.event_type == EV_TEXT:
            text = envelope.event_data.get("text", "")
            return text if isinstance(text, str) else None
        if envelope.event_type == EV_PACKET:
            return _packet_turn_text(envelope) or None
        return None

    def build_round_envelope(
        self,
        metadata: ChannelMetadata,
        sender_id: str,
        reply,
        events: list,
        state: ParallelWorkflowState | None,
        hub,
    ) -> Envelope | None:
        """Build the round-end EV_PACKET envelope.

        Same shape as WorkflowAdapter's, with one important addition:
        we enrich ``routing`` with ``tool_args`` (the matched tool
        call's parsed arguments) so ``DynamicParallelTarget`` can read
        the fan-out set at fold time. This enrichment is the *only*
        difference vs. the base workflow's routing — and it lives on
        the WAL like everything else, preserving WAL replay.
        """
        graph: TransitionGraph | None = None
        if state is not None and state.graph_data:
            try:
                graph = TransitionGraph.loads(state.graph_data)
            except WorkflowGraphError:
                graph = None

        routing = _resolve_routing(events, graph, hub._name_to_id)

        # Enrich with tool_args when the routing matched a ToolCalled rule.
        # We walk the events to find the ToolCallEvent whose name matches
        # routing["tool"] (the same call _resolve_routing picked) and
        # attach its parsed arguments. This makes the args part of the
        # WAL envelope, so DynamicParallelTarget — and any future
        # arg-reading target — works under WAL replay.
        if routing.get("tool"):
            from autogen.beta.network.adapters.workflow import ToolCallEvent

            target_name = routing["tool"]
            for ev in events:
                if isinstance(ev, ToolCallEvent) and ev.name == target_name:
                    try:
                        routing["tool_args"] = dict(ev.serialized_arguments)
                    except Exception:
                        routing["tool_args"] = {}
                    break

        body = reply.body or ""

        if routing["kind"] == "text" and not body:
            return None

        return Envelope(
            channel_id=metadata.channel_id,
            sender_id=sender_id,
            audience=None,
            event_type=EV_PACKET,
            event_data={
                "routing": routing,
                "context_updates": {"set": {}, "delete": []},
                "body": body,
            },
        )

    def render_envelope(self, envelope: Envelope):
        if envelope.event_type == EV_PACKET:
            return _packet_text(envelope)
        return default_render_envelope(envelope)

    def tools_for(
        self,
        client,
        metadata: ChannelMetadata,
        state: ParallelWorkflowState,
        participant_id: str,
    ):
        # Workflow-shaped adapters expose no framework-provided LLM tools;
        # routing tools are user-authored (Handoff-returning, or matched
        # by ToolCalled rules).
        return []

    def build_text_envelope(
        self,
        channel_id: str,
        sender_id: str,
        text: str,
        *,
        audience: list[str] | None = None,
        causation_id: str | None = None,
    ) -> Envelope:
        return default_build_text_envelope(
            channel_id=channel_id,
            sender_id=sender_id,
            text=text,
            audience=audience,
            causation_id=causation_id,
        )

    def build_packet_envelope(
        self,
        channel_id: str,
        sender_id: str,
        body: str,
        *,
        handoff=None,
        context_set: dict | None = None,
        audience: list[str] | None = None,
        causation_id: str | None = None,
    ) -> Envelope:
        return default_build_packet_envelope(
            channel_id=channel_id,
            sender_id=sender_id,
            body=body,
            handoff=handoff,
            context_set=context_set,
            audience=audience,
            causation_id=causation_id,
        )


__all__ = [
    "ParallelWorkflowAdapter",
    "ParallelWorkflowState",
    "ParallelAgentsTarget",
    "DynamicParallelTarget",
    "PARALLEL_WORKFLOW_TYPE",
]
