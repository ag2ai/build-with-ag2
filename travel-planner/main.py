import atexit
import json
import os
import tempfile
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from autogen import ConversableAgent, UserProxyAgent, LLMConfig
from autogen.agentchat import initiate_group_chat
from autogen.agentchat.group import (
    ReplyResult,
    ContextVariables,
    AgentTarget,
    AgentNameTarget,
    RevertToUserTarget,
    TerminateTarget,
    OnCondition,
    StringLLMCondition,
)
from autogen.agentchat.group.patterns import DefaultPattern
from autogen.agentchat.contrib.graph_rag.document import Document, DocumentType
from graphrag_sdk.models.openai import OpenAiGenerativeModel
from autogen.agentchat.contrib.graph_rag.falkor_graph_query_engine import (
    FalkorGraphQueryEngine,
)
from autogen.agentchat.contrib.graph_rag.falkor_graph_rag_capability import (
    FalkorGraphRagCapability,
)

# local file imports
from ontology import get_trip_ontology
from google_map_platforms import Itinerary, update_itinerary_with_travel_times

# ---------------------------------------------------------------------
# 1. Initialize the LLM Configuration
# ---------------------------------------------------------------------

api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    raise ValueError(
        "OPENAI_API_KEY not set. Copy .env.example to .env and add your key."
    )

llm_config = LLMConfig(
    {"model": "gpt-4o", "api_key": api_key},
    timeout=120,
)

# ---------------------------------------------------------------------
# 2. Initialize the FalkorDB GraphRAG
# ---------------------------------------------------------------------

falkordb_host = os.environ.get("FALKORDB_HOST", "0.0.0.0")
falkordb_port = int(os.environ.get("FALKORDB_PORT", "6379"))

_temp_files: list[str] = []


def _cleanup_temp_files() -> None:
    for path in _temp_files:
        try:
            os.unlink(path)
        except OSError:
            pass


atexit.register(_cleanup_temp_files)


def _json_to_jsonl(json_path: str) -> str:
    """Convert a JSON array file to a JSONL temp file (required by graphrag_sdk)."""
    with open(json_path) as f:
        data = json.load(f)
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False)
    for item in data:
        tmp.write(json.dumps(item) + "\n")
    tmp.close()
    _temp_files.append(tmp.name)
    return tmp.name


input_paths = [
    "./trip_planner_data/attractions.json",
    "./trip_planner_data/cities.json",
    "./trip_planner_data/restaurants.json",
]
input_documents = [
    Document(doctype=DocumentType.TEXT, path_or_url=_json_to_jsonl(p))
    for p in input_paths
]

trip_data_ontology = get_trip_ontology()

query_engine = FalkorGraphQueryEngine(
    name="trip_data",
    host=falkordb_host,
    port=falkordb_port,
    ontology=trip_data_ontology,
    model=OpenAiGenerativeModel("gpt-4o"),
)

# Data already ingested on first run — use connect_db to reconnect.
# To re-ingest from scratch, replace connect_db with init_db below.
query_engine.connect_db()

# ---------------------------------------------------------------------
# 3. Define context and tool functions
# ---------------------------------------------------------------------

trip_context = ContextVariables(
    data={
        "itinerary_confirmed": False,
        "structured_itinerary": None,
    }
)


def mark_itinerary_as_complete(
    final_itinerary: str, context_variables: ContextVariables
) -> ReplyResult:
    """Store and mark our itinerary as accepted by the customer."""
    context_variables["itinerary_confirmed"] = True

    return ReplyResult(
        message="Itinerary recorded and confirmed.",
        context_variables=context_variables,
        target=AgentNameTarget("structured_output_agent"),
    )


def create_structured_itinerary(
    structured_itinerary: str, context_variables: ContextVariables
) -> ReplyResult:
    """Once a structured itinerary is created, store it and pass on to the Route Timing agent."""
    if not context_variables["itinerary_confirmed"]:
        return ReplyResult(
            message="Itinerary not confirmed, please confirm the itinerary with the customer first.",
            context_variables=context_variables,
            target=AgentNameTarget("planner_agent"),
        )

    # Validate it's actually JSON before storing
    try:
        json.loads(structured_itinerary)
    except (ValueError, TypeError):
        return ReplyResult(
            message="Structured itinerary is not valid JSON, please reformat it correctly.",
            context_variables=context_variables,
            target=AgentNameTarget("structured_output_agent"),
        )

    # Only store the first valid itinerary — ignore duplicate parallel calls
    if context_variables.get("structured_itinerary") is not None:
        return ReplyResult(
            message="Structured itinerary already stored.",
            context_variables=context_variables,
            target=AgentNameTarget("route_timing_agent"),
        )

    context_variables["structured_itinerary"] = structured_itinerary

    return ReplyResult(
        message="Structured itinerary stored.",
        context_variables=context_variables,
        target=AgentNameTarget("route_timing_agent"),
    )


# ---------------------------------------------------------------------
# 4. Create Agents
# ---------------------------------------------------------------------

planner_agent = ConversableAgent(
    name="planner_agent",
    system_message=(
        "You are a trip planner agent. It is important to know where the customer is going, how many days, what they want to do. "
        "You will work with another agent, graphrag_agent, to get information about restaurants and attractions. "
        "You are also working with the customer, so you must ask the customer what they want to do if you don't have LOCATION, NUMBER OF DAYS, MEALS, and ATTRACTIONS. "
        "When you have the customer's requirements, work with graphrag_agent to get information for an itinerary. "
        "You are responsible for creating the itinerary and for each day in the itinerary you MUST HAVE events and EACH EVENT MUST HAVE a 'type' ('Restaurant' or 'Attraction'), 'location' (name of restaurant or attraction), 'city', and 'description'. "
        "IMPORTANT: The itinerary must ONLY contain 'Restaurant' and 'Attraction' events. Do NOT include accommodation, hotels, or any other event types — mention hotels in plain text to the customer if asked, but NEVER add them to the itinerary. "
        "Finally, YOU MUST ask the customer if they are happy with the itinerary before marking the itinerary as complete."
    ),
    llm_config=llm_config,
    functions=[mark_itinerary_as_complete],
)

graphrag_agent = ConversableAgent(
    name="graphrag_agent",
    system_message="Return a list of restaurants and/or attractions. List them separately and provide ALL the options in the location. Do not provide travel advice.",
    llm_config=False,
)

structured_output_agent = ConversableAgent(
    name="structured_output_agent",
    system_message=(
        "You are a data formatting agent. Format the itinerary from the conversation into the required structured format, "
        "then YOU MUST call the create_structured_itinerary tool with the resulting JSON string. Do not skip this tool call."
    ),
    llm_config=LLMConfig(
        {"model": "gpt-4o", "api_key": api_key},
        response_format=Itinerary,
        timeout=120,
    ),
    functions=[create_structured_itinerary],
)

route_timing_agent = ConversableAgent(
    name="route_timing_agent",
    system_message=(
        "You are a route timing agent. YOU MUST call the update_itinerary_with_travel_times tool if you do not see the exact phrase "
        "'Timed itinerary added to context with travel times' in this conversation. Only after this please tell the customer 'Your itinerary is ready!'."
    ),
    llm_config=llm_config,
    functions=[update_itinerary_with_travel_times],
)

# Add FalkorDB capability to graphrag_agent
graph_rag_capability = FalkorGraphRagCapability(query_engine)
graph_rag_capability.add_to_agent(graphrag_agent)

customer = UserProxyAgent(name="customer", code_execution_config=False)

# ---------------------------------------------------------------------
# 5. Register handoffs
# ---------------------------------------------------------------------

planner_agent.handoffs.add_many(
    [
        OnCondition(
            target=AgentTarget(graphrag_agent),
            condition=StringLLMCondition(
                "Need information on the restaurants and attractions for a location. DO NOT call more than once at a time."
            ),
        ),
        OnCondition(
            target=AgentTarget(structured_output_agent),
            condition=StringLLMCondition("Itinerary is confirmed by the customer"),
        ),
    ]
)
planner_agent.handoffs.set_after_work(RevertToUserTarget())

graphrag_agent.handoffs.set_after_work(AgentTarget(planner_agent))
structured_output_agent.handoffs.set_after_work(AgentTarget(route_timing_agent))
route_timing_agent.handoffs.set_after_work(TerminateTarget())

# ---------------------------------------------------------------------
# 6. Start the conversation
# ---------------------------------------------------------------------

pattern = DefaultPattern(
    initial_agent=planner_agent,
    agents=[planner_agent, graphrag_agent, structured_output_agent, route_timing_agent],
    user_agent=customer,
    context_variables=trip_context,
    group_after_work=TerminateTarget(),
)

chat_result, context_variables, last_agent = initiate_group_chat(
    pattern=pattern,
    messages="I want to go to Rome for a couple of days. Can you help me plan my trip?",
    max_rounds=100,
)

# ---------------------------------------------------------------------
# 7. Print itinerary
# ---------------------------------------------------------------------


def print_itinerary(itinerary_data: dict[str, Any]) -> None:
    header = "█             █\n █           █ \n  █  █████  █  \n   ██     ██   \n  █         █  \n █  ███████  █ \n █ ██ ███ ██ █ \n   █████████   \n\n ██   ███ ███  \n█  █ █       █ \n████ █ ██  ██  \n█  █ █  █ █    \n█  █  ██  ████ \n"
    width = 80
    icons = {"Travel": "🚶", "Restaurant": "🍽️", "Attraction": "🏛️"}

    for line in header.split("\n"):
        print(line.center(width))
    print(
        f"Itinerary for {itinerary_data['days'][0]['events'][0]['city']}".center(width)
    )
    print("=" * width)

    for day_num, day in enumerate(itinerary_data["days"], 1):
        print(f"\nDay {day_num}".center(width))
        print("-" * width)

        for event in day["events"]:
            event_type = event["type"]
            print(f"\n  {icons.get(event_type, '📍')} {event['location']}")
            if event_type != "Travel":
                words = event["description"].split()
                line = "    "
                for word in words:
                    if len(line) + len(word) + 1 <= 76:
                        line += word + " "
                    else:
                        print(line)
                        line = "    " + word + " "
                if line.strip():
                    print(line)
            else:
                print(f"    {event['description']}")
        print("\n" + "-" * width)


if "timed_itinerary" in context_variables:
    print_itinerary(context_variables["timed_itinerary"])
else:
    print("No itinerary available to print.")
