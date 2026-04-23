# AG2 Beta Examples

Examples built on **[AG2 Beta](https://docs.ag2.ai/docs/beta/motivation)** — the new API track inside `autogen.beta`.

Beta is a clean-slate redesign focused on simpler single-agent DX, async-first execution, modern context/memory primitives, and first-class support for emerging standards (MCP, A2A, AG-UI). Beta agents can also interoperate with existing AG2 group chats via `agent.as_conversable()`.

## Why a separate folder?

Every other project in this repo uses the classic AG2 API (`AssistantAgent`, `UserProxyAgent`, `ConversableAgent`, `initiate_chat`). The Beta API is materially different:

| Classic AG2 | AG2 Beta |
|---|---|
| `AssistantAgent(..., llm_config=...)` | `Agent(name, prompt=..., config=OpenAIConfig(...))` |
| `user_proxy.initiate_chat(...)` | `reply = await agent.ask(...)` |
| `register_function(...)` | `@tool` / `@agent.tool` |
| Sync-first | **Async-first** |
| Manual SSE plumbing | `MemoryStream` + `AGUIStream` |

Grouping Beta examples here keeps patterns, conventions, and dependency pins consistent as more are added.

## Examples

- [parallel-research/](./parallel-research/) — a lead coordinator fans out research to 3 Tavily-powered researcher subagents that run **in parallel**, with live progress streamed to the terminal as interleaved lanes. Built for the [AG2 Hackathon](https://luma.com/42lzgbrz) (Track #2: Multi-Agent Collaboration).
- [ask-the-web/](./ask-the-web/) — citation-backed web Q&A with a clean chat UI. Single Beta Agent + Tavily search/fetch, exposed through `autogen.beta.ag_ui.AGUIStream` with a one-file HTML frontend that renders streaming text and live source cards. Demonstrates Beta's first-party AG-UI integration.

## Adding a new Beta example

1. Create a `kebab-case` subfolder under `beta/`.
2. Include `pyproject.toml` (or `requirements.txt`), `main.py`, `.env.example`, and `README.md`.
3. Depend on `ag2>=0.12.0` to pick up the current `autogen.beta` API (subagents, AG-UI, etc.).
4. Prefer `async def main()` with `asyncio.run(main())` — Beta is async-first.
5. Use `MemoryStream` for observability rather than printing inside tools.

## References

- [AG2 Beta Motivation](https://docs.ag2.ai/docs/beta/motivation)
- [Beta API reference](https://docs.ag2.ai/docs/beta/agents)
- [Beta Roadmap](https://docs.ag2.ai/docs/beta/roadmap)
