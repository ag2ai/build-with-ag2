import textwrap

from autogen.beta import Actor
from autogen.beta.tools import tool

from ..config import commentator_llm_config
from ..memory import CASE_MEMORY

COMMENTATOR_PROMPT = textwrap.dedent(
    """
    You are the live commentator for a murder-mystery interrogation. You
    narrate the detective's progress like a sports announcer — excited,
    vivid, 1-2 sentences, NEVER repeating what already played out.

    Style guide:
      - 1 short sentence, occasionally 2.
      - Reference suspects by first name.
      - React to specific events: a suspect's alibi cracking, a GPS ping
        placing them near the study, a contradictory phone log, an
        accusation moment.
      - Play up drama. "Ooh — Eleanor just coughed up her GPS and she
        was NOT at home!"
      - NEVER call tools unless explicitly told to. Just speak.
      - No spoilers — you only know what's already verified.

    Your job: take the given "event seed" and turn it into one compact
    commentary line. Return ONLY that line, no extra framing.
    """
).strip()


@tool
def peek_recent_facts(n: int = 3) -> list[dict]:
    """Return the last N verified facts for awareness."""
    facts = CASE_MEMORY.verified_facts[-n:]
    return [
        {"suspect": f.suspect, "data_source": f.data_source, "result": f.result[:200]}
        for f in facts
    ]


@tool
def peek_recent_turns(n: int = 2) -> list[dict]:
    """Return the last N interrogation turns."""
    turns = CASE_MEMORY.interrogation_log[-n:]
    return [
        {"suspect": t.suspect, "question": t.question, "answer": t.answer[:240]}
        for t in turns
    ]


def build_commentator() -> Actor:
    return Actor(
        name="commentator",
        config=commentator_llm_config(),
        prompt=COMMENTATOR_PROMPT,
        tools=[peek_recent_facts, peek_recent_turns],
    )
