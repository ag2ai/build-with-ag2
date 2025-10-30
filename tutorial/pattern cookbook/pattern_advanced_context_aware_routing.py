# Context-Aware Routing pattern for dynamic task assignment
# Routes queries to the most appropriate specialist based on query content analysis

from typing import Annotated
from autogen import (
    ConversableAgent,
    UserProxyAgent,
    LLMConfig,
)

from autogen.agentchat import initiate_group_chat
from autogen.agentchat.group.patterns import DefaultPattern
from autogen.agentchat.group.targets.transition_target import AgentTarget, AgentNameTarget, RevertToUserTarget
from autogen.agentchat.group import ReplyResult, ContextVariables, ExpressionContextCondition, ExpressionAvailableCondition, ContextExpression, OnContextCondition

# Setup LLM configuration
llm_config = LLMConfig(config_list={"model": "gpt-4.1-mini", "api_type": "openai", "cache_seed": 1, "parallel_tool_calls": False})

# Shared context for tracking the conversation and routing decisions
shared_context = ContextVariables(data={
    # Routing state
    "routing_started": False,
    "current_domain": None,
    "previous_domains": [],
    "domain_confidence": {},

    # Request tracking
    "request_count": 0,
    "current_request": "",
    "domain_history": {},

    # Response tracking
    "question_responses": [], # List of question-response pairs
    "question_answered": True, # Indicates if the last question was answered

    # Specialist invocation tracking
    "tech_invocations": 0,
    "finance_invocations": 0,
    "healthcare_invocations": 0,
    "general_invocations": 0,

    # Error state (not handled but could be used to route to an error agent)
    "has_error": False,
    "error_message": "",
})

# Functions for the context-aware routing pattern

def analyze_request(
    request: Annotated[str, "The user request text to analyze"],
    context_variables: ContextVariables
) -> ReplyResult:
    """
    Analyze a user request to determine routing based on content
    Updates context variables with routing information
    """
    context_variables["question_answered"] = False

    # Update request tracking
    context_variables["routing_started"] = True
    context_variables["request_count"] += 1
    context_variables["current_request"] = request

    # Previous domain becomes part of history
    if context_variables["current_domain"]:
        prev_domain = context_variables["current_domain"]
        context_variables["previous_domains"].append(prev_domain)
        if prev_domain in context_variables["domain_history"]:
            context_variables["domain_history"][prev_domain] += 1
        else:
            context_variables["domain_history"][prev_domain] = 1

    # Reset current_domain to be determined by the router
    context_variables["current_domain"] = None

    return ReplyResult(
        message=f"Request analyzed. Will determine the best specialist to handle: '{request}'",
        context_variables=context_variables
    )

def route_to_tech_specialist(
    confidence: Annotated[int, "Confidence level for tech domain (1-10)"],
    reasoning: Annotated[str, "Reasoning for routing to tech specialist"],
    context_variables: ContextVariables
) -> ReplyResult:
    """
    Route the current request to the technology specialist
    """
    context_variables["current_domain"] = "technology"
    context_variables["domain_confidence"]["technology"] = confidence
    context_variables["tech_invocations"] += 1

    return ReplyResult(
        target=AgentTarget(agent=tech_specialist),
        message=f"Routing to tech specialist with confidence {confidence}/10. Reasoning: {reasoning}",
        context_variables=context_variables
    )

def route_to_finance_specialist(
    confidence: Annotated[int, "Confidence level for finance domain (1-10)"],
    reasoning: Annotated[str, "Reasoning for routing to finance specialist"],
    context_variables: ContextVariables
) -> ReplyResult:
    """
    Route the current request to the finance specialist
    """
    context_variables["current_domain"] = "finance"
    context_variables["domain_confidence"]["finance"] = confidence
    context_variables["finance_invocations"] += 1

    return ReplyResult(
        #target=AgentTarget(finance_specialist),
        target=AgentNameTarget(agent_name="finance_specialist"),
        message=f"Routing to finance specialist with confidence {confidence}/10. Reasoning: {reasoning}",
        context_variables=context_variables
    )

def route_to_healthcare_specialist(
    confidence: Annotated[int, "Confidence level for healthcare domain (1-10)"],
    reasoning: Annotated[str, "Reasoning for routing to healthcare specialist"],
    context_variables: ContextVariables
) -> ReplyResult:
    """
    Route the current request to the healthcare specialist
    """
    context_variables["current_domain"] = "healthcare"
    context_variables["domain_confidence"]["healthcare"] = confidence
    context_variables["healthcare_invocations"] += 1

    return ReplyResult(
        target=AgentTarget(agent=healthcare_specialist),
        message=f"Routing to healthcare specialist with confidence {confidence}/10. Reasoning: {reasoning}",
        context_variables=context_variables
    )

def route_to_general_specialist(
    confidence: Annotated[int, "Confidence level for general domain (1-10)"],
    reasoning: Annotated[str, "Reasoning for routing to general knowledge specialist"],
    context_variables: ContextVariables
) -> ReplyResult:
    """
    Route the current request to the general knowledge specialist
    """
    context_variables["current_domain"] = "general"
    context_variables["domain_confidence"]["general"] = confidence
    context_variables["general_invocations"] += 1

    return ReplyResult(
        target=AgentTarget(agent=general_specialist),
        message=f"Routing to general knowledge specialist with confidence {confidence}/10. Reasoning: {reasoning}",
        context_variables=context_variables
    )

# Functions for specialists to provide responses

def provide_tech_response(
    response: Annotated[str, "The specialist's response to the request"],
    context_variables: ContextVariables
) -> ReplyResult:
    """
    Submit a response from the technology specialist
    """
    # Record the question and response
    context_variables["question_responses"].append({
        "domain": "technology",
        "question": context_variables["current_request"],
        "response": response
    })
    context_variables["question_answered"] = True

    return ReplyResult(
        message="Technology specialist response provided.",
        context_variables=context_variables
    )

def provide_finance_response(
    response: Annotated[str, "The specialist's response to the request"],
    context_variables: ContextVariables
) -> ReplyResult:
    """
    Submit a response from the finance specialist
    """
    # Record the question and response
    context_variables["question_responses"].append({
        "domain": "finance",
        "question": context_variables["current_request"],
        "response": response
    })
    context_variables["question_answered"] = True

    return ReplyResult(
        message="Finance specialist response provided.",
        context_variables=context_variables
    )

def provide_healthcare_response(
    response: Annotated[str, "The specialist's response to the request"],
    context_variables: ContextVariables
) -> ReplyResult:
    """
    Submit a response from the healthcare specialist
    """
    # Record the question and response
    context_variables["question_responses"].append({
        "domain": "healthcare",
        "question": context_variables["current_request"],
        "response": response
    })
    context_variables["question_answered"] = True

    return ReplyResult(
        message="Healthcare specialist response provided.",
        context_variables=context_variables
    )

def provide_general_response(
    response: Annotated[str, "The specialist's response to the request"],
    context_variables: ContextVariables
) -> ReplyResult:
    """
    Submit a response from the general knowledge specialist
    """
    # Record the question and response
    context_variables["question_responses"].append({
        "domain": "general",
        "question": context_variables["current_request"],
        "response": response
    })
    context_variables["question_answered"] = True

    return ReplyResult(
        message="General knowledge specialist response provided.",
        context_variables=context_variables
    )

# Function for follow-up clarification if needed
def request_clarification(
    clarification_question: Annotated[str, "Question to ask user for clarification"],
    context_variables: ContextVariables
) -> ReplyResult:
    """
    Request clarification from the user when the query is ambiguous
    """
    return ReplyResult(
        message=f"Further clarification is required to determine the correct domain: {clarification_question}",
        context_variables=context_variables,
        target=RevertToUserTarget()
    )

# Create the agents for the routing system
router_agent = ConversableAgent(
    name="router_agent",
    system_message="""You are the routing agent responsible for analyzing user requests and directing them to the most appropriate specialist.

Your task is to carefully analyze each user query and determine which domain specialist would be best equipped to handle it:

1. Technology Specialist: For questions about computers, software, programming, IT issues, electronics, digital tools, internet, etc. Use route_to_tech_specialist to transfer.
2. Finance Specialist: For questions about money, investments, banking, budgeting, financial planning, taxes, economics, etc. Use route_to_finance_specialist to transfer.
3. Healthcare Specialist: For questions about health, medicine, fitness, nutrition, diseases, medical conditions, wellness, etc. Use route_to_healthcare_specialist to transfer.
4. General Knowledge Specialist: For general questions that don't clearly fit the other categories or span multiple domains. Use route_to_general_specialist to transfer.

For each query, you must:
1. Use the analyze_request tool to process the query and update context
2. Determine the correct domain by analyzing keywords, themes, and context
3. Consider the conversation history and previous domains if available
4. Route to the most appropriate specialist using the corresponding routing tool

When routing:
- Provide a confidence level (1-10) based on how certain you are about the domain
- Include detailed reasoning for your routing decision
- If a query seems ambiguous or spans multiple domains, route to the specialist who can best handle the primary intent

Always maintain context awareness by considering:
- Current query content and intent
- Previously discussed topics
- User's possible follow-up patterns
- Domain switches that might indicate changing topics

After a specialist has provided an answer, output the question and answer.

For ambiguous queries that could belong to multiple domains:
- If you are CERTAIN that the query is multi-domain but has a primary focus, route to the specialist for that primary domain
- If you are NOT CERTAIN and there is no clear primary domain, use the request_clarification tool to ask the user for more specifics
- When a query follows up on a previous topic, consider maintaining consistency by routing to the same specialist unless the domain has clearly changed""",
    functions=[
        analyze_request,
        route_to_tech_specialist,
        route_to_finance_specialist,
        route_to_healthcare_specialist,
        route_to_general_specialist,
        request_clarification
    ],
    llm_config=llm_config
)

tech_specialist = ConversableAgent(
    name="tech_specialist",
    system_message="""You are the technology specialist with deep expertise in computers, software, programming, IT, electronics, digital tools, and internet technologies.

When responding to queries in your domain:
1. Provide accurate, technical information based on current industry knowledge
2. Explain complex concepts in clear terms appropriate for the user's apparent level of technical understanding
3. Include practical advice, troubleshooting steps, or implementation guidance when applicable
4. Reference relevant technologies, programming languages, frameworks, or tools as appropriate
5. For coding questions, provide correct, well-structured code examples when helpful

Focus on being informative, precise, and helpful. If a query contains elements outside your domain of expertise, focus on the technology aspects while acknowledging the broader context.

Use the provide_tech_response tool to submit your final response.""",
    functions=[provide_tech_response],
    llm_config=llm_config
)

finance_specialist = ConversableAgent(
    name="finance_specialist",
    system_message="""You are the finance specialist with deep expertise in personal finance, investments, banking, budgeting, financial planning, taxes, economics, and business finance.

When responding to queries in your domain:
1. Provide accurate financial information and advice based on sound financial principles
2. Explain financial concepts clearly without excessive jargon
3. Present balanced perspectives on financial decisions, acknowledging risks and benefits
4. Avoid making specific investment recommendations but provide educational information about investment types
5. Include relevant financial principles, terms, or calculations when appropriate

Focus on being informative, balanced, and helpful. If a query contains elements outside your domain of expertise, focus on the financial aspects while acknowledging the broader context.

Use the provide_finance_response tool to submit your final response.""",
    functions=[provide_finance_response],
    llm_config=llm_config
)

healthcare_specialist = ConversableAgent(
    name="healthcare_specialist",
    system_message="""You are the healthcare specialist with deep expertise in health, medicine, fitness, nutrition, diseases, medical conditions, and wellness.

When responding to queries in your domain:
1. Provide accurate health information based on current medical understanding
2. Explain medical concepts in clear, accessible language
3. Include preventive advice and best practices for health management when appropriate
4. Reference relevant health principles, systems, or processes
5. Always clarify that you're providing general information, not personalized medical advice

Focus on being informative, accurate, and helpful. If a query contains elements outside your domain of expertise, focus on the health aspects while acknowledging the broader context.

Use the provide_healthcare_response tool to submit your final response.""",
    functions=[provide_healthcare_response],
    llm_config=llm_config
)

general_specialist = ConversableAgent(
    name="general_specialist",
    system_message="""You are the general knowledge specialist with broad expertise across multiple domains and topics.

When responding to queries in your domain:
1. Provide comprehensive information drawing from relevant knowledge domains
2. Handle questions that span multiple domains or don't clearly fit into a specialized area
3. Synthesize information from different fields when appropriate
4. Provide balanced perspectives on complex topics
5. Address queries about history, culture, society, ethics, environment, education, arts, and other general topics

Focus on being informative, balanced, and helpful. For questions that might benefit from deeper domain expertise, acknowledge this while providing the best general information possible.

Use the provide_general_response tool to submit your final response.""",
    functions=[provide_general_response],
    llm_config=llm_config
)

# User agent for interaction
user = UserProxyAgent(
    name="user",
    code_execution_config=False
)

# Register handoffs for the context-aware routing pattern
# Router agent to specialists based on domain
router_agent.register_handoffs(conditions=[
    # Route to tech specialist when domain is technology
    OnContextCondition(
        target=AgentTarget(agent=tech_specialist),
        condition=ExpressionContextCondition(expression=ContextExpression(expression="${current_domain} == 'technology'")),
        available=ExpressionAvailableCondition(expression=ContextExpression(expression="!${question_answered}"))
    ),
    # Route to finance specialist when domain is finance
    OnContextCondition(
        target=AgentTarget(agent=finance_specialist),
        condition=ExpressionContextCondition(expression=ContextExpression(expression="${current_domain} == 'finance'")),
        available=ExpressionAvailableCondition(expression=ContextExpression(expression="!${question_answered}"))
    ),
    # Route to healthcare specialist when domain is healthcare
    OnContextCondition(
        target=AgentTarget(agent=healthcare_specialist),
        condition=ExpressionContextCondition(expression=ContextExpression(expression="${current_domain} == 'healthcare'")),
        available=ExpressionAvailableCondition(expression=ContextExpression(expression="!${question_answered}"))
    ),
    # Route to general specialist when domain is general
    OnContextCondition(
        target=AgentTarget(agent=general_specialist),
        condition=ExpressionContextCondition(expression=ContextExpression(expression="${current_domain} == 'general'")),
        available=ExpressionAvailableCondition(expression=ContextExpression(expression="!${question_answered}"))
    ),
])
router_agent.handoffs.set_after_work(target=RevertToUserTarget())

# Specialists always return to router for next query
tech_specialist.handoffs.set_after_work(target=AgentTarget(agent=router_agent))
finance_specialist.handoffs.set_after_work(target=AgentTarget(agent=router_agent))
healthcare_specialist.handoffs.set_after_work(target=AgentTarget(agent=router_agent))
general_specialist.handoffs.set_after_work(target=AgentTarget(agent=router_agent))

# Run the context-aware routing pattern
def run_context_aware_routing():
    """Run the context-aware routing pattern for dynamic domain-based routing"""
    print("Initiating Context-Aware Routing Pattern...")

    # Sample requests to demonstrate the routing
    sample_general_knowledge = "Could you explain the cultural and historical significance of the Renaissance period in Europe? How did it influence art, science, and philosophy, and what lasting impacts does it have on modern society?"
    sample_healthcare_knowledge = "I've been experiencing frequent headaches, particularly in the morning, along with some dizziness. What might be causing this and what lifestyle changes or treatments should I consider? Are there specific foods that could help reduce headache frequency?"
    sample_tech_request = "What's the difference between interpreted and compiled programming languages? Can you give me examples of each and explain the advantages and disadvantages in terms of development speed and performance?"
    sample_finance_request = "Can you explain how blockchain technology works and its potential applications in finance?"
    sample_ambiguous_request = "Can you tell me about benefits? I'm trying to understand all my options and make the right decision."

    agent_pattern = DefaultPattern(
    agents=[
            router_agent,
            tech_specialist,
            finance_specialist,
            healthcare_specialist,
            general_specialist
        ],
    initial_agent=router_agent,
    context_variables=shared_context,
    user_agent=user,
    )

    chat_result, final_context, last_agent = initiate_group_chat(
        pattern=agent_pattern,
        messages=f"I have a question: {sample_ambiguous_request}",
        max_rounds=100,
    )

    # Display the Questions and Answers
    print("\n===== QUESTION-RESPONSE PAIRS =====\n")
    for i, qr_pair in enumerate(final_context["question_responses"]):
        print(f"{i+1}. Domain: {qr_pair['domain'].capitalize()}")
        print(f"Question: {qr_pair['question']}")
        print(f"Response: {qr_pair['response']}\n\n")

    # Display the results
    print("\n===== REQUEST ROUTING SUMMARY =====\n")
    print(f"Total Requests: {final_context['request_count']}")
    print(f"Routed to Domain: {final_context['current_domain']}")

    # Display the routing history
    print("\n===== DOMAIN ROUTING HISTORY =====\n")
    for domain, count in final_context["domain_history"].items():
        print(f"{domain.capitalize()}: {count} time(s)")

    # Show specialist invocation counts
    print("\n===== SPECIALIST INVOCATIONS =====\n")
    print(f"Technology Specialist: {final_context['tech_invocations']}")
    print(f"Finance Specialist: {final_context['finance_invocations']}")
    print(f"Healthcare Specialist: {final_context['healthcare_invocations']}")
    print(f"General Knowledge Specialist: {final_context['general_invocations']}")

    # Display the conversation flow
    print("\n===== SPEAKER ORDER =====\n")
    for message in chat_result.chat_history:
        if "name" in message and message["name"] != "_Group_Tool_Executor":
            print(f"{message['name']}")

if __name__ == "__main__":
    run_context_aware_routing()