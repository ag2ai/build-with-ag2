# Email Management Assistant

- By [yiranwu0](https://github.com/yiranwu0)
- Last revision: 06/06/2025 by [willhama](https://github.com/willhama)
- Last revision: 09/20/2025 by [qingyun-wu](https://github.com/qingyun-wu): added uv support
- Last revision: 11/28/2025 by [aakash232](https://github.com/aakash232): migrated to latest orchestration patterns

An intelligent email management tool that leverages AG2's group chat agents to help you quickly triage, filter, and respond to your emails. This application connects to Gmail, groups unread emails by sender, and offers two steps of automated assistance:

- **Mark as read in Batch:** Identify and mark groups of non-critical emails from the same sender as read.
- **Individual actions:** Read, summarize, and assist in drafting replies for emails requiring your attention.

## Detailed Description

This project streamlines your email workflow by performing the following tasks:

- **Connecting to Gmail:** Securely authenticates and retrieves unread emails.
- **Grouping Emails:** Organizes emails by sender and provides summaries (including subject lines and excerpts from the email body) for rapid review.
- **Bulk Filtering:** Utilizes a group chat agent (_filter_agent_) to analyze email groups, suggesting which sender groups can be marked as read, and then confirms with the user before executing the bulk action.
- **Individual Email Assistance:** Deploys another group chat agent (_email_assistant_) to classify each email, determining whether an email should be marked as read directly or read in full for further review. The agent also assists in summarizing key points and drafting responses when needed.

## AG2 Features

This project demonstrates several key AG2 features:

- **[Groupchat](https://docs.ag2.ai/latest/docs/user-guide/advanced-concepts/orchestration/group-chat/introduction/#purpose-and-benefits)**
- **[Tool using](https://docs.ag2.ai/docs/user-guide/basic-concepts/tools):** Agents trigger Python functions (e.g., marking emails as read, retrieving email threads) based on real-time context.

For further details on these features, please refer to the [AG2 Documentation](https://docs.ag2.ai/docs/Home).

## TAGS

TAGS: `groupchat`, `function-call`, `tool-use`, `email management`, `automation`, `gmail integration`, `email triage`, `workflow optimization`, `ai assistant`

## Installation

The primary dependency is the `ag2` library.

1. **Install dependencies using uv:**

   ```bash
   uv sync
   ```

2. **Set up environment variables:**

   ```bash
   cp .env.example .env
   # Edit .env with your API key
   ```

3. **Set up Google Gmail API credentials:**

- You also need to set up google credentials to access Gmail API. Search for "Gmail API" in the Google Cloud Console and enable the API.
- Follow the instructions [here](https://developers.google.com/workspace/guides/create-credentials) to set up the credentials and download the credentials JSON.
- Rename the downloaded file to `credentials.json` and move it to the root directory of this project (`email-management/`). The file should be at the same level as `main.py`

## Running the Code

1. **Settings**

   - In `main.py`, set the `max_unread_emails_limit` to be the maximum number of unread emails to fetch at each run. By default, it is set to 20.
   - By default, `is_mock_read_email` is set to `True` to mock the read email action. If set to `True`, emails in your Gmail account will be marked as read. Please be careful to modify this setting.

2. **Execute the Main Script:**
   Run the primary script to start the assistant:
   ```bash
   uv run python main.py
   ```
   - The script will prompt you to authenticate your Gmail account and authorize the application to access your emails.
   - A `token.json` file will be generated to store the authentication token for future use.
     Then you can interact with the manager to triage your emails.

## Contact

For more information or any questions, please refer to the documentation or reach out to us!

- View Documentation at: https://docs.ag2.ai/latest/
- Find AG2 on github: https://github.com/ag2ai/ag2
- Join us on Discord: https://discord.gg/pAbnFJrkgZ

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](../LICENSE) for details.
