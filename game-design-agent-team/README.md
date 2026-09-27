# AI Game Design Agent Team

- This project is collected and modified (with permission to include here) from the [awesome-llm-apps](https://github.com/Shubhamsaboo/awesome-llm-apps) repository. Check out the original code [here](https://github.com/Shubhamsaboo/awesome-llm-apps/tree/main/ai_agent_tutorials/ai_game_design_agent_team).
- By [Shubham](https://x.com/Saboo_Shubham_)

The AI Game Design Agent Team is a collaborative game design system that generates comprehensive game concepts through the coordination of multiple specialized AI agents, each focusing on different aspects of game design based on user inputs such as game type, target audience, art style, and technical requirements. It is built on AG2 (v1.1.0+) and its [network](https://docs.ag2.ai/docs/user-guide/network/pattern_cookbook/pattern_cookbook) feature: the team runs as a `workflow` channel whose `TransitionGraph.sequence([...])` pipeline hands the brief from agent to agent, and each agent's section is collected from the channel's write-ahead log.

## Description

**Agents and Workflow**
A user's game design requirements (game type, audience, art style, platforms, budget, and so on) are collected into a task brief and posted to a workflow channel. The AI Game Design Agent Team comprises the following specialized agents:

- 🎭 Story Agent:
  Focuses on narrative design and world-building. Responsible for character backgrounds, lore, plot arcs, and dialogue.
- 🎮 Gameplay Agent:
  Specializes in game mechanics, systems design, resource management, progression, balancing, and overall gameplay flow.
- 🎨 Visuals Agent:
  Manages the art direction (including style guidelines, character/environment art, UI/UX) and also addresses audio elements like sound effects and music.
- ⚙️ Tech Agent:
  Provides technical architecture and implementation guidance—engine selection, optimization strategies, networking requirements, platform constraints, and development roadmap.

When a user provides high-level game requirements (e.g., game type, setting, audience, visuals, platform), a non-LLM `HumanClient` posts the brief to a `workflow` channel, and the transition graph routes it through the pipeline: story agent → gameplay agent → visuals agent → tech agent, one turn each. Each agent sees the sections its teammates wrote before it, so the outputs combine into a cohesive game design proposal.

## AG2 Features

This project demonstrates the following AG2 features:

- [Workflow orchestration](https://docs.ag2.ai/docs/user-guide/network/pattern_cookbook/pattern_cookbook) — a `workflow` channel driven by a declarative `TransitionGraph` (the modern replacement for the classic swarm/`GroupChat` patterns)
- Multi-agent network primitives — `Hub`, `HumanClient` seeding, and replaying the conversation from the channel's write-ahead log

## TAGS

TAGS: game design, workflow orchestration, transition graph, multi-agent pipeline, ai-assisted creativity, game development, narrative design, gameplay mechanics

## Installation

1. Clone and navigate to the folder:

```bash
git clone https://github.com/ag2ai/build-with-ag2.git
cd build-with-ag2/game-design-agent-team
```

2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

The two dependencies are the ag2 (AG2) library and streamlit.

## Run the code

Before you start, get an API key — either from [OpenAI's platform](https://platform.openai.com/) or from [OpenRouter](https://openrouter.ai/).

Run the Streamlit app to start a web interface for the AI Game Design Agent Team.

```bash
streamlit run main.py
```

In the sidebar, pick your provider:

- **OpenAI** (default) — enter your OpenAI API key (uses `gpt-4o-mini`).
- **OpenRouter** — enter your OpenRouter API key and any `<vendor>/<model>` id (e.g. `openai/gpt-4o-mini`) to route through [OpenRouter](https://openrouter.ai/)'s OpenAI-compatible API.

Now you can interact with it through your browser, and click `Generate Game Concept` to receive a comprehensive design output from the specialized agents.

## Screenshots

![Game Design](./assets/game-design-page.png)

![Game Designed](./assets/game-designed.png)

## Contact

For more information or any questions, please refer to the documentation or reach out to us!

- Original Code (with permission to include here): https://github.com/Shubhamsaboo/awesome-llm-apps/tree/main/ai_agent_tutorials/ai_game_design_agent_team
- AG2 Documentation: https://docs.ag2.ai/docs/Home
- AG2 GitHub: https://github.com/ag2ai/ag2
- Discord: https://discord.gg/pAbnFJrkgZ
- X: https://x.com/ag2oss

## License

This project is also licensed under the Apache License 2.0 from the [awesome-llm-apps](https://github.com/Shubhamsaboo/awesome-llm-apps). See the [LICENSE](./LICENSE) for details.
