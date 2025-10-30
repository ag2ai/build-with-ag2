import os

from autogen import ConversableAgent, LLMConfig

llm_config=LLMConfig(config_list={"api_type": "openai", "model": "gpt-5-nano", "api_key": os.environ["OPENAI_API_KEY"]})

student_agent = ConversableAgent(
    name="Student_Agent",
    system_message="You are a student willing to learn.",
    llm_config=llm_config
)
teacher_agent = ConversableAgent(
    name="Teacher_Agent",
    system_message="You are a math teacher.",
    llm_config=llm_config
)

chat_result = student_agent.initiate_chat(
    teacher_agent,
    message="What is triangle inequality?",
    summary_method="reflection_with_llm",
    max_turns=2,
)

print(chat_result.summary)