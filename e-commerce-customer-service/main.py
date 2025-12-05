from autogen.agentchat import initiate_group_chat
from autogen.agentchat.group import (
    AgentTarget,
    ContextVariables,
    OnCondition,
    StringLLMCondition,
    RevertToUserTarget,
)
from autogen.agentchat.group.patterns import DefaultPattern


from autogen import ConversableAgent, UserProxyAgent
from autogen import LLMConfig

from prompts import (
    order_triage_prompt,
    tracking_order_prompt,
    login_in_management_prompt,
    order_management_prompt,
    return_prompt,
)
from functions import (
    verify_order_number,
    verify_user_information,
    login_account,
    get_order_history,
    check_order_status,
    check_return_eligibility,
    initiate_return_process,
)

# # 1. Load the configuration file
# config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")

# # 2. Load the keys directly
# config_list = [
#     {
#         "model": "gpt-4o",
#         "api_key": open("...", "r").read(),
#     }
# ]


# llm_config = {
#     "cache_seed": 42,  # change the cache_seed for different trials
#     "temperature": 1,
#     "config_list": config_list,
#     "timeout": 120,
#     "tools": [],
# }

# AWS Bedrock
# llm_config = LLMConfig(
#     api_type="bedrock",
#     model="us.anthropic.claude-sonnet-4-20250514-v1:0",
#     aws_region="us-east-1",
#     cache_seed=42,
#     temperature=1,
#     tools=[],
#     timeout=120,
# )

llm_config = LLMConfig(
    api_type="openai",
    model="gpt-5-nano",
    cache_seed=42,
    temperature=1,
    tools=[],
    timeout=120,
)


context_variables = {
    # retrieve for verfication
    "user_name": "Kevin Doe",
    "preferred_name": "Kev",
    "date_of_birth": "1998-02-01",
    "packages_information": "",
    "is_user_verified": False,
}

INIT_USER_INFO = {
    # when logging in
    "user_info": None,
    # for tracking agent
    "order_number": None,
    "order_info": None,
}

support_context = ContextVariables(context_variables)

order_triage_agent = ConversableAgent(
    name="order_triage_agent",
    system_message=order_triage_prompt,
    llm_config=llm_config,
)

tracking_agent = ConversableAgent(
    name="order_tracking_agent",
    system_message=tracking_order_prompt,
    llm_config=llm_config,
    functions=[verify_order_number, verify_user_information],
)

login_agent = ConversableAgent(
    name="login_management_agent",
    system_message=login_in_management_prompt,
    llm_config=llm_config,
    functions=[login_account],
)

order_management_agent = ConversableAgent(
    name="order_management_agent",
    system_message=order_management_prompt,
    llm_config=llm_config,
    functions=[get_order_history, check_order_status],
)

return_agent = ConversableAgent(
    name="return_agent",
    system_message=return_prompt,
    llm_config=llm_config,
    functions=[check_return_eligibility, initiate_return_process],
)

order_triage_agent.handoffs.add_llm_conditions(
    [
        OnCondition(
            target=AgentTarget(login_agent),
            condition=StringLLMCondition(prompt="Transfer to the login agent"),
        ),
        OnCondition(
            target=AgentTarget(tracking_agent),
            condition=StringLLMCondition(prompt="Transfer to the tracking agent"),
        ),
    ]
)
tracking_agent.handoffs.add_llm_condition(
    OnCondition(
        target=AgentTarget(login_agent),
        condition=StringLLMCondition(prompt="Transfer to the login agent"),
    )
)
order_management_agent.handoffs.add_llm_condition(
    OnCondition(
        target=AgentTarget(return_agent),
        condition=StringLLMCondition(prompt="Transfer to the return agent"),
    )
)
return_agent.handoffs.add_llm_condition(
    OnCondition(
        target=AgentTarget(order_management_agent),
        condition=StringLLMCondition(prompt="Transfer to the order management agent"),
    )
)

user = UserProxyAgent(
    name="Customer",
    system_message="Agent that represents the Customer",
    code_execution_config=False,
)


agent_pattern = DefaultPattern(
    agents=[
        order_triage_agent,
        tracking_agent,
        login_agent,
        order_management_agent,
        return_agent,
    ],
    initial_agent=order_triage_agent,
    context_variables=support_context,
    user_agent=user,
    group_after_work=RevertToUserTarget(),
)

result, final_context, last_agent = initiate_group_chat(
    pattern=agent_pattern,
    messages="Hello",
    max_rounds=40,
)
