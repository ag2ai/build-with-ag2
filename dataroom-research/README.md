# DataRoom Research: AG2 DeepResearch Agent + GoogleDriveToolkit

- Created by [internetoftim](https://github.com/internetoftim)
- Updated by [qingyun-wu](https://github.com/qingyun-wu)
- Last revision: 06/06/2025


DataRoom Research is an multi-agent research system that combines the capabilities of DeepResearchAgent with GoogleDriveToolkit, built on the AG2 framework. It enhances OpenAI's deep research agent concept by adding document handling and Google Drive integration.

## Detailed Description

This project combines two powerful agent systems:

1. **DeepResearchAgent** - Inspired by OpenAI's deep research agent, it efficiently retrieves relevant data, processes information, and provides concise research conclusions.
   - https://openai.com/index/introducing-deep-research/

2. **Google Drive Integration** - Seamlessly integrates with Google Drive to access, download, and analyze documents stored in the cloud.

The system also features a professional report writer agent that creates well-structured markdown reports with proper formatting.

## AG2 Features

- [DeepResearchAgent](https://docs.ag2.ai/docs/blog/2025-02-13-DeepResearchAgent/index) - For advanced web research and data gathering
- [GoogleDriveToolkit](https://docs.ag2.ai/latest/docs/user-guide/reference-tools/google-api/google-drive/) - For seamless Google Drive integration
- [GroupChat](https://docs.ag2.ai/latest/docs/use-cases/notebooks/notebooks/agentchat_groupchat_tools/) - Flexible orchestration of multiple specialized agents

## TAGS

TAGS: deep-research, data-retrieval, google-drive, document-analysis, multi-agent, report-writer, automation, research-assistant, web-scraping

## Installation

DeepResearchAgent requires Python 3.11 or higher.

### Using uv (Recommended)

1. Install dependencies using uv:

   ```bash
   uv sync
   ```

2. Install Playwright (required for web data retrieval):

   ```bash
   uv run playwright install
   ```

## Running the code

Before running the system, you need to complete some configuration steps:

### 1. Configure API Access

#### OpenAI API Configuration
Create an `OAI_CONFIG_LIST` file based on the provided sample and update the `api_key` field with your OpenAI API key:

```bash
cp OAI_CONFIG_LIST_sample OAI_CONFIG_LIST
# Edit the file to add your API key
```

### 2. Google Drive Integration

For a detailed tutorial on the Google Drive Toolkit functionality, see the
[AG2 Google Drive Documentation](https://docs.ag2.ai/latest/docs/use-cases/notebooks/notebooks/tools_google_drive/)

Note: In order to successfully run that notebook, you would need to do the following steps first

To enable Google Drive features, you need OAuth credentials following [Google's Quickstart](https://developers.google.com/workspace/drive/api/quickstart/python#set-up-environment):

1. Create a Google Cloud project and enable the Drive API
2. Create OAuth 2.0 credentials and download as `credentials.json`
3. Place `credentials.json` in the project root directory
4. (Optional) Generate the `token.json` file by running [gdrive_signin.py](https://github.com/googleworkspace/python-samples/blob/main/drive/quickstart/quickstart.py)

The system will automatically handle OAuth authentication on first run, and you should be able to see the files in your Google Drive account get listed here.

```bash
uv run python gdrive_signin.py
```

You can also copy over the `credentials.json` and `token.json` to run the [AG2 Google Drive Collab Notebook](https://docs.ag2.ai/latest/docs/use-cases/notebooks/notebooks/tools_google_drive/)

## 3. Run the System

### Basic Command-line Interface

Run the main application with standard research capabilities:

```bash
uv run python main.py
```

With Google Drive capabilities enabled:

```bash
uv run python main.py --use-gdrive
```

For testing with simulated research responses:

```bash
uv run python main.py --use-fake
```

## Features and Capabilities

### DeepResearchAgent
- Conducts comprehensive web research on any given topic
- Uses the latest browser automation tools to gather accurate and up-to-date information
- Analyzes multiple sources to provide balanced, objective research
- Provides citations and references for all findings


### Google Drive Integration
- Lists files and folders from your Google Drive account
- Downloads documents for local processing
- Searches Drive for specific file types or content
- Integrates downloaded documents seamlessly with the document analysis capabilities

###  Report Generation
- The Report Writer agent creates well-structured markdown reports with proper sections and exports it as a Markdown file
- Executive summaries, key findings, and detailed analysis in consistent formatting


## (Optional) Using Local LLMs with Ollama

This system supports using local language models through Ollama as an alternative to OpenAI's API. This can provide privacy benefits, reduce costs, and enable offline usage.

###  Setting Up Ollama

1. Install Ollama by following the instructions at [Ollama's official website](https://ollama.ai/download)

2. Pull a compatible model (we recommend models with at least 7B parameters):

Install a model (example)
```bash
ollama pull deepseek-r1
```

# or another compatible model
```bash
ollama pull llama3:8b
```

# Start the Ollama server
```bash
ollama serve
```

Ollama runs a REST API on http://localhost:11434 by default. The Ollama configuration is included in OAI_CONFIG_LIST to use the local LLM with your agent.


For more information or any questions, please refer to the documentation or reach out to us!

- View Documentation at: https://docs.ag2.ai/docs/Home
- Reachout to us: https://github.com/ag2ai/ag2
- Join Discord: https://discord.gg/pAbnFJrkgZ

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](../LICENSE) for details.
