from typing import Any, Annotated
from autogen import (
    ConversableAgent,
    UserProxyAgent,
    LLMConfig,
)
from autogen.agentchat import initiate_group_chat
from autogen.agentchat.group.patterns import DefaultPattern
from autogen.agentchat.group import ContextVariables, ReplyResult, RevertToUserTarget, OnContextCondition, ContextExpression, ExpressionContextCondition, NestedChatTarget, AgentTarget, ExpressionAvailableCondition

# Redundant Pattern:
# Multiple agents attempt the same task using different approaches,
# then results are compared to select the best outcome or combine strengths
# Agents respond in isolation through a nested chat

# Setup LLM configuration
llm_config = LLMConfig(config_list={"api_type": "openai", "model": "gpt-4.1-mini", "cache_seed": None})

# Shared context for tracking the conversation and redundant agent results
shared_context = ContextVariables(data={
    # Process state
    "task_initiated": False,
    "task_completed": False,
    "evaluation_complete": False,

    # Task tracking
    "current_task": "",
    "task_type": None,  # Can be "creative", "problem_solving", "factual", etc.
    "approach_count": 0,

    # Results from different agents
    "agent_a_result": None,
    "agent_b_result": None,
    "agent_c_result": None,

    # Evaluation metrics
    "evaluation_scores": {},
    "final_result": None,
    "selected_approach": None,

    # Error state (not handled but could be used to route to an error agent)
    "has_error": False,
    "error_message": "",
    "error_source": ""
})

# Function to initiate task processing
def initiate_task(
    task: Annotated[str, "The task to be processed by multiple agents"],
    task_type: Annotated[str, "Type of task: 'creative', 'problem_solving', 'factual', etc."],
    context_variables: ContextVariables
) -> ReplyResult:
    """
    Initiate processing of a task across multiple redundant agents with different approaches
    """
    context_variables["task_initiated"] = True
    context_variables["task_completed"] = False
    context_variables["evaluation_complete"] = False
    context_variables["current_task"] = task
    context_variables["task_type"] = task_type

    # Reset previous results
    context_variables["agent_a_result"] = None
    context_variables["agent_b_result"] = None
    context_variables["agent_c_result"] = None
    context_variables["evaluation_scores"] = {}
    context_variables["final_result"] = None
    context_variables["selected_approach"] = None

    return ReplyResult(
        message=f"Task initiated: '{task}' (Type: {task_type}). Will process with multiple independent approaches.",
        context_variables=context_variables
    )

# Function for evaluator provide their evaluation and select the best result
def evaluate_and_select(
    evaluation_notes: Annotated[str, "Detailed evaluation of each agent's result"],
    score_a: Annotated[int, "Score for Agent A's approach (1-10 scale)"],
    score_b: Annotated[int, "Score for Agent B's approach (1-10 scale)"],
    score_c: Annotated[int, "Score for Agent C's approach (1-10 scale)"],
    selected_result: Annotated[str, "The selected or synthesized final result"],
    selection_rationale: Annotated[str, "Explanation for why this result was selected or how it was synthesized"],
    context_variables: ContextVariables
) -> ReplyResult:
    """
    Evaluate the different approaches and select or synthesize the best result
    """
    # Create scores dictionary from individual parameters
    scores = {
        "agent_a": score_a,
        "agent_b": score_b,
        "agent_c": score_c
    }

    context_variables["evaluation_notes"] = evaluation_notes
    context_variables["evaluation_scores"] = scores
    context_variables["final_result"] = selected_result
    context_variables["evaluation_complete"] = True

    # Determine which approach was selected (highest score)
    max_score = 0
    selected_approach = None
    for agent, score in scores.items():
        if score > max_score:
            max_score = score
            selected_approach = agent
    context_variables["selected_approach"] = selected_approach

    return ReplyResult(
        message=f"Evaluation complete. Selected result: {selection_rationale[:100]}...",
        context_variables=context_variables,
        target=RevertToUserTarget()
    )

# Create the agents for the redundant pattern
taskmaster_agent = ConversableAgent(
    name="taskmaster_agent",
    system_message="""You are the Task Manager responsible for initiating tasks and coordinating the redundant pattern workflow.

    Your role is to:
    1. Understand the user's request and frame it as a clear task
    2. Determine the appropriate task type (creative, problem_solving, factual)
    3. Initiate the task to be processed by multiple independent agents
    4. Return to the user with the final selected or synthesized result

    For each request:
    1. Use the initiate_task tool to start the process
    2. After all agents have submitted their results and evaluation is complete, present the final result to the user

    Always explain to the user that their task is being processed by multiple approaches to ensure the best possible outcome.""",
    functions=[initiate_task],
    llm_config=llm_config
)

# Define the agent names so we can refer to them in the context variables
redundant_agent_names = ["agent_a", "agent_b", "agent_c"]

agent_a = ConversableAgent(
    name="agent_a",
    system_message="""You are Agent A, specializing in a structured, analytical approach to tasks.

    For creative tasks:
    - Use structured frameworks and established patterns
    - Follow proven methodologies and best practices
    - Focus on clarity, organization, and logical progression

    For problem-solving tasks:
    - Use first principles thinking and systematic analysis
    - Break down problems into component parts
    - Consider established solutions and scientific approaches

    For factual information:
    - Prioritize objective, verifiable data
    - Present information in a structured, hierarchical manner
    - Focus on accuracy and comprehensiveness

    Always identify your approach clearly and explain your methodology as part of your response.""",
    llm_config=llm_config
)

agent_b = ConversableAgent(
    name="agent_b",
    system_message="""You are Agent B, specializing in a creative, lateral-thinking approach to tasks.

    For creative tasks:
    - Use metaphors, analogies, and unexpected connections
    - Think outside conventional frameworks
    - Explore unique perspectives and novel combinations

    For problem-solving tasks:
    - Use creative ideation and divergent thinking
    - Look for non-obvious connections and innovative approaches
    - Consider unconventional solutions outside the mainstream

    For factual information:
    - Present information through narratives and examples
    - Use contextual understanding and practical applications
    - Focus on making information relatable and engaging

    Always identify your approach clearly and explain your methodology as part of your response.""",
    llm_config=llm_config
)

agent_c = ConversableAgent(
    name="agent_c",
    system_message="""You are Agent C, specializing in a thorough, comprehensive approach to tasks.

    For creative tasks:
    - Combine multiple perspectives and diverse inputs
    - Draw from cross-disciplinary knowledge and varied examples
    - Focus on thoroughness and covering all possible angles

    For problem-solving tasks:
    - Consider multiple solution pathways simultaneously
    - Evaluate trade-offs and present alternative approaches
    - Focus on robustness and addressing edge cases

    For factual information:
    - Present multiple perspectives and nuanced views
    - Include historical context and future implications
    - Focus on depth and breadth of coverage

    Always identify your approach clearly and explain your methodology as part of your response.""",
    llm_config=llm_config
)

evaluator_agent = ConversableAgent(
    name="evaluator_agent",
    system_message="""You are the Evaluator Agent responsible for assessing multiple approaches to the same task and selecting or synthesizing the best result.

    Your role is to:
    1. Carefully review each approach and result
    2. Evaluate each solution based on criteria appropriate to the task type
    3. Assign scores to each approach on a scale of 1-10
    4. Either select the best approach or synthesize a superior solution by combining strengths

    For creative tasks, evaluate based on:
    - Originality and uniqueness
    - Effectiveness in addressing the creative brief
    - Quality of execution and coherence

    For problem-solving tasks, evaluate based on:
    - Correctness and accuracy
    - Efficiency and elegance
    - Comprehensiveness and robustness

    For factual tasks, evaluate based on:
    - Accuracy and correctness
    - Comprehensiveness and depth
    - Clarity and organization

    When appropriate, rather than just selecting a single approach, synthesize a superior solution by combining the strengths of multiple approaches.

    Use the evaluate_and_select tool to submit your final evaluation, including detailed scoring and rationale.""",
    functions=[evaluate_and_select],
    llm_config=llm_config
)

# User agent for interaction
user = UserProxyAgent(
    name="user",
    code_execution_config=False
)

# NESTED CHAT
# Isolates each agent's message history so they only see the task and no other agents' responses

def extract_task_message(recipient: ConversableAgent, messages: list[dict[str, Any]], sender: ConversableAgent, config) -> str:
    """Extracts the task to give to an agent as the task"""
    return sender.context_variables.get("current_task", "There's no task, return UNKNOWN.")

def record_agent_response(sender: ConversableAgent, recipient: ConversableAgent, summary_args: dict) -> str:
    """Record each nested agent's response, track completion, and prepare for evaluation"""

    # Update the context variable with the agent's response
    context_var_key = f"{recipient.name.lower()}_result"
    taskmaster_agent.context_variables.set(context_var_key, recipient.chat_messages[sender][-1]["content"])

    # Increment the approach counter
    taskmaster_agent.context_variables.set("approach_count", taskmaster_agent.context_variables.get("approach_count") + 1)

    # Track if we now have all results
    task_completed = all(taskmaster_agent.context_variables.get(f"{key}_result") is not None
                        for key in redundant_agent_names)
    taskmaster_agent.context_variables.set("task_completed", task_completed)

    if not task_completed:
        # Still have outstanding responses to gather, in this nested chat only the last message is returned
        # to the outer group chat
        return ""
    else:
        # All agents have provided their responses
        # Combine all responses into a single message for the evaluator to evaluate
        combined_responses = "\n".join(
            [f"agent_{agent_name}:\n{taskmaster_agent.context_variables.get(f'{agent_name}_result')}\n\n---"
             for agent_name in redundant_agent_names]
        )

        return combined_responses

# Create the chat queue for the nested chats
redundant_agent_queue = []
for agent in [agent_a, agent_b, agent_c]:
    nested_chat = {
        "recipient": agent,
        "message": extract_task_message,  # Retrieve the status details of the order using the order id
        "max_turns": 1,  # Only one turn is necessary
        "summary_method": record_agent_response,  # Return each agent's response in context variables
    }

    redundant_agent_queue.append(nested_chat)

# HANDOFFS

# Register handoffs for the redundant pattern
taskmaster_agent.handoffs.add_context_conditions(
    [
        # Nested chat to get responses from all agents if the task is not completed
        OnContextCondition(
            target=NestedChatTarget(nested_chat_config={"chat_queue": redundant_agent_queue}),
            condition=ExpressionContextCondition(ContextExpression("len(${agent_a_result}) == 0 or len(${agent_b_result}) == 0 or len(${agent_c_result}) == 0")),
            available=ExpressionAvailableCondition(ContextExpression("${task_initiated} == True and len(${current_task}) > 0 and ${task_completed} == False"))
        ),
        # Transition to evaluator once all results are in
        OnContextCondition(
            target=AgentTarget(evaluator_agent),
            condition=ExpressionContextCondition(ContextExpression("${evaluation_complete} == False")),
            available=ExpressionAvailableCondition(ContextExpression("${task_completed} == True"))
        ),
    ]
)
# Default fallback
taskmaster_agent.handoffs.set_after_work(RevertToUserTarget())

# Evaluator returns to user after evaluation
evaluator_agent.handoffs.set_after_work(RevertToUserTarget())

# Function to run the redundant pattern
def run_redundant_pattern():
    """Run the redundant pattern with multiple independent approaches to the same task"""
    print("Initiating Redundant Pattern...")

    # Sample creative task
    creative_task = "Write a short story about a robot learning to understand emotions."

    # Sample problem-solving task
    # problem_solving_task = "Design an algorithm to detect and filter fake news from social media feeds."

    # Sample factual task
    # factual_task = "Explain how quantum computing works and its potential applications."

    # Choose which task to process in this run
    current_task = creative_task
    task_type = "creative"  # Options: "creative", "problem_solving", "factual"

    agent_pattern = DefaultPattern(
        initial_agent=taskmaster_agent,
        agents=[taskmaster_agent, evaluator_agent],
        context_variables=shared_context,
        user_agent=user,
    )

    chat_result, final_context, last_agent = initiate_group_chat(
        pattern=agent_pattern,
        messages=f"I need help with this task: {current_task}",
        max_rounds=30,
    )

    # Display the results
    print("\n===== TASK PROCESSING SUMMARY =====\n")
    print(f"Task: {final_context.get('current_task')}")
    print(f"Task Type: {final_context.get('task_type')}")
    print(f"Number of Approaches: {final_context.get('approach_count')}")

    # Display the evaluation scores
    print("\n===== EVALUATION SCORES =====\n")
    for agent_id, score in final_context.get("evaluation_scores", {}).items():
        print(f"{agent_id.upper()}: {score}/10")

    # Display the selected approach and final result
    print("\n===== EVALUATION NOTES =====\n")
    print(f"{final_context.get('evaluation_notes')}...")

    # Display the selected approach and final result
    print("\n===== FINAL RESULT =====\n")
    print(f"Selected Approach: {final_context.get('selected_approach')}")
    final_result = final_context.get("final_result")
    if final_result:
        print(f"Final Result: {final_result[:500]}...")

    # Display the conversation flow
    print("\n===== SPEAKER ORDER =====\n")
    for message in chat_result.chat_history:
        if "name" in message and message["name"] != "_Group_Tool_Executor":
            print(f"{message['name']}")

if __name__ == "__main__":
    run_redundant_pattern()