from autogen import ConversableAgent, LLMConfig
from autogen.agentchat import initiate_group_chat
from autogen.agentchat.group.patterns import AutoPattern
from dotenv import load_dotenv
import os
load_dotenv()

llm_config = llm_config = LLMConfig(config_list={"api_type": "openai", "model": "gpt-5-nano","api_key":os.getenv("OPENAI_API_KEY")})

triage_agent = ConversableAgent(
    name="triage_agent",
    system_message="""You are a triage agent. For each user query,
    identify whether it is a technical issue or a general question. Route
    technical issues to the tech agent and general questions to the general agent.
    Do not provide suggestions or answers, only route the query.""",
    llm_config=llm_config
)

tech_agent = ConversableAgent(
    name="tech_agent",
    system_message="""You solve technical problems like software bugs
    and hardware issues.""",
    llm_config=llm_config
)

general_agent = ConversableAgent(
    name="general_agent",
    system_message="You handle general, non-technical support questions.",
    llm_config=llm_config
)

user = ConversableAgent(name="user", human_input_mode="ALWAYS")

pattern = AutoPattern(
    initial_agent=triage_agent,
    agents=[triage_agent, tech_agent, general_agent],
    user_agent=user,
    group_manager_args={"llm_config": llm_config}
)

result, context, last_agent = initiate_group_chat(
    pattern=pattern,
    messages="My laptop keeps shutting down randomly. Can you help?",
    max_rounds=10
)