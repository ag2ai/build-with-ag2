# Automated Machine Learning Workflow

In this project, we build a machine learning workflow using AG2. The workflow involves data analysis, preprocessing, and model training to build a machine learning model.

Machine learning workflows typically involve several key steps:

1. **Data Analysis and Exploration**: Understanding dataset size, columns, and distributions.
2. **Data Preprocessing**: Cleaning data, handling missing values, and encoding categorical variables.
3. **Model Training**: Training a model, comparing different models, and tuning hyperparameters.

## Details

The workflow follows the steps of data analysis, preprocessing, and model training. Each step is executed by a specific agent, and the transition between steps is determined by the success or failure of the previous step.

We follow a state machine design to build the machine learning workflow:

- **`Init`** and **`End`**: Represent the start and end of the workflow.
- **`Explore`**: Analyze the dataset.
  - **Agents**: Data Explorer → Code Executor
  - **Transition**: If code execution is successful, move to `Preprocess`; otherwise, remain in `Explore`.
- **`Preprocess`**: Clean and prepare data.
  - **Agents**: Data Preprocessor → Code Executor
  - **Transition**: A language model determines whether all necessary preprocessing steps have been completed. If yes, move to `Train`; otherwise, return to `Explore` for further analysis.
- **`Train`**: Train a machine learning model.
  - **Agents**: Model Trainer → Code Executor
  - **Transition**: The model is trained in two iterations to compare performance. If the maximum trials are reached, move to `Summarize`. If code execution fails, remain in `Train` (failed trials do not count).
- **`Summarize`**: Generate a summary of the workflow.
  - **Agents**: Summarizer
  - **Transition**: Always moves to `End`.

At the `Explore`, `Preprocess`, and `Train` states:

- A **language model agent** is invoked first.
- A **code executor** then executes the generated code.
- If execution fails, the workflow remains in the same state.
- If execution succeeds, conditions are checked to determine whether to transition to the next state.

This structured workflow ensures an efficient and iterative approach to machine learning model building.

## AG2 Features

This project demonstrates the following AG2 features:

- [GroupChat with custom speaker transitions](https://docs.ag2.ai/docs/use-cases/notebooks/notebooks/agentchat_groupchat_customized#group-chat-with-customized-speaker-selection-method)
- [Build with StateFlow design](https://docs.ag2.ai/docs/blog/2024-02-29-StateFlow/index#stateflow-build-state-driven-workflows-with-customized-speaker-selection-in-groupchat)
- [Code Execution](https://docs.ag2.ai/docs/user-guide/advanced-concepts/code-execution#code-execution)

## TAGS

TAGS: data analysis, groupchat, stateflow, code execution, kaggle, automated machine learning, workflow automation, model training, data preprocessing, state machine, hyperparameter tuning

## Prerequisites

- Python 3.12 or higher
- OpenAI API key

## Installation

1. Clone and navigate to the folder:

```bash
git clone https://github.com/ag2ai/build-with-ag2.git
cd build-with-ag2/automate-ml-for-kaggle
```

2. Install dependencies:

```bash
uv sync
```

3. Set up environment variables:

```bash
cp .env.example .env
# Edit .env with your OpenAI API key
```


## Usage

Run the automated ML workflow:

```bash
uv run python main.py
```

The workflow will:
1. Analyze the dataset (`house_prices_train.csv`)
2. Preprocess the data automatically
3. Train and compare multiple models
4. Generate performance visualizations
5. Output a comprehensive summary

## Contact

For more information or any questions, please refer to the documentation or reach out to us!

- View Documentation at: https://docs.ag2.ai/latest/
- Find AG2 on github: https://github.com/ag2ai/ag2
- Join us on Discord: https://discord.gg/pAbnFJrkgZ
- Email us at: support@ag2.ai

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](../LICENSE) for details.
