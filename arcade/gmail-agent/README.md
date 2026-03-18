# Gmail Agent

An AG2-powered agent that manages your Gmail through natural language. It connects to Gmail via [Arcade](https://arcade.dev) — a managed OAuth2 service that handles authorization for you, so there's no token storage or manual API setup required.

## What the Agent Can Do

- **List emails** — fetch unread emails, filter by sender, control result limit
- **Read threads** — view full conversation context by thread ID
- **Search** — find emails by subject, body keywords, sender, or date range
- **Mark as read / unread** — update read status
- **Archive** — remove from inbox without deleting
- **Trash** — move to Trash with confirmation step
- **Send** — compose and send new emails with a preview + confirmation step
- **Reply / Reply All** — respond to emails with preview + confirmation
- **Create draft** — save emails as drafts without sending

Example prompts:

- `Show my unread emails`
- `List emails from someone@example.com`
- `Search for emails about the Arcade partnership`
- `Show the full thread for this email`
- `Reply to this email: sounds good, see you then`
- `Archive all emails from newsletter@substack.com`
- `Trash this email`
- `Send an email to someone@example.com about scheduling a demo`

## AG2 Features

- **[Tool use](https://docs.ag2.ai/docs/user-guide/basic-concepts/tools):** The `AssistantAgent` decides which tools to call; the `UserProxyAgent` executes them.
- **[Two-agent pattern](https://docs.ag2.ai/latest/docs/user-guide/basic-concepts/agents):** `AssistantAgent` (LLM reasoning) + `UserProxyAgent` (tool execution) with clean termination and a multi-turn conversation loop.

## Stack

| Component         | Role                                                            |
| ----------------- | --------------------------------------------------------------- |
| **AG2**           | Multi-agent orchestration (`AssistantAgent` + `UserProxyAgent`) |
| **Arcade SDK**    | Managed OAuth2 + tool execution for Gmail                       |
| **OpenAI GPT-4o** | LLM backend                                                     |
| **Gmail**         | Email management target                                         |

## Installation

1. **Install dependencies using uv:**

   ```bash
   uv sync
   ```

2. **Set up environment variables:**

   ```bash
   export OPENAI_API_KEY=...
   export ARCADE_API_KEY=...
   export ARCADE_USER_ID=your@email.com   # email used to sign up at arcade.dev
   ```

   | Variable | Where to get it |
   |----------|-----------------|
   | `OPENAI_API_KEY` | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
   | `ARCADE_API_KEY` | [docs.arcade.dev/home/api-keys](https://docs.arcade.dev/home/api-keys) |
   | `ARCADE_USER_ID` | Email used to sign up at [arcade.dev](https://arcade.dev) |

## Running the Agent

```bash
source .env && uv run python main.py
```

On the first run, Arcade will print an OAuth URL in the terminal — open it in your browser to authorize Gmail. Subsequent runs skip this step (token is cached by Arcade).

Type your request at the `You:` prompt. Type `exit` or `quit` to quit.

## Build with AG2

This project is built with [AG2 (Formerly AutoGen)](https://ag2.ai/) and utilizes the following features from the library:

1. **[AssistantAgent](https://docs.ag2.ai/latest/docs/user-guide/basic-concepts/agents)** — LLM-powered agent that reasons over user requests and decides which tools to call
2. **[UserProxyAgent](https://docs.ag2.ai/latest/docs/user-guide/basic-concepts/agents)** — executes tool calls on behalf of the user
3. **[Tool use](https://docs.ag2.ai/docs/user-guide/basic-concepts/tools)** — Python functions registered on both agents for reading and writing Gmail via Arcade SDK

Check out more projects built with AG2 at [Build with AG2](https://github.com/ag2ai/build-with-ag2)!

## Contact

- View Documentation at: https://docs.ag2.ai/latest/
- Find AG2 on GitHub: https://github.com/ag2ai/ag2
- Join us on Discord: https://discord.gg/pAbnFJrkgZ

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](../../LICENSE) for details.
