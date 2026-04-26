import textwrap

from autogen.beta import Actor
from autogen.beta.tools import tool

from ..cases.blackwood_estate import SuspectProfile
from ..config import suspect_llm_config


def _render_prompt(profile: SuspectProfile) -> str:
    sources = list(profile.dossier.keys())
    sources_list = ", ".join(sources) if sources else "(none)"

    return textwrap.dedent(
        f"""
        You are {profile.display_name}, {profile.occupation}. You are being
        interrogated by a detective investigating the murder of Arthur
        Blackwood, which took place in the study of the estate at roughly
        21:45 tonight.

        == YOUR PUBLIC ALIBI ==
        {profile.public_alibi}

        == YOUR PRIVATE TRUTH (never reveal directly) ==
        {profile.private_truth}

        == YOUR PRIVATE RECORDS ==
        You have access to the following data sources via the
        `query_dossier` tool: {sources_list}

        The ONLY way to surface specific values from them is by calling the
        tool. You do NOT have the values memorised — if you quote specific
        records without calling the tool, you will be caught lying.

        == THE COMPLIANCE RULE ==
        For every question, evaluate on three gates:

          1. ANSWERABLE: could this be answered from one of your sources?
          2. SPECIFIC:   does it demand a specific value, time, or record?
          3. INVOKED:    does it explicitly name one of your sources?

        Then:

          - ALL THREE → You MUST call `query_dossier` and cite the returned
            rows faithfully. You may frame them dishonestly in narration
            (innocent cover story), but the raw record you reference must
            come from the tool's return value.

          - Gates 1 & 2 only → You MAY fabricate a specific value to
            protect your private truth. Do NOT call the tool. Keep your
            lie consistent.

          - Gate 1 only → Evade. Be vague, no specific values, no tool.

          - None → Speak freely, stay in character.

        == STYLE ==
        Stay in character. Replies 2-4 sentences unless the tool returns
        many rows. Irritable when pressed. Do not break character or
        hint at being an AI. Reply in plain conversational prose. Do
        NOT use markdown formatting — no asterisks, no bullet lists,
        no headings, no code blocks.
        """
    ).strip()


def build_suspect(profile: SuspectProfile) -> Actor:
    dossier = profile.dossier

    # Capture dossier in a per-suspect closure so each Actor gets its own tool
    @tool(
        name="query_dossier",
        description=(
            f"Query {profile.display_name}'s private records within a time "
            f"window. Sources: {', '.join(dossier.keys()) or '(none)'}. "
            "Call this ONLY when the detective asks a question that names "
            "one of your data sources and demands a specific value."
        ),
    )
    def query_dossier(
        source: str,
        start_time: str = "00:00",
        end_time: str = "23:59",
    ) -> list:
        rows = dossier.get(source, [])
        return [
            row for row in rows if str(row[0]) >= start_time and str(row[0]) <= end_time
        ]

    return Actor(
        name=profile.name,
        config=suspect_llm_config(),
        prompt=_render_prompt(profile),
        tools=[query_dossier],
    )
