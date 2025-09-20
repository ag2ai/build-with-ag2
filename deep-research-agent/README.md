# AG2 DeepResearchAgent - Reference Implementation

- Created by [willhama](https://github.com/willhama)
- Last revision: 09/20/2025 by [qingyun-wu](https://github.com/qingyun-wu)

DeepResearchAgent is an advanced research tool built on the AG2 framework, inspired by OpenAI's deep research capabilities.

## Overview

This reference implementation demonstrates OpenAI's deep research agent functionality. It efficiently retrieves relevant data, processes information, and delivers concise conclusions to help analysts and investors make informed decisions.

Learn more: https://openai.com/index/introducing-deep-research/

## AG2 Features

- [DeepResearchAgent](https://docs.ag2.ai/docs/blog/2025-02-13-DeepResearchAgent/index)

## Tags

deep-research, data-retrieval, automation, research-assistant, streamlit, uvicorn, web-scraping

## Installation

DeepResearchAgent requires Python 3.12 or higher.

### Using uv (recommended)

1. Install uv if you haven't already:

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Install the project dependencies:

   ```bash
   uv sync
   ```

3. Set up environment variables:

   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key
   ```

4. Run the application:

   ```bash
   uv run python main.py
   ```

## Web Interface

You can also run the application with a Streamlit frontend and FastAPI backend:

1. Start the backend:

   ```bash
   uvicorn backend:app --reload
   ```

2. Start the frontend:

   ```bash
   streamlit run frontend.py
   ```

3. Open your browser and navigate to `http://localhost:8501/`

## Contact

For more information or any questions, please refer to the documentation or reach out to us!

- View Documentation at: https://docs.ag2.ai/latest/
- Find AG2 on github: https://github.com/ag2ai/ag2
- Join us on Discord: https://discord.gg/pAbnFJrkgZ

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](../LICENSE) for details.
