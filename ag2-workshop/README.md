# AG2 Workshop: Building Multi-Agent Systems

A hands-on workshop teaching you to build, orchestrate, test, and deploy multi-agent AI systems using AG2.

23 episodes covering fundamentals through production deployment. Designed for YouTube (3-4 min per episode) and university programs (5 lectures).

## Prerequisites

- Python 3.12+ recommended (3.12+ required for Episode 15 MCP)
- Basic Python proficiency
- An OpenAI API key ([get one here](https://platform.openai.com/api-keys))
- Estimated API cost for all 23 episodes: **$3-5** (using gpt-4o-mini)

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

> **Note:** The `.env` file lives in `ag2-workshop/` (one level above `episodes/`). Python-dotenv searches parent directories automatically, so `load_dotenv()` in notebooks will find it.

## Episodes

### Basics (Episodes 1-4)

| # | Title | What You Build |
|---|-------|---------------|
| 1 | [Why Multi-Agent Systems?](episodes/ep01_why_agents.ipynb) | See agents in action (demo) |
| 2 | [Your First Agent](episodes/ep02_first_agent.ipynb) | A single AI agent that chats |
| 3 | [Give Your Agent Tools](episodes/ep03_tools.ipynb) | An agent that checks the weather |
| 4 | [Two Agents Working Together](episodes/ep04_two_agents.ipynb) | Researcher + reviewer collaboration |

### Patterns (Episodes 5-9)

| # | Title | What You Build |
|---|-------|---------------|
| 5 | [Team of Agents: Taking Turns](episodes/ep05_round_robin.ipynb) | 3-agent debate with round-robin |
| 6 | [Team of Agents: Smart Speaker Selection](episodes/ep06_auto_pattern.ipynb) | LLM-driven speaker selection |
| 7 | [Routing Agents: Conditions, Handoffs & Escalation](episodes/ep07_handoffs.ipynb) | Customer support triage system |
| 8 | [Pipelines & Hierarchies](episodes/ep08_pipelines.ipynb) | Document pipeline + research hierarchy |
| 9 | [Choosing the Right Pattern](episodes/ep09_choosing_patterns.ipynb) | Decision framework (theory) |

### Applications (Episodes 10-15)

| # | Title | What You Build |
|---|-------|---------------|
| 10 | [Build a Customer Service System](episodes/ep10_real_app.ipynb) | Complete multi-agent app (guided) |
| 11 | [Build a Research Assistant](episodes/ep11_research.ipynb) | 3-agent research pipeline |
| 12 | [Give Your Agents a Knowledge Base](episodes/ep12_knowledge_base.ipynb) | RAG-powered document Q&A |
| 13 | [Web Browsing Agents](episodes/ep13_web_browsing.ipynb) | Agent that fetches web content |
| 14 | [Give Your Agent a UI](episodes/ep14_agent_ui.ipynb) | Streamlit + AG-UI frontend |
| 15 | [Connect to External Tools (MCP)](episodes/ep15_mcp.ipynb) | MCP server integration |

### Production (Episodes 16-20)

| # | Title | What You Build |
|---|-------|---------------|
| 16 | [See What Your Agents Are Doing](episodes/ep16_observability.ipynb) | Logging + OpenTelemetry tracing |
| 17 | [Security & Safe Code Execution](episodes/ep17_security.ipynb) | Input validation + approval gates |
| 18 | [Testing Agents](episodes/ep18_testing.ipynb) | Unit tests + evaluation framework |
| 19 | [Control Your Agent Costs](episodes/ep19_cost_optimization.ipynb) | Token tracking + model tiering |
| 20 | [Deploy to Production (GCP)](episodes/ep20_deploy.ipynb) | Docker + Cloud Run deployment |

### Specialized Patterns (Episodes 21-22)

| # | Title | What You Build |
|---|-------|---------------|
| 21 | [Multiple Agents, One Task: Redundancy & Nested Chats](episodes/ep21_redundant.ipynb) | Parallel agents + evaluator |
| 22 | [Make Agents Think Harder: Tree of Thoughts](episodes/ep22_reasoning.ipynb) | ReasoningAgent with search strategies |

### Closing

| # | Title | What You Learn |
|---|-------|---------------|
| 23 | [What's Next](episodes/ep23_whats_next.ipynb) | AG2 Beta, ecosystem, future directions |

## Notebook Structure

Each episode notebook has two sections:

- **Core content** — Essential concepts + one hands-on build. This is what YouTube episodes cover.
- **Additional content** — Deeper dives, alternative approaches, design rationale. For university lectures and self-study.

## For Instructors

This workshop maps to 5 university lectures:

| Lecture | Episodes | Focus |
|---------|----------|-------|
| 1. Foundations | 1-4 | Agent basics, tools, two-agent systems |
| 2. Orchestration | 5-9 | Patterns, handoffs, decision framework |
| 3. Applications | 10-15 | Real apps, RAG, web, UI, MCP |
| 4. Production | 16-20 | Observability, security, testing, costs, deployment |
| 5. Advanced | 21-23 | Specialized patterns, reasoning, future |

## Troubleshooting

See [episodes/troubleshooting.md](episodes/troubleshooting.md) for common issues and fixes.

## Resources

- [AG2 Documentation](https://docs.ag2.ai)
- [AG2 Playground](https://playground.ag2.ai) — try patterns interactively, no setup needed
- [AG2 GitHub](https://github.com/ag2ai/ag2)
- [AG2 Discord](https://discord.gg/sNGSwQME3x)
- [More Examples](https://github.com/ag2ai/build-with-ag2)
