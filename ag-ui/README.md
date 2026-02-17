# AG-UI Examples

Examples of connecting AG2 agents to browser frontends using the [AG-UI protocol](https://docs.ag-ui.com/introduction). Each example is a self-contained project with a FastAPI backend and a vanilla HTML/JS frontend — no React or build step required.

For background on AG2's AG-UI integration, see the [AG2 AG-UI User Guide](https://docs.ag2.ai/latest/docs/user-guide/ag-ui/) and our blog post [Give Your AG2 Agent its own UI with AG-UI](https://docs.ag2.ai/latest/blog/AG2-AG-UI-Protocol/).

## Examples

| Example | Description |
|---|---|
| [weather](weather/) | Single-agent chat with a weather tool. Demonstrates `AGUIStream`, streaming text, tool call events, and SSE consumption in the browser. |
| [factory](factory/) | Multi-agent document pipeline (plan → draft → review → revise → finalize). Demonstrates `ContextVariables` with `STATE_SNAPSHOT` events to drive agent transitions from the backend. |
