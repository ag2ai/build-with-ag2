# Tech Decision Debate

A structured 5-round technical debate between AG2 agents — terminal-only, no frontend required.

Three agents debate any tech decision: **Architect** argues for option A, **Challenger** argues for option B, and **Judge** delivers a structured verdict.

## AG2 Features

- [GroupChat](https://docs.ag2.ai/latest/docs/user-guide/advanced-concepts/orchestration/group-chat/introduction/) with **custom speaker selection**
- [AssistantAgent](https://docs.ag2.ai/latest/docs/api-reference/autogen/AssistantAgent/)
- [UserProxyAgent](https://docs.ag2.ai/latest/docs/api-reference/autogen/UserProxyAgent/)

## Workshop

This project is referenced in the [AG2 Workshop](../ag2-workshop/):
- [Episode 5: Team of Agents: Taking Turns](../ag2-workshop/episodes/ep05_round_robin.ipynb)

## Tags

`groupchat` `debate` `decision-making` `multi-agent` `terminal`

## Overview

The script parses your question to identify the two options, then runs a deterministic 4-round debate followed by a structured Judge verdict. All output goes to stdout — no web server, no frontend.

## Custom Speaker Selection

> **Note for learners:** If you're just getting started with AG2, check out the built-in patterns first (`round_robin`, `auto`, transition graphs). Custom speaker selection is an advanced escape hatch — use it when the built-ins don't fit.

AG2's `GroupChat` supports several built-in speaker selection strategies: `auto` (LLM picks next speaker), `round_robin`, `random`, and `manual`. You can also pass `allowed_or_disallowed_speaker_transitions` to define a graph of permitted agent handoffs.

This example uses none of those — instead it passes a **custom function** to `speaker_selection_method`. This is the right choice when you need strict round-by-round control that a transition graph alone can't express. In a debate, the Judge must appear on exactly round 5, not whenever the Challenger decides to hand off.

```python
def debate_flow(last_speaker, groupchat):
    # messages[0] is the moderator opener, so agent turns start at index 1
    turn = len(groupchat.messages) - 1  # 0-indexed agent turns

    if turn == 0:   return architect   # Round 1: open
    elif turn == 1: return challenger  # Round 2: counter
    elif turn == 2: return architect   # Round 3: rebuttal
    elif turn == 3: return challenger  # Round 4: final push
    elif turn == 4: return judge       # Round 5: verdict
    else:           return moderator   # end-of-debate signal

groupchat = GroupChat(
    agents=[moderator, architect, challenger, judge],
    messages=[],
    max_round=6,
    speaker_selection_method=debate_flow,  # custom function instead of "auto" / "round_robin"
)
```

The function receives `last_speaker` and the full `groupchat` object (including message history) and must return an `Agent` from the group. Returning `None` terminates the chat early.

## Debate Structure

| Round | Speaker    | Role                          |
| ----- | ---------- | ----------------------------- |
| 1     | Architect  | Opens: argues for option A    |
| 2     | Challenger | Counters: argues for option B |
| 3     | Architect  | Rebuttal                      |
| 4     | Challenger | Final push                    |
| 5     | Judge      | Structured verdict            |

## Installation

Requires Python 3.9+.

### Using pip

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Set up environment variables:

   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

3. Run a debate:

   ```bash
   python main.py "REST API vs GraphQL for a mobile app with complex nested data"
   ```

   Or run interactively:

   ```bash
   python main.py
   # Enter your tech decision question: PostgreSQL vs MongoDB for user data at scale
   ```

## Example Topics

```bash
python main.py "Kubernetes vs serverless for a startup with unpredictable traffic"
python main.py "TypeScript vs Python for a data pipeline with ML components"
python main.py "Microservices vs monolith for a team of 5 engineers"
python main.py "Redis vs Memcached for session storage at 10k req/s"
```

## Sample Output

```
═══════════════════════════════════════════════════
  TECH DECISION DEBATE
  PostgreSQL vs MongoDB for user data at scale
═══════════════════════════════════════════════════

[Round 1 — Architect defends PostgreSQL]
PostgreSQL's ACID guarantees make it the clear choice for user data...

───────────────────────────────────────────────────
[Round 2 — Challenger defends MongoDB]
While ACID is valuable, MongoDB's horizontal scaling...

───────────────────────────────────────────────────
[Round 3 — Architect rebuts]
MongoDB's eventual consistency is a liability when...

───────────────────────────────────────────────────
[Round 4 — Challenger final push]
The real question is operational complexity at scale...

═══════════════════════════════════════════════════
  VERDICT
═══════════════════════════════════════════════════
VERDICT: PostgreSQL

WINNER_REASON:
For user data requiring consistency and complex queries...

KEY_TRADE_OFFS:
- ACID vs horizontal scale-out
- Schema rigidity vs document flexibility
- Operational complexity vs query expressiveness

CONFIDENCE: High
CONFIDENCE_REASON: User data integrity requirements strongly favour relational semantics.
```

## Requirements

- Python 3.10+
- `ag2[openai]>=0.11.0`
- OpenAI API key (`gpt-4o-mini` by default)
