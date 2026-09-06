# Webzio News Search

- Created by [Shaked Degani](https://github.com/ShakedDegani) (Webz.io)
- Last revision: 09/06/2026

An AG2 agent that searches global news with [Webz.io](https://webz.io) Contextual News Search. Ask a question in plain language; the agent calls `news_search_by_webz` and summarizes with sources.

## Overview

1. Construct `WebzioNewsSearchToolkit` (reads `WEBZ_API_TOKEN`).
2. Pass it to an AG2 `Agent`.
3. The model picks filters from the live MCP schema (`tools/list`) and returns a sourced summary.

## AG2 Features

- [Agent](https://docs.ag2.ai/docs/user-guide/basic-concepts/introducing-agents/) — single researcher agent
- [WebzioNewsSearchToolkit](https://docs.ag2.ai/docs/user-guide/extensions/tools/search/webzio/) — hosted Webz.io News Search MCP server
- [MCPToolkit](https://docs.ag2.ai/docs/user-guide/tools/mcp_servers/) — client-side MCP used under the hood

## Tags

TAGS: news-search, webzio, webz, mcp, research-assistant, tools, automation

## Installation

### Prerequisites

- Python 3.10+
- An [OpenAI API key](https://platform.openai.com/api-keys)
- A [Webz.io API token](https://webz.io) (same token as the News Search API)
- An AG2 release that includes `WebzioNewsSearchToolkit` (see [ag2ai/ag2#3232](https://github.com/ag2ai/ag2/pull/3232))

### Setup

```bash
git clone https://github.com/ag2ai/build-with-ag2.git
cd build-with-ag2/webzio-news-search
pip install -r requirements.txt
cp .env.example .env
# Fill in OPENAI_API_KEY and WEBZ_API_TOKEN
```

## Usage

Default prompt (Nvidia supply-chain coverage, last 30 days):

```bash
python main.py
```

Your own question:

```bash
python main.py "Find negative coverage about Boeing from the last 7 days using Webz news search."
```

Optional:

```bash
export OPENAI_MODEL=gpt-4.1-mini
```

Each search uses your Webz.io News Search API credits and rate limits.

## Contact

- Webz.io News Search MCP: https://docs.webz.io/docs/webz/news-search-api-mcp
- AG2 docs: https://docs.ag2.ai
- AG2 on GitHub: https://github.com/ag2ai/ag2
- Discord: https://discord.gg/pAbnFJrkgZ

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](../LICENSE) for details.
