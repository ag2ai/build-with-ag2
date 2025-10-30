# Example task: Research and create a comprehensive report on renewable energy technologies

import json
from autogen import (
    ConversableAgent,
    ContextExpression,
    UserProxyAgent,
    LLMConfig,
)
from autogen.agentchat.group import AgentNameTarget, AgentTarget, ContextVariables, ReplyResult, OnContextCondition, ExpressionContextCondition, TerminateTarget, ExpressionAvailableCondition, RevertToUserTarget, OnCondition, StringLLMCondition
from autogen.agentchat.group.patterns import DefaultPattern
from autogen.agentchat import initiate_group_chat

# Setup LLM configuration
# Note that we turn parallel tool calling off for OpenAI so we only get one tool call at a time.
llm_config = LLMConfig(config_list={"api_type": "openai", "model": "gpt-5-nano", "parallel_tool_calls": False})

# Shared context for all agents in the group chat
shared_context = ContextVariables(data={
    # Project state
    "task_started": False,
    "task_completed": False,

    # Hierarchical state tracking
    "executive_review_ready": False,
    "manager_a_completed": False,
    "manager_b_completed": False,
    "manager_c_completed": False,

    # Specialist task tracking
    "specialist_a1_completed": False,
    "specialist_a2_completed": False,
    "specialist_b1_completed": False,
    "specialist_b2_completed": False,
    "specialist_c1_completed": False,

    # Content storage
    "solar_research": "",
    "wind_research": "",
    "hydro_research": "",
    "geothermal_research": "",
    "biofuel_research": "",
    "report_sections": {},
    "final_report": ""
})

# User agent for interaction
user = UserProxyAgent(
    name="user",
    code_execution_config=False
)

# ========================
# SPECIALIST FUNCTIONS
# ========================

def complete_solar_research(research_content: str, context_variables: ContextVariables) -> ReplyResult:
    """Submit solar energy research findings"""
    context_variables["solar_research"] = research_content
    context_variables["specialist_a1_completed"] = True

    # Check if both specialists under Manager A have completed their tasks
    if context_variables["specialist_a1_completed"] and context_variables["specialist_a2_completed"]:
        context_variables["manager_a_completed"] = True

    return ReplyResult(
        message="Solar research completed and stored.",
        context_variables=context_variables,
        target=AgentTarget(renewable_manager),
    )

def complete_wind_research(research_content: str, context_variables: ContextVariables) -> ReplyResult:
    """Submit wind energy research findings"""
    context_variables["wind_research"] = research_content
    context_variables["specialist_a2_completed"] = True

    # Check if both specialists under Manager A have completed their tasks
    if context_variables["specialist_a1_completed"] and context_variables["specialist_a2_completed"]:
        context_variables["manager_a_completed"] = True

    return ReplyResult(
        message="Wind research completed and stored.",
        context_variables=context_variables,
        target=AgentTarget(renewable_manager),
    )

def complete_hydro_research(research_content: str, context_variables: ContextVariables) -> ReplyResult:
    """Submit hydroelectric energy research findings"""
    context_variables["hydro_research"] = research_content
    context_variables["specialist_b1_completed"] = True

    # Check if both specialists under Manager B have completed their tasks
    if context_variables["specialist_b1_completed"] and context_variables["specialist_b2_completed"]:
        context_variables["manager_b_completed"] = True

    return ReplyResult(
        message="Hydroelectric research completed and stored.",
        context_variables=context_variables,
        target=AgentTarget(storage_manager),
    )

def complete_geothermal_research(research_content: str, context_variables: ContextVariables) -> ReplyResult:
    """Submit geothermal energy research findings"""
    context_variables["geothermal_research"] = research_content
    context_variables["specialist_b2_completed"] = True

    # Check if both specialists under Manager B have completed their tasks
    if context_variables["specialist_b1_completed"] and context_variables["specialist_b2_completed"]:
        context_variables["manager_b_completed"] = True

    return ReplyResult(
        message="Geothermal research completed and stored.",
        context_variables=context_variables,
        target=AgentTarget(storage_manager),
    )

def complete_biofuel_research(research_content: str, context_variables: ContextVariables) -> ReplyResult:
    """Submit biofuel research findings"""
    context_variables["biofuel_research"] = research_content
    context_variables["specialist_c1_completed"] = True
    context_variables["manager_c_completed"] = True

    return ReplyResult(
        message="Biofuel research completed and stored.",
        context_variables=context_variables,
        target=AgentTarget(alternative_manager),
    )

# ========================
# SPECIALIST AGENTS
# ========================
specialist_a1 = ConversableAgent(
    name="solar_specialist",
    system_message="""You are a specialist in solar energy technologies.
    Your task is to research and provide concise information about:
    1. Current state of solar technology
    2. Efficiency rates of different types of solar panels
    3. Cost comparison with fossil fuels
    4. Major companies and countries leading in solar energy

    Be thorough but concise. Your research will be used as part of a larger report.

    Use your tools only one at a time.""",
    functions = [complete_solar_research],
    llm_config=llm_config
)

specialist_a2 = ConversableAgent(
    name="wind_specialist",
    system_message="""You are a specialist in wind energy technologies.
    Your task is to research and provide concise information about:
    1. Current state of wind technology (onshore/offshore)
    2. Efficiency rates of modern wind turbines
    3. Cost comparison with fossil fuels
    4. Major companies and countries leading in wind energy

    Be thorough but concise. Your research will be used as part of a larger report.

    Use your tools only one at a time.""",
    functions = [complete_wind_research],
    llm_config=llm_config
)

specialist_b1 = ConversableAgent(
    name="hydro_specialist",
    system_message="""You are a specialist in hydroelectric energy technologies.
    Your task is to research and provide concise information about:
    1. Current state of hydroelectric technology
    2. Types of hydroelectric generation (dams, run-of-river, pumped storage)
    3. Cost comparison with fossil fuels
    4. Major companies and countries leading in hydroelectric energy

    Be thorough but concise. Your research will be used as part of a larger report.

    Use your tools only one at a time.""",
    functions = [complete_hydro_research],
    llm_config=llm_config
)

specialist_b2 = ConversableAgent(
    name="geothermal_specialist",
    system_message="""You are a specialist in geothermal energy technologies.
    Your task is to research and provide concise information about:
    1. Current state of geothermal technology
    2. Types of geothermal systems and efficiency rates
    3. Cost comparison with fossil fuels
    4. Major companies and countries leading in geothermal energy

    Be thorough but concise. Your research will be used as part of a larger report.

    Use your tools only one at a time.""",
    functions = [complete_geothermal_research],
    llm_config=llm_config
)

specialist_c1 = ConversableAgent(
    name="biofuel_specialist",
    system_message="""You are a specialist in biofuel technologies.
    Your task is to research and provide concise information about:
    1. Current state of biofuel technology
    2. Types of biofuels and their applications
    3. Cost comparison with fossil fuels
    4. Major companies and countries leading in biofuel production

    Be thorough but concise. Your research will be used as part of a larger report.

    Use your tools only one at a time.""",
    functions = [complete_biofuel_research],
    llm_config=llm_config
)

# ========================
# MANAGER FUNCTIONS
# ========================

def compile_renewable_section(section_content: str, context_variables: ContextVariables) -> ReplyResult:
    """Compile the renewable energy section (solar and wind) for the final report"""
    context_variables["report_sections"]["renewable"] = section_content

    # Check if all managers have submitted their sections
    if all(key in context_variables["report_sections"] for key in ["renewable", "storage", "alternative"]):
        context_variables["executive_review_ready"] = True
        return ReplyResult(
            message="Renewable energy section compiled. All sections are now ready for executive review.",
            context_variables=context_variables,
            target=AgentTarget(executive_agent),
        )
    else:
        return ReplyResult(
            message="Renewable energy section compiled and stored.",
            context_variables=context_variables,
            target=AgentTarget(executive_agent),
        )

def compile_storage_section(section_content: str, context_variables: ContextVariables) -> ReplyResult:
    """Compile the energy storage section (hydro and geothermal) for the final report"""
    context_variables["report_sections"]["storage"] = section_content

    # Check if all managers have submitted their sections
    if all(key in context_variables["report_sections"] for key in ["renewable", "storage", "alternative"]):
        context_variables["executive_review_ready"] = True
        return ReplyResult(
            message="Energy storage section compiled. All sections are now ready for executive review.",
            context_variables=context_variables,
            target=AgentTarget(executive_agent),
        )
    else:
        return ReplyResult(
            message="Energy storage section compiled and stored.",
            context_variables=context_variables,
            target=AgentTarget(executive_agent),
        )

def compile_alternative_section(section_content: str, context_variables: ContextVariables) -> ReplyResult:
    """Compile the alternative energy section (biofuels) for the final report"""
    context_variables["report_sections"]["alternative"] = section_content

    # Check if all managers have submitted their sections
    if all(key in context_variables["report_sections"] for key in ["renewable", "storage", "alternative"]):
        context_variables["executive_review_ready"] = True
        return ReplyResult(
            message="Alternative energy section compiled. All sections are now ready for executive review.",
            context_variables=context_variables,
            target=AgentTarget(executive_agent),
        )
    else:
        return ReplyResult(
            message="Alternative energy section compiled and stored.",
            context_variables=context_variables,
            target=AgentTarget(executive_agent),
        )

# ========================
# MANAGER AGENTS
# ========================
renewable_manager = ConversableAgent(
    name="renewable_manager",
    system_message="""You are the manager for renewable energy research, specifically overseeing solar and wind energy specialists.
    Your responsibilities include:
    1. Reviewing the research from your specialists
    2. Ensuring the information is accurate and comprehensive
    3. Synthesizing the information into a cohesive section on renewable energy
    4. Submitting the compiled research to the executive for final report creation

    You should wait until both specialists have completed their research before compiling your section.

    Use your tools only one at a time.""",
    functions = [compile_renewable_section],
    llm_config=llm_config
)

storage_manager = ConversableAgent(
    name="storage_manager",
    system_message="""You are the manager for energy storage and hydroelectric technologies, overseeing hydroelectric and geothermal energy specialists.
    Your responsibilities include:
    1. Reviewing the research from your specialists
    2. Ensuring the information is accurate and comprehensive
    3. Synthesizing the information into a cohesive section on energy storage and hydroelectric solutions
    4. Submitting the compiled research to the executive for final report creation

    You should wait until both specialists have completed their research before compiling your section.

    Use your tools only one at a time.""",
    functions = [compile_storage_section],
    llm_config=llm_config
)

alternative_manager = ConversableAgent(
    name="alternative_manager",
    system_message="""You are the manager for alternative energy solutions, overseeing biofuel research.
    Your responsibilities include:
    1. Reviewing the research from your specialist
    2. Ensuring the information is accurate and comprehensive
    3. Synthesizing the information into a cohesive section on alternative energy solutions
    4. Submitting the compiled research to the executive for final report creation

    Use your tools only one at a time.""",
    functions = [compile_alternative_section],
    llm_config=llm_config
)

# ========================
# EXECUTIVE FUNCTIONS
# ========================

def initiate_research(context_variables: ContextVariables) -> ReplyResult:
    """Initiate the research process by delegating to managers"""
    context_variables["task_started"] = True

    return ReplyResult(
        message="Research initiated. Tasks have been delegated to the renewable energy manager, storage manager, and alternative energy manager.",
        context_variables=context_variables
    )

def compile_final_report(report_content: str, context_variables: ContextVariables) -> ReplyResult:
    """Compile the final comprehensive report from all sections"""
    context_variables["final_report"] = report_content
    context_variables["task_completed"] = True

    return ReplyResult(
        message="Final report compiled successfully. The comprehensive renewable energy report is now complete.",
        context_variables=context_variables,
        target=AgentTarget(user)  # Return to user with final report
    )

# ========================
# EXECUTIVE AGENT
# ========================
executive_agent = ConversableAgent(
    name="executive_agent",
    system_message="""You are the executive overseeing the creation of a comprehensive report on renewable energy technologies.

    You have exactly three manager agents reporting to you, each responsible for specific technology domains:
    1. Renewable Manager - Oversees solar and wind energy research
    2. Storage Manager - Oversees hydroelectric and geothermal energy research
    3. Alternative Manager - Oversees biofuel research

    Your responsibilities include:
    1. Delegating research tasks to these three specific manager agents
    2. Providing overall direction and ensuring alignment with the project goals
    3. Reviewing the compiled sections from each manager
    4. Synthesizing all sections into a cohesive final report with executive summary
    5. Ensuring the report is comprehensive, balanced, and meets high-quality standards

    Do not create or attempt to delegate to managers that don't exist in this structure.

    The final report should include:
    - Executive Summary
    - Introduction to Renewable Energy
    - Three main sections:
    * Solar and Wind Energy (from Renewable Manager)
    * Hydroelectric and Geothermal Energy (from Storage Manager)
    * Biofuel Technologies (from Alternative Manager)
    - Comparison of technologies
    - Future outlook and recommendations""",
    functions = [initiate_research, compile_final_report],
    llm_config=llm_config
)

# ========================
# HANDOFFS REGISTRATION
# ========================

# Executive Agent handoffs
# Using OnContextCondition for task delegation based on context variables
# This eliminates the need for LLM-based decisions for simple routing
executive_agent.handoffs.add_context_conditions(
    [
        OnContextCondition(
            target=AgentTarget(renewable_manager),
            condition=ExpressionContextCondition(ContextExpression("not(${manager_a_completed})")),
            available=ExpressionAvailableCondition(ContextExpression("${task_started} == True")),
        ),
        OnContextCondition(
            target=AgentTarget(storage_manager),
            condition=ExpressionContextCondition(ContextExpression("not(${manager_b_completed})")),
            available=ExpressionAvailableCondition(ContextExpression("${task_started} == True")),
        ),
        OnContextCondition(
            target=AgentTarget(alternative_manager),
            condition=ExpressionContextCondition(ContextExpression("not(${manager_c_completed})")),
            available=ExpressionAvailableCondition(ContextExpression("${task_started} == True")),
        )
    ]
)
executive_agent.handoffs.set_after_work(RevertToUserTarget())

# Renewable Manager handoffs - uses context expressions for more efficient decision-making
renewable_manager.handoffs.add_many(
    [
        # Context-based handoffs for specialist delegation
        OnContextCondition(
            target=AgentTarget(specialist_a1),
            condition=ExpressionContextCondition(ContextExpression("not(${specialist_a1_completed})")),
            available=ExpressionAvailableCondition(ContextExpression("${task_started} == True")),
        ),
        OnContextCondition(
            target=AgentTarget(specialist_a2),
            condition=ExpressionContextCondition(ContextExpression("not(${specialist_a2_completed})")),
            available=ExpressionAvailableCondition(ContextExpression("${task_started} == True")),
        ),
        OnCondition(
            target=AgentTarget(executive_agent),
            condition=StringLLMCondition("Return to the executive after your report has been compiled."),
            available=ExpressionAvailableCondition(ContextExpression("${manager_a_completed} == True")),
        ),
    ]
)
renewable_manager.handoffs.set_after_work(AgentTarget(executive_agent))  # After work, return to executive)

# Storage Manager handoffs - similar pattern of context-based and LLM-based handoffs
storage_manager.handoffs.add_many(
    [
        # Context-based handoffs for specialist delegation
        OnContextCondition(
            target=AgentTarget(specialist_b1),
            condition=ExpressionContextCondition(ContextExpression("not(${specialist_b1_completed})")),
            available=ExpressionAvailableCondition(ContextExpression("${task_started} == True")),
        ),
        OnContextCondition(
            target=AgentTarget(specialist_b2),
            condition=ExpressionContextCondition(ContextExpression("not(${specialist_b2_completed})")),
            available=ExpressionAvailableCondition(ContextExpression("${task_started} == True")),
        ),
        OnCondition(
            target=AgentTarget(executive_agent),
            condition=StringLLMCondition("Return to the executive after your report has been compiled."),
            available=ExpressionAvailableCondition(ContextExpression("${manager_b_completed} == True")),
        ),
    ]
)
# After work, return to executive
storage_manager.handoffs.set_after_work(AgentTarget(executive_agent))

# Alternative Manager handoffs - combination of context-based and LLM-based handoffs
alternative_manager.handoffs.add_many(
    [
        # Context-based handoffs for specialist delegation
        OnContextCondition(
            target=AgentTarget(specialist_c1),
            condition=ExpressionContextCondition(ContextExpression("not(${specialist_c1_completed})")),
            available=ExpressionAvailableCondition(ContextExpression("${task_started} == True")),
        ),
        OnCondition(
            target=AgentTarget(executive_agent),
            condition=StringLLMCondition("Return to the executive with the compiled alternative energy section"),
            available=ExpressionAvailableCondition(ContextExpression("${manager_c_completed} == True")),
        ),
    ]
)
alternative_manager.handoffs.set_after_work(AgentTarget(executive_agent))  # After work, return to executive

# Specialists handoffs back to their managers based on task completion
specialist_a1.handoffs.set_after_work(AgentTarget(renewable_manager))
specialist_a2.handoffs.set_after_work(AgentTarget(renewable_manager))
specialist_b1.handoffs.set_after_work(AgentTarget(storage_manager))
specialist_b2.handoffs.set_after_work(AgentTarget(storage_manager))
specialist_c1.handoffs.set_after_work(AgentTarget(alternative_manager))

# ========================
# INITIATE THE GROUP CHAT
# ========================

def run_hierarchical_chat():
    """Run the hierarchical group chat to generate a renewable energy report"""
    print("Initiating Hierarchical Group Chat for Renewable Energy Report...")

    agent_pattern = DefaultPattern(
        initial_agent=executive_agent,
        agents=[
            # Executive level
            executive_agent,
            # Manager level
            renewable_manager, storage_manager, alternative_manager,
            # Specialist level
            specialist_a1, specialist_a2, specialist_b1, specialist_b2, specialist_c1
        ],
        context_variables=shared_context,
        group_after_work=TerminateTarget(),  # Default fallback if agent doesn't specify
        user_agent=user,
    )

    # Provide default after_work option that aligns with hierarchical pattern
    chat_result, final_context, last_agent = initiate_group_chat(
        pattern=agent_pattern,
        messages="We need a comprehensive report on the current state of renewable energy technologies. Please coordinate the research and compilation of this report.",
        max_rounds=50,
    )

    # The final report will be stored in final_context["final_report"]
    if final_context["task_completed"]:
        print("Report generation completed successfully!")
        print("\n===== FINAL REPORT =====\n")
        print(final_context["final_report"])
        print("\n\n===== FINAL CONTEXT VARIABLES =====\n")
        print(json.dumps(final_context.to_dict(), indent=2))
        print("\n\n===== SPEAKER ORDER =====\n")
        for message in chat_result.chat_history:
            if "name" in message and message["name"] != "_Group_Tool_Executor":
                print(f"{message['name']}")
    else:
        print("Report generation did not complete successfully.")

if __name__ == "__main__":
    run_hierarchical_chat()