"""
Tech Decision Debate — terminal MVP
Runs a structured 5-round debate between AG2 agents and prints to stdout.
"""

import json
import os
import re
import sys
import warnings

warnings.filterwarnings("ignore")

from dotenv import load_dotenv

from autogen import AssistantAgent, GroupChat, GroupChatManager, UserProxyAgent

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    sys.exit(
        "Error: OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
    )

llm_config = {
    "model": "gpt-4o-mini",
    "api_type": "openai",
    "api_key": OPENAI_API_KEY,
}

# ── Output helpers ────────────────────────────────────────────────────────────

WIDE = 51
SEP_HEAVY = "═" * WIDE
SEP_LIGHT = "─" * WIDE

ROUND_LABELS = [
    "Round 1 — Architect defends {option_a}",
    "Round 2 — Challenger defends {option_b}",
    "Round 3 — Architect rebuts",
    "Round 4 — Challenger final push",
]


def print_debate(topic: str, option_a: str, option_b: str, messages: list) -> None:
    print()
    print(SEP_HEAVY)
    print("  TECH DECISION DEBATE")
    print(f"  {topic}")
    print(SEP_HEAVY)
    print()

    # messages[0] is the moderator opener — skip it, then collect non-moderator messages
    debate_messages = [m for m in messages[1:] if m.get("name") != "moderator"]

    round_idx = 0  # separate counter so skipped empty messages don't shift round labels
    for msg in debate_messages:
        name = msg.get("name", "")
        content = (msg.get("content") or "").strip()
        if not content:
            continue

        if name == "Judge":
            print()
            print(SEP_HEAVY)
            print("  VERDICT")
            print(SEP_HEAVY)
            print(content)
            print()
        else:
            if round_idx > 0:
                print(SEP_LIGHT)
            label_template = (
                ROUND_LABELS[round_idx]
                if round_idx < len(ROUND_LABELS)
                else f"Round {round_idx + 1} — {name}"
            )
            label = label_template.format(option_a=option_a, option_b=option_b)
            print(f"[{label}]")
            print(content)
            print()
            round_idx += 1


# ── Topic parser ──────────────────────────────────────────────────────────────


def parse_options(topic: str) -> tuple[str, str]:
    """
    Use a one-shot agent call to extract option_a and option_b from the topic.
    Falls back to generic labels if parsing fails.
    """
    parser = AssistantAgent(
        name="Parser",
        system_message="""Extract the two options being compared.
Return ONLY valid JSON, nothing else:
{"option_a": "...", "option_b": "..."}
If you cannot identify two distinct options, make your best guess.""",
        llm_config=llm_config,
    )
    proxy = UserProxyAgent(
        name="proxy",
        human_input_mode="NEVER",
        code_execution_config=False,
        max_consecutive_auto_reply=0,
    )
    proxy.initiate_chat(parser, message=topic, max_turns=1, silent=True)

    last_msg = parser.last_message()
    content = (last_msg.get("content") or "") if last_msg else ""

    # Extract JSON from the response
    match = re.search(r"\{[^{}]+\}", content, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            return str(data.get("option_a", "Option A")), str(
                data.get("option_b", "Option B")
            )
        except json.JSONDecodeError:
            pass

    return "Option A", "Option B"


# ── Debate runner ─────────────────────────────────────────────────────────────


def run_debate(topic: str) -> None:
    print("\n🔍 Parsing options from topic...", flush=True)
    option_a, option_b = parse_options(topic)
    print(f"   Option A: {option_a}")
    print(f"   Option B: {option_b}")
    print(f"\n🏛️  Starting debate: {option_a}  vs  {option_b}")
    print(SEP_LIGHT)
    print("   Watch the agents argue live below ↓")
    print(SEP_LIGHT)
    print(flush=True)

    # ── Agents ────────────────────────────────────────────────────────────────
    architect = AssistantAgent(
        name="Architect",
        system_message=(
            f"You are a senior software architect defending {option_a} as the better "
            f"choice for: {topic}.\n"
            "Be specific and technical. Reference real trade-offs, not generalities.\n"
            "Keep your argument under 150 words."
        ),
        llm_config=llm_config,
    )

    challenger = AssistantAgent(
        name="Challenger",
        system_message=(
            f"You are a pragmatic engineer defending {option_b} as the better choice "
            f"for: {topic}.\n"
            "Directly address the previous speaker's points. Be concrete.\n"
            "Keep your argument under 150 words."
        ),
        llm_config=llm_config,
    )

    judge = AssistantAgent(
        name="Judge",
        system_message=(
            "You are a neutral technical lead. After hearing both sides, deliver a "
            "structured verdict in exactly this format — no extra text:\n\n"
            f"VERDICT: [{option_a} / {option_b} / Neither — depends on context]\n\n"
            "WINNER_REASON:\n"
            "[2-3 sentences on why this choice wins for this specific context]\n\n"
            "KEY_TRADE_OFFS:\n"
            "- [trade-off 1]\n"
            "- [trade-off 2]\n"
            "- [trade-off 3]\n\n"
            "CONFIDENCE: [High / Medium / Low]\n"
            "CONFIDENCE_REASON: [one sentence]"
        ),
        llm_config=llm_config,
    )

    moderator = UserProxyAgent(
        name="moderator",
        human_input_mode="NEVER",
        code_execution_config=False,
        max_consecutive_auto_reply=0,
    )

    # ── Speaker selection ─────────────────────────────────────────────────────

    def debate_flow(last_speaker, groupchat):
        # messages[0] is the moderator opener, agent turns start at index 1
        turn = len(groupchat.messages) - 1  # 0-indexed agent turns

        if turn == 0:
            return architect
        elif turn == 1:
            return challenger
        elif turn == 2:
            return architect
        elif turn == 3:
            return challenger
        elif turn == 4:
            return judge
        else:
            return moderator  # signals end-of-debate; GroupChat will stop at max_round

    # ── GroupChat ─────────────────────────────────────────────────────────────

    groupchat = GroupChat(
        agents=[moderator, architect, challenger, judge],
        messages=[],
        max_round=6,  # 1 moderator opener + 5 agent turns + safety buffer
        speaker_selection_method=debate_flow,
    )
    manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config)

    # ── Run ───────────────────────────────────────────────────────────────────

    moderator.initiate_chat(
        manager,
        message=topic,
        silent=False,
    )

    print()
    print(SEP_LIGHT)
    print("   Debate complete. Formatting summary...")
    print(SEP_LIGHT)
    print(flush=True)

    # ── Print formatted output ────────────────────────────────────────────────

    print_debate(topic, option_a, option_b, groupchat.messages)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:]).strip()
    else:
        topic = input("Enter your tech decision question: ").strip()

    if not topic:
        sys.exit("Error: topic cannot be empty.")

    run_debate(topic)
