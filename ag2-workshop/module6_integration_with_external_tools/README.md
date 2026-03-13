### Module 6 — Integration with External Tools (MCP)

This guide shows how to set up a fresh Python environment and install the dependencies to run the MCP demos for arXiv and Wikipedia.

### Prerequisites
- Python 3.12+ required (`mcp` package does not support Python < 3.10; 3.12 recommended)
- macOS/Linux/Windows shell

### 1) Create and activate a virtual environment
```bash
# From the repo root
python3.12 -m venv .venv

# macOS/Linux
source .venv/bin/activate

# Windows (PowerShell)
# .venv\Scripts\Activate.ps1
```

### 2) Upgrade pip and install dependencies
```bash
pip install -U "ag2[openai,mcp]" python-dotenv streamlit arxiv wikipedia
```

### 3) Configure LLM credentials
Create a `.env` file in this directory:
```bash
OPENAI_API_KEY=your_key_here
```
Or export directly:
```bash
export OPENAI_API_KEY=YOUR_KEY
```

### 4) Run the Streamlit UI
```bash
cd ag2-workshop/module6_integration_with_external_tools
python3.12 -m streamlit run my_app.py
```
The app opens at **http://localhost:8501**. The arXiv MCP server starts automatically.

### 5) (Optional) Start the Wikipedia MCP server (SSE)
This module includes an SSE-based Wikipedia MCP server. Run it in a **separate terminal** before starting the app if you want Wikipedia tools available.
```bash
cd ag2-workshop/module6_integration_with_external_tools
python3.12 mcp_wikipedia.py --storage-path /tmp/wiki_articles sse
# This starts an SSE server on http://127.0.0.1:8000/sse
```

### 6) Run the integration script directly (without UI)
```bash
cd ag2-workshop/module6_integration_with_external_tools

# With default query (arXiv multi-agent AI papers)
python3.12 integrate_agent_with_mcp.py

# With a custom query
python3.12 integrate_agent_with_mcp.py "Search for papers about large language models"
```

You should see the agent call the arXiv MCP server and return paper summaries. If you started the Wikipedia server in step 5, the agent can also route queries to Wikipedia.
