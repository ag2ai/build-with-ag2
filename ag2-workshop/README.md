# AG2 Workshop: Building Agents with the AG2 Beta API

A hands-on workshop teaching you to build, orchestrate, test, and deploy AI agent systems using the **AG2 Beta API** (`autogen.beta`).

34 episodes across 7 groups, from a first agent through production deployment. Designed for YouTube (3–4 min per episode) and university programs (5 lectures).

> **Beta-only.** This workshop teaches the current, async-first AG2 Beta API exclusively. If you've used the classic AG2 API, Episode 33 maps every classic pattern to its beta equivalent.

## Prerequisites

- Python 3.12+ recommended
- Basic Python proficiency (including `async`/`await`)
- An OpenAI API key ([get one here](https://platform.openai.com/api-keys))
- Estimated API cost for all 34 episodes: **$5–8** (using `gpt-4.1-mini`)

## Getting Started

```bash
# Clone the repository
git clone https://github.com/ag2ai/build-with-ag2.git
cd build-with-ag2/ag2-workshop

# Set up your environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Install dependencies
pip install -r requirements.txt

# Start with Episode 1
jupyter notebook episodes/ep01_why_agents.ipynb
```

> **Note:** The `.env` file lives in `ag2-workshop/`. `python-dotenv` searches parent directories, so `load_dotenv()` in any episode notebook will find it.

## The Beta API in one minute

```python
from autogen.beta import Agent
from autogen.beta.config import OpenAIConfig

agent = Agent(
    "assistant",
    prompt="You are a helpful assistant.",
    config=OpenAIConfig(model="gpt-4.1-mini"),
)

reply = await agent.ask("Hello!")
print(reply.body)
```

Everything else — tools, middleware, structured output, multi-agent networking — plugs into that same `Agent` constructor.

## Episodes

### Group 1 — Fundamentals (Episodes 1–5)

| # | Title | What You Build |
|---|-------|----------------|
| 1 | [Why Agents?](episodes/ep01_why_agents.ipynb) | See agents in action (demo) |
| 2 | [Your First Agent](episodes/ep02_first_agent.ipynb) | A single agent and the `ask()` loop |
| 3 | [Tools](episodes/ep03_tools.ipynb) | An agent that calls functions you write |
| 4 | [Task & Sub-Agent Delegation](episodes/ep04_task_delegation.ipynb) | A coordinator that delegates to specialists |
| 5 | [LiveAgent: Real-Time Voice](episodes/ep05_live_agent.ipynb) | A voice assistant you can talk to |

### Group 2 — Agent Harness (Episodes 6–9)

| # | Title | What You Build |
|---|-------|----------------|
| 6 | Anatomy of an Agent | A tour of every constructor slot |
| 7 | Middleware | Request/response interceptors |
| 8 | Assembly & Policies | Control what enters each prompt |
| 9 | Structured Output | Typed Pydantic responses |

### Group 3 — Multi-Agent Networking (Episodes 10–15)

| # | Title | What You Build |
|---|-------|----------------|
| 10 | The Hub | Register autonomous agents on a Hub |
| 11 | Consulting Adapter | Strict one-question / one-answer channels |
| 12 | Conversation Adapter | Free-form two-party dialogue |
| 13 | Discussion Adapter | Round-robin N-party debate |
| 14 | Workflow & TransitionGraph | Declarative orchestration |
| 15 | Coordinator Pattern | LLM-driven routing with explicit control |

### Group 4 — Choosing the Right Pattern (Episode 16)

| # | Title | What You Build |
|---|-------|----------------|
| 16 | Choosing the Right Pattern | A decision framework for all patterns |

### Group 5 — Applications (Episodes 17–23)

| # | Title | What You Build |
|---|-------|----------------|
| 17 | Customer Service System | A triage-and-delegate support app |
| 18 | Research with Feedback Loop | Parallel research + writer/reviewer loop |
| 19 | Knowledge Base | RAG with `KnowledgeConfig` |
| 20 | Web Browsing | An agent that searches and fetches the web |
| 21 | Agent UI (AG-UI) | A streaming chat UI |
| 22 | Plain HTML Frontend | A framework-free HTML + `fetch` frontend |
| 23 | MCP Tools | Connect to Model Context Protocol servers |

### Group 6 — Production (Episodes 24–29)

| # | Title | What You Build |
|---|-------|----------------|
| 24 | Telemetry | Event streams + OpenTelemetry spans |
| 25 | Observers | Safety hooks that raise alerts |
| 26 | Security | Approval gates and audit trails |
| 27 | Testing | Deterministic tests with `TestConfig` |
| 28 | Cost Optimization | Budgets, monitoring, and compaction |
| 29 | Deployment | Ship via AG-UI and the A2A protocol |

### Group 7 — Advanced (Episodes 30–34)

| # | Title | What You Build |
|---|-------|----------------|
| 30 | Redundancy & Voting | Parallel workers with consensus |
| 31 | Reasoning | Structured chain-of-thought |
| 32 | Events | The event system in depth |
| 33 | Migration Guide | Classic AG2 / AutoGen / LangChain → Beta |
| 34 | What's Next | Where the ecosystem is heading |

## Notebook Structure

Each episode notebook has two parts:

- **Core content** — Essential concepts plus one hands-on build. This is what the YouTube episodes cover.
- **Additional content** — Deeper dives, alternative approaches, and design rationale. For university lectures and self-study.

## For Instructors

This workshop maps to 5 university lectures:

| Lecture | Episodes | Focus |
|---------|----------|-------|
| 1. Foundations | 1–9 | Agents, tools, delegation, the harness |
| 2. Multi-Agent Systems | 10–16 | The Hub, channel adapters, choosing patterns |
| 3. Applications | 17–23 | Real apps, RAG, web, UIs, MCP |
| 4. Production | 24–29 | Telemetry, observers, security, testing, cost, deploy |
| 5. Advanced | 30–34 | Redundancy, reasoning, events, migration, future |

## Troubleshooting

See [episodes/troubleshooting.md](episodes/troubleshooting.md) for common issues and fixes.

## Resources

- [AG2 Documentation](https://docs.ag2.ai)
- [AG2 Playground](https://playground.ag2.ai) — runnable beta walkthroughs; many episodes cross-reference specific demos
- [AG2 GitHub](https://github.com/ag2ai/ag2)
- [AG2 Discord](https://discord.gg/sNGSwQME3x)
- [More Examples](https://github.com/ag2ai/build-with-ag2)
