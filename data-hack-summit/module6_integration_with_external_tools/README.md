### Module 6 — Integration with External Tools (MCP)

This guide shows how to set up a fresh Python environment and install the dependencies to run the MCP demos for arXiv and Wikipedia.

### Prerequisites
- Python 3.11+ recommended
- macOS/Linux/Windows shell

### 1) Create and activate a virtual environment
```bash
# From the repo root
python -m venv .venv

# macOS/Linux
source .venv/bin/activate

# Windows (PowerShell)
# .venv\Scripts\Activate.ps1
```

### 2) Upgrade pip and install dependencies
```bash
pip install -U "ag2[openai,mcp]"
```

### 3) Configure LLM credentials
- If using OpenAI, set:
```bash
export OPENAI_API_KEY=YOUR_KEY
```
- If using Azure OpenAI, ensure your endpoint, API version, and key are configured in `integrate_agent_with_mcp.py`.

### 4) (Optional) Start the Wikipedia MCP server (SSE)
This module includes an SSE-based Wikipedia MCP server. Run it in a separate terminal if you want Wikipedia tools available.
```bash
cd data-hack-summit/module6_integration_with_external_tools
python mcp_wikipedia.py sse --storage-path /tmp/wiki_articles
# This starts an SSE server on http://127.0.0.1:8000/sse
```

The arXiv MCP server runs via stdio and is launched automatically by the integration script.

### 5) Run the integration script
```bash
cd data-hack-summit/module6_integration_with_external_tools
python integrate_agent_with_mcp.py
```

You should see the agent call the arXiv MCP server and fetch the latest paper IDs. If you started the Wikipedia server, the agent can also route queries to Wikipedia.
