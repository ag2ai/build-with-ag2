# 🌟 Build with AG2

> Are you building with AG2? Add your project to the list by [submitting code](./project-template/) through pull requests or [add a link](./external_repo_guide.md) to your own repository!

A curated collection of awesome agentic applications built with [AG2](https://github.com/ag2ai/ag2).

- 💡 Practical implementations demonstrating AI agents in action - from custom support to smart email management systems

- 🔥 Cutting-edge AI agent applications that seamlessly integrate models from OpenAI, Anthropic, Gemini, and open-source providers, and a diverse range of tools

- 🎓 Production-ready, extensively documented agentic projects that help you contribute to the thriving AI agent ecosystem

## 🎓 AG2 Workshop: 23-Episode Course

New to AG2? The [AG2 Workshop](ag2-workshop/) takes you from first agent to production deployment in 23 hands-on episodes.

1. **Learn the patterns** → [Agent Pattern Cookbook](tutorial/agent_pattern_cookbook/) — 13 runnable examples from simple two-agent chat to hierarchical multi-agent systems.
2. **See real apps** → Browse the [Featured Agentic Apps](#-featured-agentic-apps) section below for complete, documented projects.
3. **Connect external services** → Explore [Arcade SDK Examples](#-arcade-sdk-examples) to integrate OAuth-protected APIs like Gmail and Linear.
4. **Add a UI** → Explore [AG-UI Examples](#%EF%B8%8F-ag-ui-examples) to connect your agents to a browser frontend.
5. **Deep dive** → Work through the [7-module workshop](ag2-workshop/) for a comprehensive hands-on course.
6. **Go to production** → Use the [GCP Agent Starter Pack](gcp-agent-starter-pack/templates/ag2/) to deploy your agent to Google's Cloud Run with CI/CD and observability.
| Section | Episodes | What You Build |
|---------|----------|---------------|
| **Basics** | 1-4 | Your first agent, tools, two-agent collaboration |
| **Patterns** | 5-9 | Round-robin, auto, handoffs, pipelines, decision framework |
| **Applications** | 10-15 | Customer service, research, RAG, web browsing, UI, MCP |
| **Production** | 16-20 | Observability, security, testing, costs, deployment |
| **Advanced** | 21-23 | Redundancy, reasoning, what's next |

**[Start Episode 1 →](ag2-workshop/episodes/ep01_why_agents.ipynb)** | **[Try the Playground (no setup) →](https://playground.ag2.ai)**

## 🗺️ More Ways to Learn

- **See real apps** → Browse the [Featured Agentic Apps](#-featured-agentic-apps) below for complete, documented projects.
- **Add a UI** → Explore [AG-UI Examples](#%EF%B8%8F-ag-ui-examples) to connect your agents to a browser frontend.
- **Go to production** → Use the [GCP Agent Starter Pack](gcp-agent-starter-pack/templates/ag2/) to deploy your agent to Google Cloud Run with CI/CD and observability.

## 📂 Featured Agentic Apps

- 🛍️ [E-Commerce Custom Service for Order Management](e-commerce-customer-service) (last updated and ran on 09/20/2025, ag2 version 0.9.9): A smart, agent-driven system that makes order tracking quick and easy while simplifying returns for both logged-in and guest users.
- 📈 [Financial Analysis](financial-analysis) (last updated and ran on 09/20/2025, ag2 version 0.9.9): A AI-powered stock analysis generating market insights and recommendations.
- 🤖 [Automated Machine Learning for Kaggle](automate-ml-for-kaggle) (last updated and ran on 09/20/2025, ag2 version 0.9.9): An agent system to automate the machine learning pipeline for Kaggle competitions.
- 🧑‍🔬 [Deep Research Agent](deep-research-agent): Reference implementation of the deep research agent.
- ✈️ [Travel Planner](travel-planner): A trip planning multi-agent system that creates an itinerary together with a customer.
- 🎮 [AI Game Design Agent Team](game-design-agent-team) ⚠️ _(currently broken — pending fix for AG2 0.9+)_: A collaborative game design system that generates comprehensive game concepts through the coordination of multiple specialized AI agents.
- ☑ [Manage Todos With Realtime Agent](manage-todos-with-realtime-agent): A voice-controlled todo assistant with real-time interaction.
- 🔍 [Due Diligence with TinyFish](due-diligence-with-tinyfish): A multi-agent due diligence pipeline that automatically researches a company from a single URL using AG2 and TinyFish for deep web scraping.

## 🔌 Arcade SDK Examples

Examples of connecting AG2 agents to external services via [Arcade](https://arcade.dev) — a managed OAuth2 platform that handles authorization and tool execution, so there's no token storage or manual API setup required.

- 📋 [Linear Agent](arcade/linear-agent): A natural language interface for managing Linear issues — list, create, and update issues via Arcade's managed OAuth2 integration.
- 📧 [Gmail Agent](arcade/gmail-agent): A Gmail management agent that reads, searches, sends, and organizes emails through natural language.

## 🖥️ AG-UI Examples

Examples of connecting AG2 agents to browser frontends using the [AG-UI protocol](https://docs.ag-ui.com/introduction). Each example includes a FastAPI backend and a vanilla HTML/JS frontend — no React or build step required.

- 🌤️ [Weather Agent](ag-ui/weather/): Single-agent chat with a weather tool. Demonstrates `AGUIStream`, streaming text, tool call events, and SSE consumption in the browser.
- 🏭 [Factory Agent](ag-ui/factory/): Multi-agent document pipeline (plan → draft → review → revise → finalize). Demonstrates `ContextVariables` with `STATE_SNAPSHOT` events to provide multi-agent context to the UI.
- 🔬 [GPT Researcher](ag-ui/gpt-researcher/): Wraps the GPT Researcher multi-agent pipeline as an AG2 tool and streams pipeline stage updates and the final report to a browser frontend via AG-UI.

## ☁️ Deploy to Google Cloud

- 🚀 [GCP Agent Starter Pack](gcp-agent-starter-pack/templates/ag2/): Production-ready template that deploys an AG2 agent to Google's Cloud Run with one command. Includes Terraform, CI/CD (Cloud Build or GitHub Actions), OpenTelemetry tracing, and A2A protocol support for cross-framework agent communication.

## 🚀 Getting Started

1. **Clone the repository**

   ```bash
   git clone https://github.com/ag2ai/build-with-ag2.git
   ```

2. **Navigate to the desired project directory**

   ```bash
   cd build-with-ag2/travel-planner
   ```

3. **Install the required dependencies**

   ```bash
   # Requires Python >= 3.9, < 3.14
   pip install -r requirements.txt
   ```

4. **Follow the project-specific instructions** in each project's `README.md` file to set up and run the app.

## 🔗 Links to More Projects Built with AG2

- 📓 [AG2 Notebooks](https://github.com/ag2ai/ag2/tree/main/notebook): AG2 notebooks
- 🖥️ [Waldiez](https://github.com/waldiez/waldiez): UI for designing AG2-based workflows using drag-and-drop
- 🦸 [HeroYouth](https://github.com/linmou/HeroYouth): Empowering youth against school bullying
- 🔬 [SciAgents](https://github.com/lamm-mit/SciAgentsDiscovery): Automating scientific discovery through multi-agent intelligent graph reasoning
- 🌐 [Agent-E](https://github.com/EmergenceAI/Agent-E): A browser automation agent for natural language-driven web interactions and task automation.
- 📱 [Aquinas](https://github.com/thomasturek/aquinas): AI-Powered social media engagement tool
- 🛡️ [disarmBot](https://github.com/ultra-supara/disarmBot): A multi-agent LM system for analyzing disinformation based on DISARM
- 🛠️ [Hercules](https://github.com/test-zeus-ai/testzeus-hercules): An open-source testing agent that turns simple Gherkin steps into fully automated end-to-end tests
- 📊 [CMBAgent](https://github.com/CMBAgents/cmbagent): Multi-agent system for data analysis and visualization
- 🔏 [AutoDefense](https://github.com/XHMY/AutoDefense): Multi-agent LLM Defense against jailbreak attacks
- 🔍 [Prompt Leakage Probing](https://github.com/airtai/prompt-leakage-probing): Framework for testing LLM agents for system prompt leaks
- 💌 [AI-Powered Event Invitation Workflow](https://github.com/neosantara-xyz/examples/tree/main/ag2/event_invitation): Multi-agent event invitation system using Neosantara AI's Grok 4 for personalized multilingual content generation
- ⚡ [L402 Lightning Payments for AG2](https://github.com/refined-element/l402-requests): Gives AG2 agents the ability to access L402-protected APIs with automatic Bitcoin Lightning micropayments using `register_function()`

## 🤝 Contributing to AG2 Open Source

Created something with AG2? Contributions are welcome! If you have any ideas, improvements, or new apps to add, please create a new [GitHub Issue](https://github.com/ag2ai/build-with-ag2/issues) or submit a pull request. Make sure to follow the existing project structure and include a detailed `README.md` for each new app.

### Option 1: Link to your own repositories built with AG2

Refer to the [external repository guide](./external_repo_guide.md) to link to your own repositories showcasing projects built with AG2.

### Option 2: Creating a new project

- You can take the [project template](./project-template/) as a starting point
- Use `kebab-case` for a new project, e.g. `space-time-travel-agent`
- Add a `requirements.txt` file with the required libraries
- Write a concise `README.md` file, use [this](./project-template/README.md) as a template
- Add a `OAI_CONFIG_LIST_sample` file
- Create your project and contribute. Happy coding!

#### Code Style and Linting

This project uses pre-commit hooks to maintain code quality. Before contributing:

1. Install pre-commit:

```bash
pip install pre-commit
pre-commit install
```

2. The hooks will run automatically on commit, or you can run them manually:

```bash
pre-commit run --all-files
```

## 🌟 **Stay Updated**

Star this repository and [AG2](https://github.com/ag2ai/ag2) to receive notifications about the newest and coolest agentic applications!
