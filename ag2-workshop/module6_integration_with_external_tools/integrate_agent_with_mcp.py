import asyncio
import os
import sys
import warnings

warnings.filterwarnings("ignore", category=UserWarning, message=".*being overridden.*")
warnings.filterwarnings("ignore", category=DeprecationWarning)

from dotenv import load_dotenv

from autogen import LLMConfig
from autogen.agentchat.conversable_agent import ConversableAgent
from autogen.agentchat.group import AgentTarget
from autogen.agentchat.group.llm_condition import StringLLMCondition
from autogen.agentchat.group.on_condition import OnCondition
from autogen.agentchat.group.reply_result import ReplyResult
from autogen.mcp.mcp_client import create_toolkit
from autogen.tools import tool
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
llm_config = LLMConfig(
    {"model": "gpt-4.1-mini", "api_type": "openai", "api_key": OPENAI_API_KEY}
)

# build server config
script_dir = os.path.dirname(os.path.abspath(__file__))
arxiv_script_path = os.path.join(script_dir, "mcp_arxiv.py")

arxiv_server_params = StdioServerParameters(
    command=sys.executable,
    args=[arxiv_script_path, "stdio", "--storage-path", "/tmp/arxiv_papers"],
)

wikipedia_sse_url = "http://127.0.0.1:8000/sse"

RESEARCH_AGENT_PROMPT = """
You are a research assistant agent
You will provide assistance for research tasks.
You have two mcp servers to use:
1. ArxivServer: to search for papers on arXiv
2. WikipediaServer: to search for articles on Wikipedia
"""
research_assistant = ConversableAgent(
    name="research_assistant",
    description=RESEARCH_AGENT_PROMPT,
    llm_config=llm_config,
    human_input_mode="TERMINATE",
)


TOOL_PROMPT = """
You are a mcp_server tool.
Your purpose is to identify the correct server to execute based on the user's query.

inputs:
query: (actual user query)
server_name: (name of the server to execute — either "ArxivServer" or "WikipediaServer")

# NOTE:
    - Strictly return only servername for server_name param e.g.(ArxivServer)
    - TERMINATE after response from the server
"""


def _get_event_content(event):
    """Unwrap event: outer event.content holds the inner typed event."""
    inner = event.content if hasattr(event, "content") else event
    return inner


def _best_message_from_history(history: list) -> str:
    """
    In ag2 0.11.2, agent replies are stored as role='user', name=<agent_name>.
    Find the first (earliest) substantive agent reply in the conversation.
    """
    # First pass: find first agent reply that has real content (>50 chars)
    for msg in history:
        role = msg.get("role", "")
        name = msg.get("name", "")
        content = msg.get("content", "")
        if role == "user" and name not in ("", "user") and content and len(str(content).strip()) > 50:
            return str(content).strip()
    # Second pass: any non-empty agent reply
    for msg in history:
        role = msg.get("role", "")
        name = msg.get("name", "")
        content = msg.get("content", "")
        if role == "user" and name not in ("", "user") and content and str(content).strip():
            return str(content).strip()
    return ""


def _extract_last_message_sync(result) -> str:
    """Extract the best agent message from a sync RunResponse by consuming events."""
    try:
        for event in result.events:
            inner = _get_event_content(event)
            name = type(inner).__name__
            if name == "RunCompletionEvent":
                if hasattr(inner, "history") and inner.history:
                    best = _best_message_from_history(inner.history)
                    if best:
                        return best
    except AssertionError:
        # ag2 cleanup bug: "agent config doesn't have tool" — safe to ignore, extract from summary
        pass
    except Exception as e:
        error_str = str(e)
        if "tool_call_id" in error_str or "BadRequestError" in type(e).__name__:
            return "⚠️ arXiv API was overwhelmed — too many concurrent requests. Please wait 30 seconds and try again."
        if "429" in error_str or "HTTPError" in type(e).__name__:
            return "⚠️ arXiv is rate-limiting requests (HTTP 429). Please wait 60 seconds and try again."
        return f"⚠️ Error: {error_str[:300]}"
    # Fallback: try to get summary from result directly
    try:
        if hasattr(result, "summary") and result.summary:
            return str(result.summary)
    except Exception:
        pass
    return "No result."


async def _extract_last_message_async(result) -> str:
    """Extract the best agent message from an AsyncRunResponse by consuming events."""
    async for event in result.events:
        inner = _get_event_content(event)
        name = type(inner).__name__
        if name == "RunCompletionEvent":
            if hasattr(inner, "history") and inner.history:
                best = _best_message_from_history(inner.history)
                if best:
                    return best
    return "No result."


@tool(description=TOOL_PROMPT)
async def run_mcp_agent_to_client(query: str, server_name: str) -> ReplyResult:
    """
    Executes a query using the specified MCP server and returns the result as a ReplyResult.

    Args:
        query (str): The user's query to be processed by the agent.
        server_name (str): The name of the MCP server to use ("ArxivServer" or "WikipediaServer").

    Returns:
        ReplyResult: The result of the agent's processing, including the message and target agent.
    """
    try:
        if server_name == "ArxivServer":
            async with stdio_client(arxiv_server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    agent_tool_prompt = await session.list_tools()
                    toolkit = await create_toolkit(session=session)

                    agent = ConversableAgent(
                        name="agent",
                        llm_config=llm_config,
                        human_input_mode="NEVER",
                    )
                    toolkit.register_for_llm(agent)
                    toolkit.register_for_execution(agent)

                    result = await agent.a_run(
                        message=query
                        + " Use the following tools to answer the question: "
                        + str(agent_tool_prompt),
                        tools=toolkit.tools,
                        max_turns=5,
                    )
                    last_message = await _extract_last_message_async(result)
        elif server_name == "WikipediaServer":
            async with sse_client(wikipedia_sse_url) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    agent_tool_prompt = await session.list_tools()
                    toolkit = await create_toolkit(session=session)

                    agent = ConversableAgent(
                        name="agent",
                        llm_config=llm_config,
                        human_input_mode="NEVER",
                    )
                    toolkit.register_for_llm(agent)
                    toolkit.register_for_execution(agent)

                    result = await agent.a_run(
                        message=query
                        + " Use the following tools to answer the question: "
                        + str(agent_tool_prompt),
                        tools=toolkit.tools,
                        max_turns=5,
                    )
                    last_message = await _extract_last_message_async(result)
        else:
            raise ValueError(f"Unknown server_name: {server_name}. Use 'ArxivServer' or 'WikipediaServer'.")
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "HTTPError" in type(e).__name__ or "rate" in error_str.lower():
            last_message = "⚠️ arXiv is rate-limiting requests (HTTP 429). Please wait 60 seconds and try again."
        elif "tool_call_id" in error_str or "BadRequestError" in type(e).__name__:
            last_message = "⚠️ arXiv API was too slow — request timed out internally. Please try again."
        elif "WikipediaServer" in server_name and ("Connection" in error_str or "ConnectError" in type(e).__name__):
            last_message = "Wikipedia MCP server is not running. Start it with: python3.12 mcp_wikipedia.py --storage-path /tmp/wiki_articles sse"
        else:
            last_message = f"Error contacting {server_name}: {error_str[:200]}"

    return ReplyResult(
        message=str(last_message),
        target_agent=AgentTarget(research_assistant),
    )


def run_workflow(prompt):
    # Create a fresh agent for each request to avoid tool_call_id history bleed-over
    agent = ConversableAgent(
        name="research_assistant",
        description=RESEARCH_AGENT_PROMPT,
        llm_config=llm_config,
        human_input_mode="TERMINATE",
    )
    result = agent.run(
        message=prompt,
        tools=[run_mcp_agent_to_client],
        max_turns=2,
    )
    # ag2 0.11.2: iterate sync events, find RunCompletionEvent
    return _extract_last_message_sync(result)


if __name__ == "__main__":
    import sys

    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Search arxiv for recent papers on multi-agent AI systems and summarize the top 2 results"
    print(f"\nQuery: {prompt}\n")
    result = run_workflow(prompt)
    print("\n=== Result ===")
    print(result)

