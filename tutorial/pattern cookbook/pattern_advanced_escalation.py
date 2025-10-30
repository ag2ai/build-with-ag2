# Example implementation of the Escalation Pattern for agent orchestration
# with structured confidence outputs and agent-specific context variables

import json
from typing import Any, Optional
from pydantic import BaseModel, Field
from autogen import (
    ConversableAgent,
    UserProxyAgent,
    ContextExpression,
    LLMConfig,
)
from autogen.agentchat import initiate_group_chat
from autogen.agentchat.group import ReplyResult, ContextVariables, AgentNameTarget, AgentTarget, RevertToUserTarget, OnContextCondition, StayTarget, ExpressionContextCondition, TerminateTarget
from autogen.agentchat.group.patterns import DefaultPattern

# Define structured output models
class ConsideredResponse(BaseModel):
    """Structured response format for agents in the escalation pattern"""
    answer: str = Field(..., description="The agent's answer to the query")
    confidence: int = Field(
        ...,
        description="Confidence level from 1-10 where 1 is extremely uncertain and 10 is absolutely certain",
    )
    reasoning: str = Field(..., description="The agent's reasoning process")
    escalation_reason: Optional[str] = Field(
        None,
        description="Reason for possible escalation if confidence < 8."
    )

    class Config:
        arbitrary_types_allowed = True

def new_question_asked(question: str, context_variables: ContextVariables) -> ReplyResult:
    """If a new question is asked, this tool will reset context variables and route to the basic_agent. Only call this if the user has just asked a new question. If you have just received an answer, output it to the user."""
    context_variables["basic_agent_confidence"] = 0
    context_variables["intermediate_agent_confidence"] = 0
    context_variables["advanced_agent_confidence"] = 0
    context_variables["escalation_count"] = 0
    context_variables["last_escalation_reason"] = ""
    context_variables["last_escalating_agent"] = ""

    context_variables["current_question"] = question
    return ReplyResult(
        target=AgentNameTarget("basic_agent"),
        context_variables=context_variables,
        message=f"New question received, context variables reset.\n\nbasic_agent try and answer this question:\n{question}"
    )

def answer_question_common(response: ConsideredResponse, agent_level: str, context_variables: ContextVariables) -> ReplyResult:
    """Common question answer function that updates context variables and routes based on the answer confidence.

    agent_level will be one of "basic", "intermediate", or "advanced".
    """
    context_variables[f"{agent_level}_agent_confidence"] = response.confidence

    if response.confidence < 8:
        context_variables["escalation_count"] = context_variables["escalation_count"] + 1
        context_variables["last_escalation_reason"] = response.escalation_reason
        context_variables["last_escalating_agent"] = f"{agent_level}_agent"

        if agent_level == "advanced":
            return ReplyResult(target=AgentNameTarget("triage_agent"), context_variables=context_variables, message=f"I am not confident with my answer (confidence level {response.confidence}/10, reason:\n{response.escalation_reason}\n\nanswer: {response.answer}\n\nPlease consult a human expert.")

        next_agent_level = "intermediate" if agent_level == "basic" else "advanced"
        return ReplyResult(target=AgentNameTarget(f"{next_agent_level}_agent"), context_variables=context_variables, message=f"Need to escalate with confidence {response.confidence}/10, reason:\n{response.escalation_reason}")
    else:
        return ReplyResult(target=AgentNameTarget("triage_agent"), context_variables=context_variables, message=f"Successfully answered with confidence ({response.confidence}/10):\n{response.answer}")

def answer_question_basic(response: ConsideredResponse, context_variables: ContextVariables) -> ReplyResult:
    """Always call this tool with your answer."""
    return answer_question_common(response, "basic", context_variables)

def answer_question_intermediate(response: ConsideredResponse, context_variables: ContextVariables) -> ReplyResult:
    """Always call this tool with your answer."""
    return answer_question_common(response, "intermediate", context_variables)

def answer_question_advanced(response: ConsideredResponse, context_variables: ContextVariables) -> ReplyResult:
    """Always call this tool with your answer."""
    return answer_question_common(response, "advanced", context_variables)

def main():
    """
    Main function to demonstrate the Escalation Pattern with the Group Chat orchestration engine.
    """
    # Triage agent will handle the user interaction
    triage_agent = ConversableAgent(
        name="triage_agent",
        system_message="""You are a triage agent that routes queries to the appropriate level of expertise.
        If there's a new question, call the new_question_asked tool to process it.
        If a question has been successfully answered, output the question and answer and don't call a tool.
        You should never answer the question yourself.
        """,
        functions=[new_question_asked],
        llm_config=LLMConfig(config_list={
            "model": "gpt-4.1-mini",
            "temperature": 0,
            "cache_seed": None,
        })
    )

    # Create agents of increasing capability/cost
    basic_agent = ConversableAgent(
        name="basic_agent",
        system_message="""You are a basic agent that handles simple tasks efficiently.
        You can answer common knowledge questions and perform basic calculations.

        You MUST provide your responses in the required structured format, including a confidence score from 1-10.

        If a query requires specialized knowledge beyond your capabilities or is complex, set needs_escalation to True
        and provide a brief reason in escalation_reason.

        Confidence level guide:
        - 1-3: Very uncertain, likely to be incorrect
        - 4-6: Moderate confidence, might be correct
        - 7-8: Good confidence, probably correct
        - 9-10: High confidence, almost certainly correct

        For simple factual questions and basic calculations that you can handle well, your confidence should be 8-10.
        For it's not a simple question, rate accordingly lower.

        Always call the answer_question_basic tool when answering.
        """,
        functions=[answer_question_basic],
        llm_config=LLMConfig(config_list={
            "api_type": "openai",
            "model": "gpt-5-nano",
            "temperature": 0,
            "cache_seed": None,
        })
    )

    intermediate_agent = ConversableAgent(
        name="intermediate_agent",
        system_message="""You are an intermediate agent that handles moderately complex tasks.
        You can perform more nuanced analysis, provide detailed explanations, and handle domain-specific knowledge.

        You MUST provide your responses in the required structured format, including a confidence score from 1-10.

        If a query requires deep expertise or is very complex beyond your capabilities, set needs_escalation to True
        and provide a brief reason in escalation_reason.

        Confidence level guide:
        - 1-3: Very uncertain, likely to be incorrect
        - 4-6: Moderate confidence, might be correct
        - 7-8: Good confidence, probably correct
        - 9-10: High confidence, almost certainly correct

        For questions within your knowledge domain that you can handle well, your confidence should be 8-10.
        For more specialized or complex questions where you're less certain, rate accordingly lower.
        """,
        functions=[answer_question_intermediate],
        llm_config=LLMConfig(config_list={
            "api_type": "openai",
            "model": "gpt-5-nano",
            "temperature": 0,
            "seed": 42,
        })
    )

    advanced_agent = ConversableAgent(
        name="advanced_agent",
        system_message="""You are an advanced agent with extensive knowledge and reasoning capabilities.
        You can handle complex reasoning, specialized domains, and difficult problem-solving tasks.

        You MUST provide your responses in the required structured format, including a confidence score from 1-10.

        If a task is beyond even your capabilities, set needs_escalation to True and recommend consulting a human expert
        in the escalation_reason field.

        Confidence level guide:
        - 1-3: Very uncertain, likely to be incorrect
        - 4-6: Moderate confidence, might be correct
        - 7-8: Good confidence, probably correct
        - 9-10: High confidence, almost certainly correct

        For questions that you can handle well, your confidence should be 8-10.
        For extremely specialized or cutting-edge questions where you're less certain, rate accordingly lower.
        """,
        functions=[answer_question_advanced],
        llm_config=LLMConfig(config_list={
            "api_type": "anthropic",
            "model": "claude-3-7-sonnet-20250219",
            "seed": 42,
        })
    )

    # Create a user proxy agent
    user_proxy = UserProxyAgent(
        name="user_proxy",
        system_message="You are a proxy for the human user.",
        human_input_mode="ALWAYS"
    )

    triage_agent.handoffs.set_after_work(RevertToUserTarget())

    # Register escalation paths for the basic agent

    # Escalate based on agent-specific context variables
    basic_agent.handoffs.add_context_condition(
        OnContextCondition(
            target=AgentTarget(intermediate_agent),
            condition=ExpressionContextCondition(expression=ContextExpression("${basic_agent_confidence} > 0 and ${basic_agent_confidence} < 8"))
            )
        )
    basic_agent.handoffs.set_after_work(StayTarget())

    # Register escalation paths for the intermediate agent

    # Escalate based on agent-specific context variables
    intermediate_agent.handoffs.add_context_condition(
        OnContextCondition(
            target=AgentTarget(advanced_agent),
            condition=ExpressionContextCondition(expression=ContextExpression("${intermediate_agent_confidence} > 0 and ${intermediate_agent_confidence} < 8"))
        )
    )

    # Advanced agent falls back to user when all agents are insufficient
    advanced_agent.handoffs.set_after_work(RevertToUserTarget())

    # Initial context variables with agent-specific confidence and escalation flags
    context_variables = ContextVariables(data={
        # Agent-specific variables
        "basic_agent_confidence": 0,
        "intermediate_agent_confidence": 0,
        "advanced_agent_confidence": 0,

        # Global tracking variables
        "escalation_count": 0,
        "last_escalation_reason": "",
        "last_escalating_agent": "",

        "current_question": ""
    })

    basic_question = "What is 100 divided by 5?"
    intermediate_question = (
        "Calculate the energy of a quantum system with three particles in a harmonic oscillator potential. "
        "The first particle has energy level n=2, the second particle has energy level n=1, and the third particle has energy level n=0. "
        "Assume the harmonic oscillator has a frequency of ω = 2.5 eV/ħ."
        )
    advanced_question = (
        "Develop a mathematical model for optimizing the tradeoff between exploration and exploitation in reinforcement learning for a "
        "non-stationary multi-armed bandit problem where the reward distributions shift according to a hidden Markov model. "
        "Include the formal equations for the Upper Confidence Bound (UCB) algorithm modification you would propose, and explain "
        "how your approach addresses the non-stationarity challenge better than Thompson Sampling with a sliding window."
        )

    agent_pattern = DefaultPattern(
        agents=[
            basic_agent,
            intermediate_agent,
            advanced_agent,
            triage_agent
        ],
        initial_agent=triage_agent,
        context_variables=context_variables,
        group_after_work=TerminateTarget(),
        user_agent=user_proxy,
    )

    chat_result, final_context, last_speaker = initiate_group_chat(
        pattern=agent_pattern,
        messages=advanced_question, # Try different questions
        max_rounds=20,
    )

    print("\n===== SUMMARY =====\n")
    print(chat_result.summary)
    print("\n\n===== FINAL CONTEXT VARIABLES =====\n")
    print(json.dumps(final_context.to_dict(), indent=2))
    print("\n\n===== SPEAKER ORDER =====\n")
    for message in chat_result.chat_history:
        if "name" in message and message["name"] != "_Group_Tool_Executor":
            print(f"{message['name']}")

if __name__ == "__main__":
    main()