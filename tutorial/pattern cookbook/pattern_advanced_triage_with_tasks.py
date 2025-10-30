from copy import deepcopy
from enum import Enum
from typing import Annotated, Any, List, Tuple
from pydantic import BaseModel, Field
from autogen import (
    ConversableAgent,
    UpdateSystemMessage,
    ChatResult,
    LLMConfig
)
from autogen.agentchat import initiate_group_chat
from autogen.agentchat.group.patterns import DefaultPattern
from autogen.agentchat.group import ContextVariables, ReplyResult, AgentNameTarget, AgentTarget, OnContextCondition, ExpressionContextCondition, StayTarget, TerminateTarget, ContextExpression

# === STRUCTURED DATA MODELS ===

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class ResearchTask(BaseModel):
    topic: str = Field(description="Topic to research")
    details: str = Field(description="Specific details or questions to research")
    priority: TaskPriority = Field(description="Priority level of the task")

class WritingTask(BaseModel):
    topic: str = Field(description="Topic to write about")
    type: str = Field(description="Type of writing (article, email, report, etc.)")
    details: str = Field(description="Details or requirements for the writing task")
    priority: TaskPriority = Field(description="Priority level of the task")

class TaskAssignment(BaseModel):
    """Structured output for task triage decisions."""
    research_tasks: List[ResearchTask] = Field(description="List of research tasks to complete first")
    writing_tasks: List[WritingTask] = Field(description="List of writing tasks to complete after research")

# === AGENTS ===

# Task Manager
TASK_MANAGER_NAME = "TaskManagerAgent"
TASK_MANAGER_SYSTEM_MESSAGE = """
You are a task manager. Your responsibilities include:

1. Initialize tasks from the TriageAgent using the initiate_tasks tool
2. Route research tasks to the ResearchAgent (complete ALL research tasks first)
3. Route writing tasks to the WritingAgent (only after ALL research tasks are done)
4. Hand off to the SummaryAgent when all tasks are complete

Use tools to transfer to the appropriate agent based on the context variables.
Only call tools once in your response.
"""

# Research Agent
RESEARCH_AGENT_SYSTEM_MESSAGE = """
You are a research specialist who gathers information on various topics.

When assigned a research task:
1. Analyze the topic and required details
2. Provide comprehensive and accurate information
3. Focus on facts and reliable information
4. Use the complete_research_task tool to submit your findings

Be thorough but concise, and ensure your research is relevant to the specific request.
"""

# Writing Agent
WRITING_AGENT_SYSTEM_MESSAGE = """
You are a writing specialist who creates various types of content.

When assigned a writing task:
1. Review the topic, type, and requirements
2. Create well-structured, engaging content
3. Adapt your style to the specified type (article, email, report, etc.)
4. Use the complete_writing_task tool to submit your work

Focus on quality, clarity, and meeting the specific requirements of each task.
"""

# Summary Agent
SUMMARY_AGENT_SYSTEM_MESSAGE = """
You provide clear summaries of completed tasks.

Format your summary as follows:
1. Total research tasks completed
2. Total writing tasks completed
3. Brief overview of each completed task

Be concise and focus on the most important details and outcomes.
"""

# Error Agent
ERROR_AGENT_NAME = "ErrorAgent"
ERROR_AGENT_SYSTEM_MESSAGE = """
You communicate errors to the user. Include the original error messages in full.
Use the format:
The following error(s) occurred while processing your request:
- Error 1
- Error 2
"""

# === TOOL FUNCTIONS ===

def initiate_tasks(
    research_tasks: list[ResearchTask],
    writing_tasks: list[WritingTask],
    context_variables: ContextVariables,
) -> ReplyResult:
    """Initialize the task processing based on triage assessment."""
    if "TaskInitiated" in context_variables:
        return ReplyResult(
            message="Task already initiated",
            context_variables=context_variables
        )

    # Process tasks
    formatted_research_tasks = []
    for i, task in enumerate(research_tasks):
        formatted_research_tasks.append({
            "index": i,
            "topic": task.topic,
            "details": task.details,
            "priority": task.priority,
            "status": "pending",
            "output": None
        })

    formatted_writing_tasks = []
    for i, task in enumerate(writing_tasks):
        formatted_writing_tasks.append({
            "index": i,
            "topic": task.topic,
            "type": task.type,
            "details": task.details,
            "priority": task.priority,
            "status": "pending",
            "output": None
        })

    # Sort tasks by priority
    for task_list in [formatted_research_tasks, formatted_writing_tasks]:
        task_list.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["priority"]])

    # Update context variables
    context_variables["ResearchTasks"] = formatted_research_tasks
    context_variables["WritingTasks"] = formatted_writing_tasks
    context_variables["CurrentResearchTaskIndex"] = -1 if not formatted_research_tasks else 0
    context_variables["CurrentWritingTaskIndex"] = -1 if not formatted_writing_tasks else 0
    context_variables["ResearchTasksCompleted"] = []
    context_variables["WritingTasksCompleted"] = []
    context_variables["TaskInitiated"] = True

    return ReplyResult(
        message="Initialized tasks for processing",
        context_variables=context_variables,
        target=AgentNameTarget(TASK_MANAGER_NAME),
    )

def complete_research_task(
    index: Annotated[int, "Research task index"],
    topic: Annotated[str, "Research topic"],
    findings: Annotated[str, "Research findings"],
    context_variables: ContextVariables,
) -> ReplyResult:
    """Complete a research task with findings."""
    try:
        current_index = context_variables["CurrentResearchTaskIndex"]

        if index != current_index:
            return ReplyResult(
                message=f"The index provided, {index}, does not match the current writing task index, {current_index}.",
                context_variables=context_variables,
                target=AgentNameTarget(TASK_MANAGER_NAME),
            )

        if current_index == -1:
            return ReplyResult(
                message="No current research task to complete.",
                context_variables=context_variables,
                target=AgentNameTarget(TASK_MANAGER_NAME),
            )

        current_task = context_variables["ResearchTasks"][current_index]

        # Update task status
        current_task["status"] = "completed"
        current_task["topic"] = topic
        current_task["output"] = findings

        # Move task to completed list
        context_variables["ResearchTasksCompleted"].append(current_task)

        # Move to the next research task, if there is one.
        if current_index + 1 >= len(context_variables["ResearchTasks"]):
            # No more tasks
            context_variables["ResearchTasksDone"] = True
            context_variables["CurrentResearchTaskIndex"] = -1
        else:
            # Move to the next task
            context_variables["CurrentResearchTaskIndex"] = current_index + 1

        return ReplyResult(
            message=f"Research task completed: {topic}",
            context_variables=context_variables,
        )
    except Exception as e:
        return ReplyResult(
            message=f"Error occurred with research task #{index}: {str(e)}",
            context_variables=context_variables,
            target=AgentNameTarget(ERROR_AGENT_NAME),
        )

def complete_writing_task(
    index: Annotated[int, "Writing task index"],
    topic: Annotated[str, "Writing topic"],
    findings: Annotated[str, "Writing findings"],
    context_variables: ContextVariables,
) -> ReplyResult:
    """Complete a writing task with content."""
    try:
        current_index = context_variables["CurrentWritingTaskIndex"]

        if index != current_index:
            return ReplyResult(
                message=f"The index provided, {index}, does not match the current writing task index, {current_index}.",
                context_variables=context_variables,
                target=AgentNameTarget(TASK_MANAGER_NAME),
            )

        if current_index == -1:
            return ReplyResult(
                message="No current writing task to complete.",
                context_variables=context_variables,
                target=AgentNameTarget(TASK_MANAGER_NAME),
            )

        current_task = context_variables["WritingTasks"][current_index]

        # Update task status
        current_task["status"] = "completed"
        current_task["topic"] = topic
        current_task["output"] = findings

        # Move task to completed list
        context_variables["WritingTasksCompleted"].append(current_task)

        # Move to the next research task, if there is one.
        if current_index + 1 >= len(context_variables["WritingTasks"]):
            # No more tasks
            context_variables["WritingTasksDone"] = True
            context_variables["CurrentWritingTaskIndex"] = -1
        else:
            # Move to the next task
            context_variables["CurrentWritingTaskIndex"] = current_index + 1

        return ReplyResult(
            message=f"Writing task completed: {topic}",
            context_variables=context_variables,
        )
    except Exception as e:
        return ReplyResult(
            message=f"Error occurred with writing task #{index}: {str(e)}",
            context_variables=context_variables,
            target=AgentNameTarget(ERROR_AGENT_NAME),
        )

# Create the agents for the group chat
def create_research_writing_group_chat(llm_config_base: dict[str, Any]):
    """Create and configure all agents for the research-writing group chat."""

    # Triage agent
    structured_config = deepcopy(llm_config_base)
    structured_config["config_list"][0]["response_format"] = TaskAssignment

    triage_agent = ConversableAgent(
        name="triage_agent",
        llm_config=structured_config,
        system_message=(
            "You are a task triage agent. You analyze requests and break them down into tasks.\n"
            "For each request, identify two types of tasks:\n"
            "1. Research tasks: Topics that need information gathering before writing\n"
            "2. Writing tasks: Content creation tasks that may depend on the research\n\n"
            "Structure all tasks with appropriate details and priority levels.\n"
            "Research tasks will be completed first, followed by writing tasks."
        ),
    )

    llm_config_with_tools = LLMConfig(config_list={"model": "gpt-4.1-mini", "api_type": "openai", "parallel_tool_calls": False})

    # Task Manager agent
    task_manager_agent = ConversableAgent(
        name=TASK_MANAGER_NAME,
        system_message=TASK_MANAGER_SYSTEM_MESSAGE,
        llm_config=llm_config_with_tools,
        functions=[initiate_tasks],
    )

    # Define the system message generation for the research agent, getting the next research task
    def create_research_agent_prompt(agent: ConversableAgent, messages: list[dict[str, Any]]) -> str:
        """Create the research agent prompt with the current research task."""
        current_research_index = agent.context_variables.get("CurrentResearchTaskIndex", -1)
        research_tasks = agent.context_variables.get("ResearchTasks")

        if current_research_index >= 0:

            current_task = research_tasks[current_research_index]
            return (f"{RESEARCH_AGENT_SYSTEM_MESSAGE}"
                "\n\n"
                f"Research Task:\n"
                f"Index: {current_research_index}:\n"
                f"Topic: {current_task['topic']}\n"
                f"Details: {current_task['details']}\n"
            )
        else:
            return "No more research tasks to process."

    # Research agent
    research_agent = ConversableAgent(
        name="ResearchAgent",
        system_message=RESEARCH_AGENT_SYSTEM_MESSAGE,
        llm_config=llm_config_with_tools,
        functions=[complete_research_task],
        update_agent_state_before_reply=[UpdateSystemMessage(create_research_agent_prompt)],
    )

    # Define the system message generation for the writing agent, getting the next writing task
    def create_writing_agent_prompt(agent: ConversableAgent, messages: list[dict[str, Any]]) -> str:
        """Create the writing agent prompt with the current writing task."""
        current_writing_index = agent.context_variables.get("CurrentWritingTaskIndex", -1)
        writing_tasks = agent.context_variables.get("WritingTasks")

        if current_writing_index >= 0:

            current_task = writing_tasks[current_writing_index]
            return (f"{WRITING_AGENT_SYSTEM_MESSAGE}"
                "\n\n"
                f"Writing Task:\n"
                f"Index: {current_writing_index}:\n"
                f"Topic: {current_task['topic']}\n"
                f"Type: {current_task['type']}\n"
                f"Details: {current_task['details']}\n"
            )
        else:
            return "No more writing tasks to process."

    # Writing agent
    writing_agent = ConversableAgent(
        name="WritingAgent",
        system_message=WRITING_AGENT_SYSTEM_MESSAGE,
        llm_config=llm_config_with_tools,
        functions=[complete_writing_task],
        update_agent_state_before_reply=[UpdateSystemMessage(create_writing_agent_prompt)],
    )

    # Summary agent
    def create_summary_agent_prompt(agent: ConversableAgent, messages: list[dict[str, Any]]) -> str:
        """Create the summary agent prompt with task completion results."""
        research_tasks = agent.context_variables.get("ResearchTasksCompleted")
        writing_tasks = agent.context_variables.get("WritingTasksCompleted")

        system_message = (
            "You are a task summary specialist. Provide a summary of all completed tasks.\n\n"
            f"Research Tasks Completed: {len(research_tasks)}\n"
            f"Writing Tasks Completed: {len(writing_tasks)}\n\n"
            "Task Details:\n\n"
        )

        if research_tasks:
            system_message += "RESEARCH TASKS:\n"
            for i, task in enumerate(research_tasks, 1):
                system_message += (
                    f"{i}. Topic: {task['topic']}\n"
                    f"   Priority: {task['priority']}\n"
                    f"   Details: {task['details']}\n"
                    f"   Findings: {task['output'][:200]}...\n\n"
                )

        if writing_tasks:
            system_message += "WRITING TASKS:\n"
            for i, task in enumerate(writing_tasks, 1):
                system_message += (
                    f"{i}. Topic: {task['topic']}\n"
                    f"   Type: {task['type']}\n"
                    f"   Priority: {task['priority']}\n"
                    f"   Content: {task['output'][:200]}...\n\n"
                )

        return system_message

    # Create the summary agent
    summary_agent = ConversableAgent(
        name="SummaryAgent",
        llm_config=llm_config_base,
        system_message=SUMMARY_AGENT_SYSTEM_MESSAGE,
        update_agent_state_before_reply=[UpdateSystemMessage(create_summary_agent_prompt)],
    )

    # Create the error agent
    error_agent = ConversableAgent(
        name=ERROR_AGENT_NAME,
        system_message=ERROR_AGENT_SYSTEM_MESSAGE,
        llm_config=llm_config_base,
    )

    # Set up handoffs between agents

    # Triage agent always hands off to the Task Manager
    triage_agent.handoffs.set_after_work(AgentTarget(task_manager_agent))

    # Task Manager routes to Research and Writing agents if they have tasks
    # then to the Summary agent if the tasks are done
    task_manager_agent.handoffs.add_context_conditions(
        [
            OnContextCondition(
                target=AgentTarget(research_agent),
                condition=ExpressionContextCondition(ContextExpression("${CurrentResearchTaskIndex} >= 0")),
            ),
            OnContextCondition(
                target=AgentTarget(writing_agent),
                condition=ExpressionContextCondition(ContextExpression("${CurrentWritingTaskIndex} >= 0")),
            ),
            OnContextCondition(
                target=AgentTarget(summary_agent),
                condition=ExpressionContextCondition(ContextExpression("${ResearchTasksDone} and ${WritingTasksDone}")),
            ),
        ]
    )

    task_manager_agent.handoffs.set_after_work(StayTarget())

    # Research agent hands back to the Task Manager if they have no more tasks
    research_agent.handoffs.add_context_condition(
        OnContextCondition(
            target=AgentTarget(task_manager_agent),
            condition=ExpressionContextCondition(ContextExpression("${CurrentResearchTaskIndex} == -1")),
        ),
    )
    research_agent.handoffs.set_after_work(AgentTarget(task_manager_agent))

    # Writing agent hands back to the Task Manager if they have no more tasks
    writing_agent.handoffs.add_context_condition(
        OnContextCondition(
            target=AgentTarget(task_manager_agent),
            condition=ExpressionContextCondition(ContextExpression("${CurrentWritingTaskIndex} == -1")),
        ),
    )
    writing_agent.handoffs.set_after_work(AgentTarget(task_manager_agent))

    # The Summary Agent will summarize and then terminate
    summary_agent.handoffs.set_after_work(TerminateTarget())

    # If an error occurs, hand off to the Error Agent
    error_agent.handoffs.set_after_work(TerminateTarget())

    # Return all the agents
    return {
        "triage_agent": triage_agent,
        "task_manager_agent": task_manager_agent,
        "research_agent": research_agent,
        "writing_agent": writing_agent,
        "summary_agent": summary_agent,
        "error_agent": error_agent
    }

# Function to run the group chat
def run_research_writing(user_request: str) -> Tuple[ChatResult, ContextVariables]:
    """Run the research and writing group chat for a given user request."""

    llm_config_base = {
        "config_list": [{"model": "gpt-4.1-mini", "api_type": "openai"}],
    }

    # Create the agents
    agents = create_research_writing_group_chat(llm_config_base)

    # Set up initial context variables
    context_variables = ContextVariables({
        "CurrentResearchTaskIndex": -1,
        "CurrentWritingTaskIndex": -1,
        "ResearchTasksDone": False,
        "WritingTasksDone": False,
    })

    # Get all agents as a list
    all_agents = list(agents.values())

    agent_pattern = DefaultPattern(
        initial_agent=agents["triage_agent"],
        agents=all_agents,
        context_variables=context_variables,
        group_after_work=TerminateTarget()
    )

    # Run the group chat
    chat_result, final_context, _ = initiate_group_chat(
        pattern=agent_pattern,
        messages=user_request,
        max_rounds=100,
    )

    # Return the results
    return chat_result, final_context

# Example usage
if __name__ == "__main__":
    # Sample request
    request = "I need to write about climate change solutions. Can you help me research solar panels and wind farms and then write two articles a blog and a longer form article summarizing the state of these two technologies."

    # Run the group chat
    result, final_context = run_research_writing(request)

    # Display the Research
    print("\n===== RESEARCH =====\n")
    for i, research_task in enumerate(final_context["ResearchTasksCompleted"]):
        print(f"{research_task['index']}. Topic: {research_task['topic']}")
        print(f"Details: {research_task['details']}")
        print(f"Research: {research_task['output']}\n\n")

    # Display the Writing
    print("\n===== WRITING =====\n")
    for i, writing_task in enumerate(final_context["WritingTasksCompleted"]):
        print(f"{writing_task['index']}. Topic: {writing_task['topic']}")
        print(f"Type: {writing_task['type']}")
        print(f"Details: {writing_task['details']}")
        print(f"Content: {writing_task['output']}\n\n")

    # Print the result
    print("===== SUMMARY =====")
    print(result.summary)

    # Display the conversation flow
    print("\n===== SPEAKER ORDER =====\n")
    for message in result.chat_history:
        if "name" in message and message["name"] != "_Group_Tool_Executor":
            print(f"{message['name']}")