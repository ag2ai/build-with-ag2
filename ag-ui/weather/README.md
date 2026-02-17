# AG-UI Weather Agent

A weather chat agent built with AG2's ConversableAgent and connected to a pixel-art browser UI via the [AG-UI protocol](https://docs.ag2.ai/latest/docs/user-guide/ag-ui/). The agent uses a `get_weather` tool that calls the free [Open-Meteo API](https://open-meteo.com/) — no API key required for weather data.

The frontend is a single HTML file (no React, no build step) that consumes AG-UI events over SSE to render streaming text, tool call progress, and a weather data card.

## AG2 Features

This project demonstrates the following AG2 features:

- [AG-UI Protocol](https://docs.ag2.ai/latest/docs/user-guide/ag-ui/) — streaming typed events to a browser frontend
- [ConversableAgent](https://docs.ag2.ai/latest/docs/user-guide/agentchat-user-guide/basics/conversable-agent/) — single-agent setup
- [Tool Use / Function Calling](https://docs.ag2.ai/latest/docs/user-guide/agentchat-user-guide/basics/tools/) — async weather tool with type annotations

## TAGS

TAGS: ag-ui, weather, streaming, tool-use, sse, fastapi, single-agent

## File Structure

| File | Description |
|---|---|
| `backend.py` | FastAPI server, ConversableAgent with `get_weather` tool, AGUIStream integration |
| `frontend.html` | Pixel-art chat UI, SSE consumption, weather card rendering, markdown via marked.js |
| `assets/style.css` | AG2-themed CSS (pixel borders, retro fonts, status dot) |
| `assets/*.png` | Robot avatars, clouds, sun, roadscape background |

## Installation

1. Clone and navigate to the folder:

   ```bash
   git clone https://github.com/ag2ai/build-with-ag2.git
   cd build-with-ag2/ag-ui/weather
   ```

2. Install dependencies:

   ```bash
   pip install "ag2[openai,ag-ui]" fastapi uvicorn httpx python-dotenv
   ```

3. Set your OpenAI API key (used by the ConversableAgent's LLM):

   ```bash
   export OPENAI_API_KEY="sk-..."
   ```

   Or create a `.env` file in the project directory:

   ```
   OPENAI_API_KEY=sk-...
   ```

## Running the Code

```bash
python backend.py
```

Open http://localhost:8456 in your browser.

Click **Tokyo Weather** or **SF Weather** to see the weather card, or type any question for a free-text conversation.

## Contact

For more information or any questions, please refer to the documentation or reach out to us!

- AG2 Documentation: https://docs.ag2.ai/docs/Home
- AG2 GitHub: https://github.com/ag2ai/ag2
- Discord: https://discord.gg/pAbnFJrkgZ

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](../../LICENSE) for details.
