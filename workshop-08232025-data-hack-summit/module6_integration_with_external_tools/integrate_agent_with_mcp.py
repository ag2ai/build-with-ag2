import os
import sys

from dotenv import load_dotenv

from autogen import LLMConfig
from autogen.agentchat.conversable_agent import ConversableAgent
from autogen.agentchat.group import AgentTarget
from autogen.agentchat.group.llm_condition import StringLLMCondition
from autogen.agentchat.group.on_condition import OnCondition
from autogen.agentchat.group.reply_result import ReplyResult
from autogen.mcp.mcp_client import (
    MCPClientSessionManager,
    MCPConfig,
    SseConfig,
    StdioConfig,
    create_toolkit,
)
from autogen.tools import tool

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
llm_config = LLMConfig(model="gpt-5-nano", api_type="openai", api_key=OPENAI_API_KEY)

# build server config
script_dir = os.path.dirname(os.path.abspath(__file__))
arxiv_script_path = os.path.join(script_dir, "mcp_arxiv.py")

ArxivServer = StdioConfig(
    command=sys.executable,
    args=[arxiv_script_path, "stdio", "--storage-path", "/tmp/arxiv_papers"],
    transport="stdio",
    server_name="ArxivServer",
)

WikipediaServer = SseConfig(
    url="http://127.0.0.1:8000/sse",
    timeout=10,
    sse_read_timeout=60,
    server_name="WikipediaServer",
)

mcp_config = MCPConfig(servers=[ArxivServer, WikipediaServer])


def get_server_config(
    mcp_config: MCPConfig, server_name: str
) -> StdioConfig | SseConfig:
    """
    Return the server config (StdioConfig or SseConfig) matching the given server_name.
    """
    existing_names = {
        getattr(server, "server_name", None) for server in mcp_config.servers
    }
    for server in mcp_config.servers:
        if getattr(server, "server_name", None) == server_name:
            return server
    raise KeyError(
        f"Server '{server_name}' not found in MCPConfig. Existing servers: {list(existing_names)}"
    )


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
You are a mcp_server tool
your purpose is to Identify correct server to execute based on the user's query

inputs:
query: (actual user query)
server_name: (name of the server to execute)

You have two mcp servers to use:
1. ArxivServer: to search for papers on arXiv
2. WikipediaServer: to search for articles on Wikipedia

# NOTE:
    - Strictly return only servername for server_name param e.g.(ArxivServer)
    - TERMINATE after response from the server
"""


@tool(description=TOOL_PROMPT)
async def run_mcp_agent_to_client(query: str, server_name: str) -> ReplyResult:
    """
    Executes a query using the specified MCP server and returns the result as a ReplyResult.

    Args:
        query (str): The user's query to be processed by the agent.
        server_name (str): The name of the MCP server to use (e.g., "ArxivServer" or "WikipediaServer").

    Returns:
        ReplyResult: The result of the agent's processing, including the message and target agent.
    """
    server = get_server_config(mcp_config, server_name)
    async with MCPClientSessionManager().open_session(server) as session:
        await session.initialize()
        agent_tool_prompt = await session.list_tools()

        toolkit = await create_toolkit(session=session)
        # internal agent to execute the query
        agent = ConversableAgent(
            name="agent",
            llm_config=llm_config,
            human_input_mode="NEVER",
        )
        toolkit.register_for_llm(agent)
        toolkit.register_for_execution(agent)
        agent.handoffs.add_llm_conditions(
            [
                OnCondition(
                    target=AgentTarget(research_assistant),
                    condition=StringLLMCondition(
                        prompt="The research paper ids are fetched."
                    ),
                ),
                OnCondition(
                    target=AgentTarget(research_assistant),
                    condition=StringLLMCondition(
                        prompt="Wikipedia Information was fetched from MCP Server tools."
                    ),
                ),
            ]
        )
        # Make a request using the MCP tool
        result = await agent.a_run(
            message=query
            + "use the following tools to answer the question:  "
            + str(agent_tool_prompt),
            tools=toolkit.tools,
            max_turns=5,
        )
        res = await result.process()
        last_message = await res.last_message()
        return ReplyResult(
            message=str(last_message["content"][-1]),
            target_agent=AgentTarget(research_assistant),
        )


def run_workflow(prompt):
    result = research_assistant.run(
        message=prompt,
        tools=[run_mcp_agent_to_client],
        max_turns=2,
    )
    res = result.process()
    last_message = res.last_message()
    return last_message["content"][-1]
