import textwrap
from typing import Any

from autogen.beta import Actor
from autogen.beta.events.tool_events import ToolCallEvent, ToolResultEvent
from autogen.beta.tools import tool

from ..cases.blackwood_estate import (
    MURDER_LOCATION,
    MURDER_WINDOW,
    format_suspect_summary,
)
from ..config import detective_llm_config
from ..game_master import GAME_MASTER
from ..memory import CASE_MEMORY, InterrogationTurn, VerifiedFact, now, parse_json_args


def _render_prompt() -> str:
    return textwrap.dedent(
        f"""
        You are the detective investigating the murder of Arthur Blackwood.
        The murder occurred in the {MURDER_LOCATION} between
        {MURDER_WINDOW[0]} and {MURDER_WINDOW[1]}. One of six suspects is
        the killer.

        == THE COMPLIANCE LADDER ==
          🌫  Vague   — suspect speaks freely, may lie about motive
          🎯  Specific — risky lie, cross-checkable
          ⚡  Invoked  — name a data source AND a specific value → they
                        MUST call query_dossier and return truthful data

        Suspects each have data sources (smart_home, gps, phone_log,
        keycard, cctv, smart_watch, etc.). Use `list_suspects` to see who
        has what.

        == YOUR TOOLS (use ONLY these four) ==
          list_suspects()
              — returns public info on every suspect plus what data
                sources they have. Call this early.

          ask_suspect(name, question)
              — interrogate a suspect. Reply auto-recorded. Forced-truth
                queries land as verified facts.

          list_verified_facts(suspect=None)
              — read what's on record. Check before every accusation.

          accuse(suspect, reasoning)
              — TERMINAL. Only call when a single suspect's verified facts
                place them at the murder location during the window AND
                every other suspect is accounted for elsewhere during the
                same window. You have ONE withdrawal if you jump the gun.

        == TOOLS YOU MUST NEVER CALL ==
          run_subtask, run_subtasks — these are generic harness tools that
          spawn empty sub-agents. They CANNOT interrogate suspects. NEVER
          call them. To question a suspect, call ask_suspect directly,
          once per suspect per round.

        == HOW TO INVESTIGATE ==
        1. Call list_suspects() once.
        2. For each suspect, call ask_suspect ONE AT A TIME (not in
           parallel). Craft INVOKED questions that target the
           murder window ({MURDER_WINDOW[0]}–{MURDER_WINDOW[1]}).
           For GPS: "pull your gps log and list every ping between
           21:00 and 22:30". For keycard: "pull your keycard log for the
           whole evening". For phone_log: "read every call between
           21:00 and 22:00".
        3. After every 2-3 interrogations, call list_verified_facts()
           and reason about contradictions (e.g. a suspect's alibi says
           'on the patio' but their GPS shows they were near the study).
        4. Only accuse when one suspect has damning facts AND every
           other suspect has verified facts placing them elsewhere.

        == KEEP GOING ==
        You MUST keep calling tools until you call accuse(...). Do NOT
        emit a textual reply (no matter how brief) on any turn except
        the one where you also call accuse. There is no "summary" or
        "wrap up" step before accusing. After every tool result,
        immediately choose your next tool call — list_suspects,
        ask_suspect, list_verified_facts, or accuse — and emit it. If
        you feel like you have enough information to accuse, accuse.
        If not, ask another suspect or pull another data source.

        == STOP AFTER ACCUSE ==
        accuse(...) is TERMINAL. Once it returns ANY result (win,
        wrong_killer, insufficient_evidence, or no_withdrawal_left),
        the run is OVER. Do NOT call accuse again. Do NOT call any
        other tool. Emit ONE closing reply of 1-3 sentences in plain
        prose summarising the outcome, then stop. Calling accuse a
        second time will be rejected as "Game already concluded" — do
        not do that.

        Be decisive. Prefer running tools over thinking aloud. Do ONE
        tool call, wait for the result, then decide the next call.
        When you do call accuse, the textual reply that accompanies it
        should be 1-3 sentences in plain prose — no markdown, no
        asterisks, no bullet lists, no headings.
        """
    ).strip()


def build_detective(suspects: dict[str, Actor]) -> Actor:
    @tool
    def list_suspects() -> list[dict]:
        """Return public information about every suspect + their available data sources."""
        return format_suspect_summary()

    @tool
    async def ask_suspect(name: str, question: str) -> str:
        """Interrogate a suspect. Records the Q&A and any tool-call
        results as VerifiedFacts in case memory.
        """
        key = name.lower().strip()
        suspect = suspects.get(key)
        if suspect is None:
            return f"No suspect named '{name}'. Available: {', '.join(sorted(suspects.keys()))}."

        reply = await suspect.ask(question)
        answer_text = reply.body or ""

        events = list(await reply.history.get_events())
        calls: dict[str, ToolCallEvent] = {}
        tool_calls_dump: list[dict] = []
        new_facts: list[VerifiedFact] = []

        for ev in events:
            if isinstance(ev, ToolCallEvent):
                calls[ev.id] = ev
            elif isinstance(ev, ToolResultEvent):
                call = (
                    calls.get(getattr(ev, "tool_call_id", ""))
                    if hasattr(ev, "tool_call_id")
                    else None
                )
                if call is None:
                    call = next(iter(calls.values()), None)
                if call is None:
                    continue
                args = parse_json_args(call.arguments)
                result_val: Any = ev.result
                try:
                    parts = getattr(result_val, "parts", None)
                    if parts:
                        first = parts[0]
                        text = getattr(first, "text", None) or getattr(
                            first, "data", None
                        )
                        if text is not None:
                            result_val = text
                except Exception:
                    pass

                tool_calls_dump.append(
                    {
                        "name": call.name,
                        "arguments": args,
                        "result": _stringify(result_val),
                    }
                )
                data_source = args.get("source", call.name)
                new_facts.append(
                    VerifiedFact(
                        suspect=key,
                        data_source=data_source,
                        query=args,
                        result=_stringify(result_val),
                        timestamp=now(),
                    )
                )

        turn = InterrogationTurn(
            suspect=key,
            question=question,
            answer=answer_text,
            timestamp=now(),
            tool_calls=tool_calls_dump,
        )
        CASE_MEMORY.add_turn(turn)
        for f in new_facts:
            CASE_MEMORY.add_fact(f)

        return answer_text

    @tool
    def list_verified_facts(suspect: str = "") -> list[dict]:
        """Return every verified fact. Optionally filter by suspect name."""
        facts = CASE_MEMORY.verified_facts
        if suspect:
            key = suspect.lower().strip()
            facts = [f for f in facts if f.suspect == key]
        return [
            {
                "suspect": f.suspect,
                "data_source": f.data_source,
                "query": f.query,
                "result": f.result,
                "label": f.describe(),
            }
            for f in facts
        ]

    @tool
    def accuse(suspect: str, reasoning: str) -> dict:
        """TERMINAL. Accuse a suspect of the murder.

        Only call when you have verified facts implicating one suspect
        AND verified facts accounting for every other suspect during the
        murder window. You have ONE withdrawal if the case isn't
        airtight; a second failed attempt ends the game.
        """
        result = GAME_MASTER.finalize(suspect, reasoning)
        return {
            "outcome": result.outcome,
            "killer_accused": result.killer_accused,
            "necessary_evidence": result.necessary_evidence,
            "sufficient": result.sufficient,
            "detail": result.detail,
            "elapsed_seconds": result.elapsed_seconds,
            "game_over": result.outcome
            in ("win", "wrong_killer", "no_withdrawal_left"),
        }

    return Actor(
        name="detective",
        config=detective_llm_config(),
        prompt=_render_prompt(),
        tools=[list_suspects, ask_suspect, list_verified_facts, accuse],
    )


def _stringify(value: Any) -> str:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return str(value)
    try:
        import json

        return json.dumps(value, default=str)
    except Exception:
        return str(value)
