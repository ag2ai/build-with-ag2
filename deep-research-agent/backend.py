from fastapi import FastAPI, Request
from autogen.agents.experimental import DeepResearchAgent
from autogen import LLMConfig
import nest_asyncio
import io
import contextlib


nest_asyncio.apply()

app = FastAPI()


def run_agent(user_query):
    """Runs the agent synchronously and returns the final JSON result."""
    # Initialize DeepResearchAgent
    llm_config = LLMConfig(
        {"api_type": "openai", "model": "gpt-5-nano", "temperature": 1, "timeout": 120}
    )

    agent = DeepResearchAgent(
        name="DeepResearchAgent",
        llm_config=llm_config,
    )

    # Run the agent (synchronous call)
    final_result = agent.run(
        message=user_query,
        tools=agent.tools,
        max_turns=2,
        user_input=False,
        summary_method="reflection_with_llm",
    )

    final_result.process()

    return final_result


@app.post("/chat")
async def chat(request: Request):
    """API Endpoint that returns only the final result as JSON."""
    data = await request.json()
    user_query = data.get("message", "")

    # Capture stdout without modifying the function
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        final_result = run_agent(user_query)

    captured_output = buffer.getvalue()

    results = {
        "final_result_summary": final_result.summary,
        "final_result_cost": final_result.cost,
        "captured_output": captured_output,
    }
    return results
