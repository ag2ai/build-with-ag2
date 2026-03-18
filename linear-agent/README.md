# Linear Agent

An AG2-powered agent that manages your [Linear](https://linear.app) issues through natural language. It connects to Linear via [Arcade](https://arcade.dev) — a managed OAuth2 service that handles authorization for you, so there's no token storage or manual API setup required.

## What the Agent Can Do

- **List issues** — fetch issues assigned to you or someone else, filtered by status, with grouped output
- **Get issue details** — look up current fields (due date, assignee, status, etc.) of a specific issue
- **Create issues** — with a preview + confirmation step before writing to Linear
- **Update issues** — change any field (due date, priority, assignee, status) on an existing issue

Example prompts:

- `Show my in-progress issues`
- `List all backlog issues assigned to john@ag2.ai`
- `What is the due date for ENG-869?`
- `Create a high-priority issue titled 'Fix login bug' in the ENG team, due March 20th`
- `Change the priority of ENG-869 to urgent`
- `Update the due date of ENG-123 to next Friday`

## AG2 Features

- **[Tool use](https://docs.ag2.ai/docs/user-guide/basic-concepts/tools):** The `AssistantAgent` decides which tools to call; the `UserProxyAgent` executes them.
- **[Two-agent pattern](https://docs.ag2.ai/latest/docs/user-guide/basic-concepts/agents):** `AssistantAgent` (LLM reasoning) + `UserProxyAgent` (tool execution) with clean termination and a multi-turn conversation loop.

## Stack

| Component         | Role                                                            |
| ----------------- | --------------------------------------------------------------- |
| **AG2**           | Multi-agent orchestration (`AssistantAgent` + `UserProxyAgent`) |
| **Arcade SDK**    | Managed OAuth2 + tool execution for Linear                      |
| **OpenAI GPT-4o** | LLM backend                                                     |
| **Linear**        | Project management target                                       |

## Installation

1. **Install dependencies using uv:**

   ```bash
   uv sync
   ```

2. **Set up environment variables:**

   ```bash
   cp .env.example .env
   # Fill in your keys
   ```

   Required variables (see `.env.example` for details):

   | Variable | Where to get it |
   |----------|-----------------|
   | `OPENAI_API_KEY` | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
   | `ARCADE_API_KEY` | [docs.arcade.dev/home/api-keys](https://docs.arcade.dev/home/api-keys) |
   | `ARCADE_USER_ID` | Email used to sign up at [arcade.dev](https://arcade.dev) |

## Running the Agent

```bash
source .env && uv run python main.py
```

On the first run, Arcade will print an OAuth URL in the terminal — open it in your browser to authorize Linear. Subsequent runs skip this step (token is cached by Arcade).

Type your request at the `You:` prompt. Type `exit` to quit.

## Build with AG2

This project is built with [AG2 (Formerly AutoGen)](https://ag2.ai/) and utilizes the following features from the library:

1. **[AssistantAgent](https://docs.ag2.ai/latest/docs/user-guide/basic-concepts/agents)** — LLM-powered agent that reasons over user requests and decides which tools to call
2. **[UserProxyAgent](https://docs.ag2.ai/latest/docs/user-guide/basic-concepts/agents)** — executes tool calls on behalf of the user
3. **[Tool use](https://docs.ag2.ai/docs/user-guide/basic-concepts/tools)** — Python functions registered on both agents for reading and writing Linear issues via Arcade SDK

Check out more projects built with AG2 at [Build with AG2](https://github.com/ag2ai/build-with-ag2)!

## Contact

- View Documentation at: https://docs.ag2.ai/latest/
- Find AG2 on GitHub: https://github.com/ag2ai/ag2
- Join us on Discord: https://discord.gg/pAbnFJrkgZ

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](../LICENSE) for details.
