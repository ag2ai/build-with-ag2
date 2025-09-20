from autogen import ConversableAgent, LLMConfig
from autogen.agentchat import initiate_group_chat
from autogen.agentchat.group.patterns import DefaultPattern
from autogen.agentchat.group import (
    AgentTarget,
    RevertToUserTarget,
    OnCondition,
    StringLLMCondition,
    OnContextCondition,
    ExpressionContextCondition,
    ContextExpression,
    ContextVariables,
)
import os
from dotenv import load_dotenv


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
print(OPENAI_API_KEY)

llm_config = LLMConfig(api_type="openai", model="gpt-5-nano", api_key=OPENAI_API_KEY)

# Shared context for ticket state
shared_context = ContextVariables(
    data={
        "ticket_text": "",
        "ticket_category": "",
        "ticket_status": "open",
        "escalation_flag": False,
        "response_text": "",
        "customer_email": "",
        "billing_status": "",
        "system_status": "",
    }
)

with llm_config:
    triage_agent = ConversableAgent(
        name="triage_agent",
        system_message=(
            "You are a customer support triage agent. "
            "For each incoming ticket, analyze the content and classify it as one of: "
            "'billing', 'technical', or 'general'. "
            "Set the 'ticket_category' context variable accordingly. "
            "If the ticket is ambiguous, use your best judgment. "
            "Do not answer the ticket yourself."
        ),
    )

    billing_agent = ConversableAgent(
        name="billing_agent",
        system_message=(
            "You are a billing support specialist. "
            "For each ticket, use the check_billing_status tool if a customer email is provided. "
            "Draft a clear, empathetic, and actionable response. "
            "Set 'ticket_status' to 'resolved' if you can help, or set 'escalation_flag' to True if escalation is needed. "
            "Store your response in 'response_text'."
        ),
    )

    technical_agent = ConversableAgent(
        name="technical_agent",
        system_message=(
            "You are a technical support specialist. "
            "For each ticket, use the check_system_status tool to inform your response. "
            "Draft a clear troubleshooting response. "
            "Set 'ticket_status' to 'resolved' if you can help, or set 'escalation_flag' to True if escalation is needed. "
            "Store your response in 'response_text'."
        ),
    )

    general_agent = ConversableAgent(
        name="general_agent",
        system_message=(
            "You are a general support specialist. "
            "For each ticket, draft a helpful, friendly response. "
            "Set 'ticket_status' to 'resolved' if you can help, or set 'escalation_flag' to True if escalation is needed. "
            "Store your response in 'response_text'."
        ),
    )

    user = ConversableAgent(name="user", human_input_mode="ALWAYS")


@billing_agent.register_for_execution()
def check_billing_status(
    customer_email: str, context_variables: ContextVariables
) -> str:
    """Simulate checking a billing system for the latest invoice/payment status."""
    if customer_email:
        status = "Paid in full. No outstanding invoices."
    else:
        status = "No email provided. Unable to check billing status."
    context_variables["billing_status"] = status
    return status


@technical_agent.register_for_execution()
def check_system_status(context_variables: ContextVariables) -> str:
    """Simulate checking the current system status."""
    status = "All systems operational. No known outages."
    context_variables["system_status"] = status
    return status


triage_agent.handoffs.add_llm_conditions(
    [
        OnCondition(
            target=AgentTarget(billing_agent),
            condition=StringLLMCondition(
                prompt="If the ticket is about billing, payment, refund, subscription, or invoices, set ticket_category to 'billing' and route to billing_agent."
            ),
        ),
        OnCondition(
            target=AgentTarget(technical_agent),
            condition=StringLLMCondition(
                prompt="If the ticket is about technical issues, bugs, errors, login problems, or product malfunctions, set ticket_category to 'technical' and route to technical_agent."
            ),
        ),
        OnCondition(
            target=AgentTarget(general_agent),
            condition=StringLLMCondition(
                prompt="If the ticket is about general questions, account management, feedback, or topics not related to billing or technical issues, set ticket_category to 'general' and route to general_agent."
            ),
        ),
    ]
)

for agent in [billing_agent, technical_agent, general_agent]:
    agent.handoffs.add_context_condition(
        OnContextCondition(
            target=RevertToUserTarget(),
            condition=ExpressionContextCondition(
                ContextExpression(
                    "${ticket_status} == 'resolved' and ${escalation_flag} == False"
                )
            ),
        )
    )
    agent.handoffs.add_context_condition(
        OnContextCondition(
            target=RevertToUserTarget(),
            condition=ExpressionContextCondition(
                ContextExpression("${escalation_flag} == True")
            ),
        )
    )

pattern = DefaultPattern(
    initial_agent=triage_agent,
    agents=[triage_agent, billing_agent, technical_agent, general_agent],
    user_agent=user,
    context_variables=shared_context,
    group_manager_args={"llm_config": llm_config},
)


def run_workflow(prompt):
    result, context, last_agent = initiate_group_chat(
        pattern=pattern, messages=prompt, max_rounds=5
    )
    return result.summary
