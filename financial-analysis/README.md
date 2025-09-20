# Financial Analysis of a Given Stock

- By [yiranwu0](https://github.com/yiranwu0)
- Last revision: 06/06/2025 by [willhama](https://github.com/willhama)
- Last revision: 09/20/2025 by [qingyun-wu](https://github.com/qingyun-wu): added uv support
- This project referenced the AG2 notebook [task solving with code generation, execution, and debugging](https://docs.ag2.ai/notebooks/agentchat_auto_feedback_from_code_execution#a-comparative-analysis-of-meta-and-tesla-stocks-in-early-2024)

This project retrieves news and stock price changes for a given stock symbol (e.g., AAPL) and generates a summarized market analysis report.

## Details

- Getting 5 news from Yahoo Finance
- Getting stock price changes with Python Code, and plot a 1-year stock price change graph.
- Summarized report and analysis report generation in `market_analysis_report.md`, including a conclusion to buy, sell, or hold the stock. Note this is not a financial advice, but a demonstration of how AG2 can help with financial analysis.

## AG2 Features

This project uses the following AG2 features:

- [Using Tools](https://docs.ag2.ai/docs/user-guide/basic-concepts/tools)
- [Async Initiate Chat and Chat Summary](https://docs.ag2.ai/docs/api-reference/autogen/ConversableAgent#a-initiate-chat)

## TAGS

financial analysis, tool-use, async chat, stock-market, data-visualization, news-retrieval, investment-analysis, decision-support, market-trends

## Installation

1. Install dependencies using uv:

```bash
uv sync
```

2. Set up environment variables:

```bash
cp .env.example .env
# Edit .env with your API key
```

The primary dependency is the `ag2` library.

## Run the code

Before running the demo, you need to set up your OpenAI API configuration:


## Run the Demo

```bash
uv run python main.py
```

At the `Enter the stock you want to investigate: ` prompt, enter the stock symbol or stock name you want to investigate. For example, you can enter `AAPL` for Apple Inc. stock.

Checkout the generated `market_analysis_report.md` file for the summarized market analysis report.

## Contact

For more information or any questions, please refer to the documentation or reach out to us!

- View Documentation at: https://docs.ag2.ai/latest/
- Find AG2 on github: https://github.com/ag2ai/ag2
- Join us on Discord: https://discord.gg/pAbnFJrkgZ

## License

This project is also licensed under the Apache License 2.0 [LICENSE](../LICENSE).
