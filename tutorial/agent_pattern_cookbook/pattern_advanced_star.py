import json
from typing import Annotated
from autogen import (
    ConversableAgent,
    UserProxyAgent,
    LLMConfig,
)
from autogen.agentchat import initiate_group_chat
from autogen.agentchat.group.patterns import DefaultPattern
from autogen.agentchat.group import (
    ReplyResult,
    ContextVariables,
    AgentTarget,
    OnContextCondition,
    OnCondition,
    RevertToUserTarget,
    ContextExpression,
    ExpressionContextCondition,
    StringAvailableCondition,
    StringLLMCondition,
    ExpressionAvailableCondition,
)

# Example task: Create a virtual city guide that can answer questions about weather, events,
# transportation, and dining in various cities

# Setup LLM configuration
llm_config = LLMConfig(
    config_list={
        "api_type": "openai",
        "model": "gpt-4.1-mini",
        "parallel_tool_calls": False,
        "cache_seed": None,
    }
)

# Shared context for all agents in the group chat
shared_context = ContextVariables(
    {
        # Query state
        "query_analyzed": False,
        "query_completed": False,
        # Specialist task tracking
        "weather_info_needed": False,
        "weather_info_completed": False,
        "events_info_needed": False,
        "events_info_completed": False,
        "traffic_info_needed": False,
        "traffic_info_completed": False,
        "food_info_needed": False,
        "food_info_completed": False,
        # Content storage
        "city": "",
        "date_range": "",
        "weather_info": "",
        "events_info": "",
        "traffic_info": "",
        "food_info": "",
        "final_response": "",
    }
)

# User agent for interaction
user = UserProxyAgent(name="user", code_execution_config=False)

# ========================
# SPECIALIST FUNCTIONS
# ========================


def provide_weather_info(
    weather_content: str, context_variables: ContextVariables
) -> ReplyResult:
    """Submit weather information for the specified city and date range"""
    context_variables["weather_info"] = weather_content
    context_variables["weather_info_completed"] = True

    return ReplyResult(
        message="Weather information provided and stored.",
        context_variables=context_variables,
        target=AgentTarget(coordinator_agent),  # Always return to the coordinator
    )


def provide_events_info(
    events_content: str, context_variables: ContextVariables
) -> ReplyResult:
    """Submit events information for the specified city and date range"""
    context_variables["events_info"] = events_content
    context_variables["events_info_completed"] = True

    return ReplyResult(
        message="Events information provided and stored.",
        context_variables=context_variables,
        target=AgentTarget(coordinator_agent),  # Always return to the coordinator
    )


def provide_traffic_info(
    traffic_content: str, context_variables: ContextVariables
) -> ReplyResult:
    """Submit traffic/transportation information for the specified city"""
    context_variables["traffic_info"] = traffic_content
    context_variables["traffic_info_completed"] = True

    return ReplyResult(
        message="Traffic/transportation information provided and stored.",
        context_variables=context_variables,
        target=AgentTarget(coordinator_agent),  # Always return to the coordinator
    )


def provide_food_info(
    food_content: str, context_variables: ContextVariables
) -> ReplyResult:
    """Submit dining recommendations for the specified city"""
    context_variables["food_info"] = food_content
    context_variables["food_info_completed"] = True

    return ReplyResult(
        message="Dining recommendations provided and stored.",
        context_variables=context_variables,
        target=AgentTarget(coordinator_agent),  # Always return to the coordinator
    )


# ========================
# SPECIALIST AGENTS
# ========================
weather_specialist = ConversableAgent(
    name="weather_specialist",
    system_message="""You are a specialist in weather forecasting and climate information.
    Your task is to provide accurate and helpful weather information for the specified city and date range.
    Include:
    1. Temperature ranges (high/low)
    2. Precipitation forecasts
    3. Notable weather conditions (sunny, rainy, windy, etc.)
    4. Recommendations for appropriate clothing or preparation

    Be concise but informative, focusing on what would be most relevant for someone planning activities.
    Use your tool to provide the weather information.
    """,
    functions=[provide_weather_info],
    llm_config=llm_config,
)

events_specialist = ConversableAgent(
    name="events_specialist",
    system_message="""You are a specialist in local events, attractions, and entertainment.
    Your task is to provide information about interesting events, attractions, and activities for the specified city and date range.
    Include:
    1. Major events (concerts, festivals, sports games)
    2. Popular attractions and landmarks
    3. Cultural activities (museums, galleries, theater)
    4. Outdoor recreation opportunities

    Be specific about what's happening during the requested time frame and focus on notable highlights.
    Use your tool to provide the events information.
    """,
    functions=[provide_events_info],
    llm_config=llm_config,
)

traffic_specialist = ConversableAgent(
    name="traffic_specialist",
    system_message="""You are a specialist in transportation, traffic patterns, and getting around cities.
    Your task is to provide helpful transportation information for the specified city.
    Include:
    1. Best ways to get around (public transit, rental options, walking)
    2. Traffic patterns and areas to avoid
    3. Parking recommendations if relevant
    4. Tips for efficient transportation between popular areas

    Focus on practical advice that will help someone navigate the city efficiently.
    Use your tool to provide the traffic information.
    """,
    functions=[provide_traffic_info],
    llm_config=llm_config,
)

food_specialist = ConversableAgent(
    name="food_specialist",
    system_message="""You are a specialist in local cuisine, dining, and food culture.
    Your task is to provide dining recommendations for the specified city.
    Include:
    1. Notable restaurants across different price ranges
    2. Local specialties and must-try dishes
    3. Food districts or areas with good dining options
    4. Any famous food markets or unique food experiences

    Focus on what makes the food scene in this city special and provide diverse options.
    Use your tool to provide the food recommendations.
    """,
    functions=[provide_food_info],
    llm_config=llm_config,
)

# ========================
# COORDINATOR FUNCTIONS
# ========================


def compile_final_response(
    response_content: str, context_variables: ContextVariables
) -> ReplyResult:
    """Compile the final comprehensive response from all specialist inputs"""
    context_variables["final_response"] = response_content
    context_variables["query_completed"] = True

    return ReplyResult(
        message="Final response compiled successfully.",
        context_variables=context_variables,
        target=AgentTarget(user),  # Return to user with final response
    )


# ========================
# COORDINATOR AGENT
# ========================
coordinator_agent = ConversableAgent(
    name="coordinator_agent",
    system_message="""You are the coordinator for a virtual city guide service that helps users plan their visits or activities.

    You have four specialist agents that you can delegate to:
    1. Weather Specialist - Provides weather forecasts and climate information
    2. Events Specialist - Provides information about local events, attractions, and activities
    3. Traffic Specialist - Provides transportation advice and traffic information
    4. Food Specialist - Provides dining recommendations and food culture information

    Your responsibilities include:
    1. Analyzing user queries to determine which specialists need to be consulted
    2. Delegating specific questions to the appropriate specialists
    3. Synthesizing information from all specialists into a comprehensive, coherent response
    4. Ensuring the response is helpful, well-organized, and addresses the user's query

    First, analyze the user's query to understand what city they're asking about and what timeframe.
    Then, delegate to the appropriate specialists to gather the necessary information.
    Finally, synthesize all the information into a helpful response.

    When responding to the user, organize the information clearly with appropriate sections and highlights.
    """,
    functions=[compile_final_response],
    llm_config=llm_config,
)


@coordinator_agent.register_for_llm(description="Currency exchange calculator.")
def analyze_query(
    city: Annotated[str, "Location/City"],
    date_range: Annotated[str, "Date range for the activities"],
    needs_weather_info: Annotated[bool, "Provide weather information?"],
    needs_events_info: Annotated[bool, "Provide events information?"],
    needs_traffic_info: Annotated[bool, "Provide traffic information?"],
    needs_food_info: Annotated[bool, "Provide food/eating information?"],
    context_variables: ContextVariables,
) -> ReplyResult:
    """Analyze the user query and determine which specialists are needed"""
    context_variables["city"] = city
    context_variables["date_range"] = date_range
    context_variables["query_analyzed"] = True

    # Determine which specialist information is needed based on the parameters
    context_variables["weather_info_needed"] = needs_weather_info
    context_variables["events_info_needed"] = needs_events_info
    context_variables["traffic_info_needed"] = needs_traffic_info
    context_variables["food_info_needed"] = needs_food_info

    return ReplyResult(
        message=f"Query analyzed. Will gather information about {city} for {date_range}.",
        context_variables=context_variables,
    )


# ========================
# HANDOFFS REGISTRATION
# ========================

# Coordinator Agent handoffs to specialists
coordinator_agent.handoffs.add_many(
    [
        # Conditional handoffs to specialists based on what information is needed
        OnContextCondition(  # Example of Context Variable-based transfer, this happens automatically without LLM
            target=AgentTarget(weather_specialist),
            condition=ExpressionContextCondition(
                ContextExpression(
                    "${weather_info_needed} == True and ${weather_info_completed} == False"
                )
            ),
            available=StringAvailableCondition("query_analyzed"),
        ),
        OnCondition(  # Uses an LLM to determine if this transfer should happen
            target=AgentTarget(events_specialist),
            condition=StringLLMCondition(
                "Delegate to the events specialist for local events and activities information."
            ),
            available=ExpressionAvailableCondition(
                ContextExpression(
                    "${query_analyzed} == True and ${events_info_needed} == True and ${events_info_completed} == False"
                )
            ),
        ),
        OnCondition(
            target=AgentTarget(traffic_specialist),
            condition=StringLLMCondition(
                "Delegate to the traffic specialist for transportation and traffic information."
            ),
            available=ExpressionAvailableCondition(
                ContextExpression(
                    "${query_analyzed} == True and ${traffic_info_needed} == True and ${traffic_info_completed} == False"
                )
            ),
        ),
        OnCondition(
            target=AgentTarget(food_specialist),
            condition=StringLLMCondition(
                "Delegate to the food specialist for dining recommendations."
            ),
            available=ExpressionAvailableCondition(
                ContextExpression(
                    "${query_analyzed} == True and ${food_info_needed} == True and ${food_info_completed} == False"
                )
            ),
        ),
    ]
)
# Revert to user when finished
coordinator_agent.handoffs.set_after_work(RevertToUserTarget())

# Each specialist always returns to the coordinator
weather_specialist.handoffs.set_after_work(AgentTarget(coordinator_agent))
events_specialist.handoffs.set_after_work(AgentTarget(coordinator_agent))
traffic_specialist.handoffs.set_after_work(AgentTarget(coordinator_agent))
food_specialist.handoffs.set_after_work(AgentTarget(coordinator_agent))

# ========================
# INITIATE THE GROUP CHAT
# ========================


def run_star_pattern():
    """Run the star pattern to provide city information"""
    print("Initiating Star Pattern for City Guide...")

    agent_pattern = DefaultPattern(
        initial_agent=coordinator_agent,
        agents=[
            # Coordinator (hub)
            coordinator_agent,
            # Specialists (spokes)
            weather_specialist,
            events_specialist,
            traffic_specialist,
            food_specialist,
        ],
        context_variables=shared_context,
        user_agent=user,
    )

    chat_result, final_context, last_agent = initiate_group_chat(
        pattern=agent_pattern,
        messages="What should I do in Seattle this weekend? I'm visiting from Friday 7th March 2025 to Sunday 9th March 2025. I want to know the weather, events, transportation options, and good places to eat.",
        max_rounds=100,
    )

    # The final response will be stored in final_context["final_response"]
    if final_context["query_completed"]:
        print("City guide response completed successfully!")
        print("\n===== FINAL RESPONSE =====\n")
        print(final_context["final_response"])
        print("\n\n===== FINAL CONTEXT VARIABLES =====\n")
        print(json.dumps(final_context.to_dict(), indent=2))
        print("\n\n===== SPEAKER ORDER =====\n")
        for message in chat_result.chat_history:
            if "name" in message and message["name"] != "_Group_Tool_Executor":
                print(f"{message['name']}")
    else:
        print("City guide response did not complete successfully.")


if __name__ == "__main__":
    run_star_pattern()
