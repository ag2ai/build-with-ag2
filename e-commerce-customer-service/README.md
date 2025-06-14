# E-commerce Customer Service for order management

<!-- [Overall Description, authorship/references,] -->

- By [yiranwu0](https://github.com/yiranwu0)
- Last revision: 26/05/2025 by [willhama](https://github.com/willhama)

In this study, we build a robust and flexible order management system using decentralized agent orchestration. The system addresses two primary user needs: order tracking and order returns. The workflow considers the user’s login status during the initial interaction. Users can quickly track an order using a tracking number without logging in, while returns require authentication. This system leverages modular agents for triaging, tracking, login management, order management, and returns, ensuring a seamless user experience.

## AG2 Features

This project demonstrates the following AG2 features:

- [Groupchat](https://docs.ag2.ai/latest/docs/user-guide/advanced-concepts/orchestration/group-chat/introduction/#purpose-and-benefits)

## TAGS

TAGS: groupchat, e-commerce, order management, customer service, order tracking, returns processing, authentication, workflow automation, agent orchestration

## Description

<!-- [More detailed description, any additional information about the use case] -->

**Agents and Workflow**
We initialize the context variables with two fields: `user_info` to store user information (and order list when a user logs in) and `order_info` to store the retrieved order information. Since groupchat is a decentralized orchestration, we will transfer logic in each agent:

- **Order Triage Agent**:
  When the user sends a message related to orders, it will be routed to the Order Triage Agent. This agent will further decide whether to transfer to the Tracking Agent or the Login Agent.

- **Tracking Agent**:
  Helps the user track an order without login. It will first ask the user to provide a tracking number. If the number is valid, it will ask for additional information (email, last name, phone number) to confirm the user’s identity. It can also transfer to the Login Agent if the user needs to manage the orders.

  - Tools:
    - `verify_tracking_number`: verifies if the tracking number is valid and updates the context variables with the order info if valid.
    - `verify_user_information`: validates the user’s information and returns the order details if correct.

- **Login Agent**:
  Prompts the user to log in and checks login status. This agent has a tool `login_account` to initiate a login session for the user. Upon successful login, it updates the context variables with the user’s info and transfers control to the Order Management Agent. If login fails, it can guide the user to try again or help them start the process to find their account or reset their password. Currently, we have a dummy login system that logs in directly without any authentication.

- **Order Management Agent**:
  A general-purpose agent used after the user is logged in. It has access to the user’s entire order history, so it can help the user find past orders through the `get_order_history` or `check_order_status` tool. It can also hand off to a Return Agent for returning orders.

- **Return Agent**:
  Helps the user return an order. It first verifies if the order is eligible for return via the `check_return_eligibility` tool, and then starts the process upon the user’s confirmation with `initiate_return_process`. It can transfer back to the Order Management Agent as needed.

## Installation

To set up the environment, run the following command:

```bash
pip install -r requirements.txt
```

The primary dependency is the `ag2` library.

## Run the code

First, set up the `config_list` in the `main.py` file (line 10). Read more about configurations [here](https://docs.ag2.ai/docs/topics/llm_configuration).

```python
python main.py
```

The system will start running, and you can interact with it through the command line.

**Example Interaction 1: Cancel orders**

1. `I want to cancel my order`
2. `TR14234`
3. .. Continue to interact with the system ..

**Example Interaction 2: Track orders**

1. `I want to track my order`
2. `TR13845`
3. `8453` (last 4 digits of phone number)
4. .. Continue to interact with the system ..

## Contact

For more information or any questions, please refer to the documentation or reach out to us!

- View Documentation at: https://docs.ag2.ai/docs/Home
- Reachout to us: https://github.com/ag2ai/ag2
- Join Discord: https://discord.gg/pAbnFJrkgZ

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](../LICENSE) for details.
