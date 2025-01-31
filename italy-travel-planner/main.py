import streamlit as st
import autogen
from typing import Any, Dict
from autogen import (
    AFTER_WORK,
    ON_CONDITION,
    AfterWorkOption,
    SwarmAgent,
    SwarmResult,
    UserProxyAgent,
    initiate_swarm_chat,
)
from autogen.agentchat.contrib.graph_rag.document import Document, DocumentType
from graphrag_sdk.models.openai import OpenAiGenerativeModel
from autogen.agentchat.contrib.graph_rag.falkor_graph_query_engine import (
    FalkorGraphQueryEngine,
)
from autogen.agentchat.contrib.graph_rag.falkor_graph_rag_capability import (
    FalkorGraphRagCapability,
)

from ontology import get_trip_ontology
from google_map_platforms import update_itinerary_with_travel_times


def initialize_agents(config_list):
    llm_config = {"config_list": config_list, "timeout": 120}

    planner_agent = SwarmAgent(
        name="planner_agent",
        system_message="You are a trip planner agent specializing in Italian travel. You must ask the customer what they want to do if you don't have LOCATION (must be in Italy), NUMBER OF DAYS, MEALS, and ATTRACTIONS. Work with graphrag_agent to get information for an itinerary. Each event MUST HAVE a 'type' ('Restaurant' or 'Attraction'), 'location' (name), 'city', and 'description'. Ask the customer if they are happy with the itinerary before marking it as complete.",
        functions=[mark_itinerary_as_complete],
        llm_config=llm_config,
    )

    graphrag_agent = SwarmAgent(
        name="graphrag_agent",
        system_message="Return a list of restaurants and/or attractions in Italy. List them separately and provide ALL the options in the location.",
    )

    structured_config_list = config_list.copy()
    for config in structured_config_list:
        config["response_format"] = {
            "type": "object",
            "properties": {
                "message_type": {
                    "type": "string",
                    "enum": ["itinerary", "status", "error"],
                },
                "content": {"type": "object"},
                "timestamp": {"type": "string"},
            },
        }

    structured_output_agent = SwarmAgent(
        name="structured_output_agent",
        system_message="Format the provided itinerary into a structured JSON format with message_type, content, and timestamp.",
        llm_config={"config_list": structured_config_list, "timeout": 120},
        functions=[create_structured_itinerary],
    )

    route_timing_agent = SwarmAgent(
        name="route_timing_agent",
        system_message="Add travel times between locations using update_itinerary_with_travel_times. Confirm with 'Timed itinerary added' and format as a structured message.",
        llm_config=llm_config,
        functions=[update_itinerary_with_travel_times],
    )

    return planner_agent, graphrag_agent, structured_output_agent, route_timing_agent


def mark_itinerary_as_complete(
    final_itinerary: str, context_variables: Dict[str, Any]
) -> SwarmResult:
    context_variables["itinerary_confirmed"] = True
    context_variables["itinerary"] = final_itinerary
    return SwarmResult(
        agent="structured_output_agent",
        context_variables=context_variables,
        values={
            "message_type": "status",
            "content": {"status": "confirmed"},
            "timestamp": "",
        },
    )


def create_structured_itinerary(
    context_variables: Dict[str, Any], structured_itinerary: str
) -> SwarmResult:
    if not context_variables["itinerary_confirmed"]:
        return SwarmResult(
            agent="planner_agent",
            values={
                "message_type": "error",
                "content": {"error": "Itinerary not confirmed"},
                "timestamp": "",
            },
        )

    context_variables["structured_itinerary"] = structured_itinerary
    return SwarmResult(
        agent="route_timing_agent",
        context_variables=context_variables,
        values={
            "message_type": "status",
            "content": {"status": "structured"},
            "timestamp": "",
        },
    )


def setup_page():
    st.set_page_config(page_title="Italy Travel Planner", layout="wide")
    st.image("assets/ag2-logo.png", width=100)
    st.title("Italy Travel Planner")

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "context" not in st.session_state:
        st.session_state.context = {
            "itinerary_confirmed": False,
            "itinerary": "",
            "structured_itinerary": None,
        }


def main():
    setup_page()

    if "agents_initialized" not in st.session_state:
        config_list = autogen.config_list_from_json(
            "OAI_CONFIG_LIST", filter_dict={"model": ["gpt-4o"]}
        )

        query_engine = FalkorGraphQueryEngine(
            name="trip_data",
            host="0.0.0.0",
            port=6379,
            ontology=get_trip_ontology(),
            model=OpenAiGenerativeModel("gpt-4o"),
        )

        input_paths = [
            "./trip_planner_data/attractions.json",
            "./trip_planner_data/cities.json",
            "./trip_planner_data/restaurants.json",
        ]
        input_documents = [
            Document(doctype=DocumentType.TEXT, path_or_url=path)
            for path in input_paths
        ]
        query_engine.init_db(input_doc=input_documents)

        planner, graphrag, structured, route = initialize_agents(config_list)
        graph_rag_capability = FalkorGraphRagCapability(query_engine)
        graph_rag_capability.add_to_agent(graphrag)

        planner.register_hand_off(
            hand_to=[
                ON_CONDITION(
                    graphrag, "Need information on Italian restaurants and attractions"
                ),
                ON_CONDITION(structured, "Itinerary is confirmed by the customer"),
                AFTER_WORK(AfterWorkOption.REVERT_TO_USER),
            ]
        )
        graphrag.register_hand_off(hand_to=[AFTER_WORK(planner)])
        structured.register_hand_off(hand_to=[AFTER_WORK(route)])
        route.register_hand_off(hand_to=[AFTER_WORK(AfterWorkOption.TERMINATE)])

        st.session_state.agents = {
            "planner": planner,
            "graphrag": graphrag,
            "structured": structured,
            "route": route,
        }
        st.session_state.agents_initialized = True

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    if prompt := st.chat_input("What are your travel plans for Italy?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        customer = UserProxyAgent(name="customer", code_execution_config=False)

        chat_result, context_variables, last_agent = initiate_swarm_chat(
            initial_agent=st.session_state.agents["planner"],
            agents=list(st.session_state.agents.values()),
            user_agent=customer,
            context_variables=st.session_state.context,
            messages=prompt,
            after_work=AfterWorkOption.TERMINATE,
            max_rounds=100,
        )

        st.session_state.context = context_variables

        for message in chat_result:
            with st.chat_message(message.get("agent", "assistant")):
                st.write(message.get("content", ""))


if __name__ == "__main__":
    main()
