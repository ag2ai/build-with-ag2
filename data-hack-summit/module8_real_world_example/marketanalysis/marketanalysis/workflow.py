import os
from typing import Any

from autogen import LLMConfig
from fastagency import UI
from fastagency.runtimes.ag2 import Workflow
from autogen.agentchat import initiate_group_chat
from marketanalysis.market_analysis import agent_pattern

llm_config = LLMConfig(
    model="gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.8,
)

wf = Workflow()


@wf.register(name="simple_learning", description="Student and teacher learning chat")  # type: ignore[misc]
def simple_workflow(ui: UI, params: dict[str, Any]) -> str:
    initial_message = ui.text_input(
        sender="Workflow",
        recipient="User",
        prompt="I can help you learn about mathematics. What subject you would like to explore?",
    )

    chat_result, final_context, last_agent = initiate_group_chat(
        pattern=agent_pattern,
        messages=initial_message,
        max_rounds=30,
    )
    return chat_result.summary
