# AG2 Agent Pattern Cookbook

A comprehensive collection of agent orchestration patterns using AG2 (AutoGen 2). This cookbook demonstrates various ways to design and coordinate multi-agent systems, from simple two-agent conversations to complex hierarchical structures.

## Overview

This cookbook provides ready-to-run examples of common agent interaction patterns. Each pattern demonstrates a specific approach to organizing agent communication and task coordination.

## Setup

1. Install dependencies:
```bash
uv sync
```

2. Configure your environment:
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

3. Run any pattern:
```bash
python pattern_basic_1_two_agent_chat.py
```

## Basic Patterns

These patterns cover fundamental agent interaction models:

### 1. Two Agent Chat (`pattern_basic_1_two_agent_chat.py`)
The simplest pattern: a direct conversation between two agents.
- **Use case**: Question-answering, simple task delegation
- **Key features**: Direct communication, single conversation thread
- **Example**: Student asks teacher about math concepts

### 2. Sequential Chat (`pattern_basic_2_sequential_chat.py`)
Agents communicate in a predetermined sequence.
- **Use case**: Multi-stage workflows, assembly-line processing
- **Key features**: Fixed order of execution, context passing between stages
- **Example**: Task flows through multiple specialized agents in order

### 3. Nested Chat (`pattern_basic_3_nested_chat.py`)
An agent delegates subtasks to other agent conversations.
- **Use case**: Complex tasks requiring specialized sub-teams
- **Key features**: Hierarchical delegation, isolated sub-conversations
- **Example**: Manager delegates to specialist sub-teams

### 4. Group Chat (`pattern_basic_4_group_chat.py`)
Multiple agents participate in a shared conversation.
- **Use case**: Collaborative problem-solving, brainstorming
- **Key features**: Dynamic turn-taking, shared context
- **Example**: Team discussion with multiple perspectives

## Advanced Patterns

These patterns demonstrate sophisticated orchestration techniques:

### Context-Aware Routing (`pattern_advanced_context_aware_routing.py`)
Routes conversations based on context and conditions.
- **Use case**: Dynamic workflow adaptation, intelligent routing
- **Key features**: Conditional transitions, context-based decisions
- **Complexity**: Medium-High

### Escalation (`pattern_advanced_escalation.py`)
Tasks escalate through levels of expertise or authority.
- **Use case**: Support systems, progressive problem-solving
- **Key features**: Tier-based handling, automatic escalation
- **Complexity**: Medium

### Feedback Loop (`pattern_advanced_feedback_loop.py`)
Agents provide iterative feedback until quality standards are met.
- **Use case**: Quality assurance, iterative refinement
- **Key features**: Review cycles, quality gates, revision tracking
- **Complexity**: Medium-High

### Hierarchical (`pattern_advanced_hierarchical.py`)
Multi-level organization with executives, managers, and specialists.
- **Use case**: Large-scale projects, organizational workflows
- **Key features**: Authority levels, delegation chains, state tracking
- **Complexity**: High

### Organic/Auto (`pattern_advanced_organic.py`)
Agents are automatically selected based on their expertise descriptions.
- **Use case**: Dynamic team formation, flexible collaboration
- **Key features**: Automatic routing using AutoPattern, description-based selection
- **Complexity**: Medium

### Pipeline (`pattern_advanced_pipeline.py`)
Sequential processing with specialized stages and checkpoints.
- **Use case**: Data processing pipelines, content production
- **Key features**: Stage-based workflow, validation gates
- **Complexity**: Medium

### Redundant (`pattern_advanced_redundant.py`)
Multiple agents work on the same task for reliability or comparison.
- **Use case**: Critical decisions, consensus building, validation
- **Key features**: Parallel execution, result comparison
- **Complexity**: Medium

### Star (`pattern_advanced_star.py`)
Central coordinator distributes work to specialized agents.
- **Use case**: Task distribution, resource allocation
- **Key features**: Hub-and-spoke architecture, central control
- **Complexity**: Medium

### Triage with Tasks (`pattern_advanced_triage_with_tasks.py`)
Incoming requests are classified and routed to appropriate handlers.
- **Use case**: Request handling, ticket routing, customer service
- **Key features**: Classification, priority assignment, specialized routing
- **Complexity**: Medium-High

## Pattern Selection Guide

Choose a pattern based on your requirements:

| Pattern | Best For | Complexity | Control Level |
|---------|----------|------------|---------------|
| Two Agent Chat | Simple Q&A | Low | Direct |
| Sequential Chat | Fixed workflows | Low | High |
| Nested Chat | Modular tasks | Medium | High |
| Group Chat | Collaboration | Medium | Low |
| Context-Aware Routing | Adaptive workflows | Medium-High | Medium |
| Escalation | Tiered support | Medium | Medium |
| Feedback Loop | Quality control | Medium-High | Medium |
| Hierarchical | Large organizations | High | High |
| Organic | Dynamic teams | Medium | Low |
| Pipeline | Processing stages | Medium | High |
| Redundant | Critical validation | Medium | Medium |
| Star | Centralized control | Medium | High |
| Triage | Request routing | Medium-High | Medium |

## Key Concepts

### LLM Configuration
All patterns use AG2's `LLMConfig` for model configuration:
```python
from autogen import LLMConfig
llm_config = LLMConfig(config_list={
    "api_type": "openai",
    "model": "gpt-5-nano",
    "api_key": os.getenv("OPENAI_API_KEY")
})
```

### Agent Types
- **ConversableAgent**: General-purpose agent with LLM capabilities
- **UserProxyAgent**: Represents human users or automated executors

### Pattern Framework
Advanced patterns use:
- **ContextVariables**: Shared state across agents
- **AgentTarget**: Define conversation transitions
- **Conditions**: Control flow based on context or LLM decisions
- **Functions**: Agent capabilities and context updates

### Pattern Initialization
```python
from autogen.agentchat import initiate_group_chat
result, final_context, last_agent = initiate_group_chat(
    pattern=agent_pattern,
    messages="Your initial message",
    max_rounds=20
)
```

## Common Customizations

### Adding New Agents
```python
new_agent = ConversableAgent(
    name="agent_name",
    system_message="Role description",
    description="When to use this agent",
    llm_config=llm_config
)
```

### Adding Agent Functions
```python
def custom_function(param: str, context_variables: ContextVariables) -> ReplyResult:
    context_variables["key"] = param
    return ReplyResult(
        response="Function completed",
        context_variables=context_variables,
        handoff="next_agent_name"
    )
```

### Customizing Transitions
```python
from autogen.agentchat.group import OnCondition, StringLLMCondition
transitions = [
    OnCondition(
        target=AgentNameTarget("target_agent"),
        available_condition=ExpressionAvailableCondition(
            condition=ContextExpression('task_completed == True')
        )
    )
]
```

## Project Structure
```
pattern cookbook/
├── .env                    # Environment configuration
├── .env.example           # Example environment file
├── pyproject.toml         # Project dependencies
├── uv.lock               # Locked dependencies
├── pattern_basic_1_two_agent_chat.py
├── pattern_basic_2_sequential_chat.py
├── pattern_basic_3_nested_chat.py
├── pattern_basic_4_group_chat.py
├── pattern_advanced_context_aware_routing.py
├── pattern_advanced_escalation.py
├── pattern_advanced_feedback_loop.py
├── pattern_advanced_hierarchical.py
├── pattern_advanced_organic.py
├── pattern_advanced_pipeline.py
├── pattern_advanced_redundant.py
├── pattern_advanced_star.py
└── pattern_advanced_triage_with_tasks.py
```

## Learning Path

1. **Start with basics**: Run the basic patterns in order (1-4)
2. **Understand concepts**: Study agent types, transitions, and context
3. **Explore advanced patterns**: Choose patterns relevant to your use case
4. **Customize**: Modify examples to fit your specific requirements
5. **Combine patterns**: Mix and match concepts from different patterns

## Resources

- [AG2 Documentation](https://docs.ag2.ai/)
- [AG2 GitHub Repository](https://github.com/ag2ai/ag2)
- [AutoGen Group Chat Patterns](https://docs.ag2.ai/docs/patterns)

## Contributing

This is a tutorial collection for learning AG2 patterns. Feel free to:
- Experiment with the examples
- Create variations for different use cases
- Share insights and improvements

## License

Part of the build-with-ag2 tutorial collection.
