from autogen.agents.experimental import DeepResearchAgent
from autogen import LLMConfig


def main():
    llm_config = LLMConfig(
        api_type="openai",
        model="gpt-5-nano",
        cache_seed=42,
        temperature=1,
        tools=[],
        timeout=120,
    )

    # config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")
    # You can also set config_list directly as a list, for example, config_list = [{'model': 'gpt-4o', 'api_key': '<your OpenAI API key here>'},]

    agent = DeepResearchAgent(
        name="DeepResearchAgent",
        # llm_config={"config_list": config_list},
        llm_config=llm_config,
    )

    first_message = input("What would you like to research deeply?: ")

    result = agent.run(
        message=first_message,
        tools=agent.tools,
        max_turns=2,
        user_input=False,
        summary_method="reflection_with_llm",
    )

    print("#### DEEP RESEARCH RESULT ####")
    result.process()
    print(result.summary)


if __name__ == "__main__":
    main()
