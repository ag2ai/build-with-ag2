# AG2 Agent Pattern Cookbook

> **Last Updated**: October 30, 2025
> This is a living document and patterns may evolve as AG2 develops.

A comprehensive collection of agent orchestration patterns using AG2 (AutoGen 2). This cookbook demonstrates various ways to design and coordinate multi-agent systems, from simple two-agent conversations to complex hierarchical structures.

## Overview

This cookbook provides ready-to-run examples of common agent interaction patterns. Each pattern demonstrates a specific approach to organizing agent communication and task coordination.

## Agent Patterns as Digital Workforce Design

Just as human organizations have evolved different structures to solve various types of problems, multi-agent systems can be designed using patterns that mirror successful human workforce models. These patterns aren't arbitrary - they reflect decades of organizational design wisdom applied to autonomous AI agents.

**Why This Matters**: Understanding the human analogy helps you:
- Choose the right pattern by thinking about how you'd organize a human team
- Predict system behavior based on familiar organizational dynamics
- Communicate system architecture to non-technical stakeholders
- Identify bottlenecks and inefficiencies using organizational theory
- Scale agent systems using proven management principles

Each pattern in this cookbook corresponds to a real-world organizational structure, from one-on-one mentoring to complex corporate hierarchies.

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

These patterns cover fundamental agent interaction models, each mirroring common human collaboration structures:

### 1. Two Agent Chat (`pattern_basic_1_two_agent_chat.py`)
**Pattern**: Direct one-on-one interaction between two agents.

**Human Workforce Analogy**:
- Mentoring session (teacher and student)
- Consulting relationship (expert and client)
- Peer review (writer and editor)
- Customer support (agent and customer)

**When to Use**:
- Simple question-answering scenarios
- Expert consultation on focused topics
- Iterative refinement between two roles
- Direct task handoff situations

**Real-World Example**: A junior developer asking a senior architect about system design decisions.

---

### 2. Sequential Chat (`pattern_basic_2_sequential_chat.py`)
**Pattern**: Agents process work in a fixed, predetermined sequence.

**Human Workforce Analogy**:
- Manufacturing assembly line (each station adds value)
- Document approval workflow (draft → review → approval → publication)
- Healthcare patient flow (intake → diagnosis → treatment → discharge)
- Content production pipeline (research → writing → editing → publishing)

**When to Use**:
- Clear stage-gate processes
- Quality control checkpoints
- Predictable, repeatable workflows
- When each stage builds on previous work

**Real-World Example**: A content creation workflow where a researcher gathers information, a writer creates the draft, an editor refines it, and a publisher distributes it.

---

### 3. Nested Chat (`pattern_basic_3_nested_chat.py`)
**Pattern**: A coordinator agent delegates work to specialized sub-teams who have their own internal conversations.

**Human Workforce Analogy**:
- Project manager coordinating multiple specialized teams
- General contractor managing subcontractors (electrical, plumbing, carpentry)
- Event planner coordinating vendors (catering, AV, venue)
- Product manager orchestrating design, engineering, and marketing teams

**When to Use**:
- Complex projects requiring diverse expertise
- Parallel workstreams that need coordination
- Specialized knowledge domains
- When subtasks need internal collaboration

**Real-World Example**: A project manager assigns the backend work to a dev team (who discuss architecture among themselves), frontend to another team (who coordinate on UI/UX), and QA to a testing team.

---

### 4. Group Chat (`pattern_basic_4_group_chat.py`)
**Pattern**: Multiple agents collaborate in a shared discussion space.

**Human Workforce Analogy**:
- Team brainstorming session
- War room / crisis response team
- Design critique meeting
- Agile standup or planning meeting
- Executive committee discussion

**When to Use**:
- Need multiple perspectives simultaneously
- Creative problem-solving
- Consensus building
- When the best solution emerges from dialogue
- Situations requiring cross-functional input

**Real-World Example**: A product launch meeting with marketing, engineering, sales, and customer success all contributing their perspectives on go-to-market strategy.

## Advanced Patterns

These patterns mirror sophisticated organizational structures found in modern workforces:

### Context-Aware Routing (`pattern_advanced_context_aware_routing.py`)
**Pattern**: Dynamic routing where the next agent is selected based on current context and conditions.

**Human Workforce Analogy**: Smart help desk routing, hospital patient routing to specialists, legal case assignment, dynamic project staffing

**Real-World Example**: A customer inquiry system that routes technical questions to engineering, billing questions to finance, and feature requests to product based on inquiry content.

**Complexity**: Medium-High

### Escalation (`pattern_advanced_escalation.py`)
**Pattern**: Progressive escalation through tiers of increasing expertise or authority.

**Human Workforce Analogy**: IT support tiers (L1 → L2 → L3), customer complaints (CSR → Supervisor → Manager), medical diagnosis (Nurse → GP → Specialist)

**Real-World Example**: Technical support where basic questions are handled by automated responses, moderate issues go to support agents, and critical problems escalate to senior engineers.

**Complexity**: Medium

### Feedback Loop (`pattern_advanced_feedback_loop.py`)
**Pattern**: Iterative cycles of work and review until quality standards are met.

**Human Workforce Analogy**: Code review cycles, academic paper review, design iteration with critique, PR review process

**Real-World Example**: Content creation where a writer produces content, an editor provides feedback, the writer revises, and the cycle continues until approval.

**Complexity**: Medium-High

### Hierarchical (`pattern_advanced_hierarchical.py`)
**Pattern**: Multi-level organizational structure with executives, managers, and specialists.

**Human Workforce Analogy**: Corporate structure (C-Suite → VPs → Directors → Managers → ICs), military command chain, academic administration, construction projects

**Real-World Example**: A research project where an executive sets objectives, managers define workstreams, team leads coordinate specialists, and researchers execute tasks - with results flowing back up the chain.

**Complexity**: High

### Organic/Auto (`pattern_advanced_organic.py`)
**Pattern**: Agents are dynamically selected based on their expertise descriptions (auto-routing).

**Human Workforce Analogy**: Consulting firms matching consultants to clients, gig economy platforms (Upwork, Fiverr), hospital on-call specialists, open-source collaboration

**Real-World Example**: A software project where the system automatically brings in the security expert for security questions, database specialist for data modeling, and frontend developer for UI decisions based on conversation context.

**Complexity**: Medium

### Pipeline (`pattern_advanced_pipeline.py`)
**Pattern**: Sequential processing through specialized stages with quality gates.

**Human Workforce Analogy**: Software CI/CD pipeline, manufacturing with QC checkpoints, pharmaceutical drug development, publishing workflow

**Real-World Example**: Data processing pipeline where analysts clean data, engineers transform it, data scientists build models, and ML engineers deploy - with validation checks between stages.

**Complexity**: Medium

### Redundant (`pattern_advanced_redundant.py`)
**Pattern**: Multiple agents independently work on the same task for validation or consensus.

**Human Workforce Analogy**: Jury deliberation, academic peer review, medical second opinions, audit processes, competitive bidding

**Real-World Example**: Hiring decisions where multiple interviewers independently assess a candidate and compare notes to reach consensus, reducing individual bias.

**Complexity**: Medium

### Star (`pattern_advanced_star.py`)
**Pattern**: Central coordinator distributes work to specialized agents (hub-and-spoke).

**Human Workforce Analogy**: Dispatch center (911), project manager coordinating parallel workstreams, talent agent managing clients, administrative assistant coordinating meetings

**Real-World Example**: A project coordinator receiving a complex request, breaking it into parallel tasks (design, development, documentation), assigning to specialists, and consolidating results.

**Complexity**: Medium

### Triage with Tasks (`pattern_advanced_triage_with_tasks.py`)
**Pattern**: Incoming requests are classified, prioritized, and routed to appropriate handlers.

**Human Workforce Analogy**: Emergency room triage, IT ticketing systems, airport security screening, customer service routing, legal intake

**Real-World Example**: Customer support system that analyzes tickets, categorizes by type (bug, feature, question), assigns priority (critical/high/medium/low), and routes to appropriate teams.

**Complexity**: Medium-High

## Pattern Selection Guide

Choose a pattern based on your requirements:

| Pattern | Best For | Complexity | Control Level | Human Analogy |
|---------|----------|------------|---------------|---------------|
| Two Agent Chat | Simple Q&A | Low | Direct | Mentoring |
| Sequential Chat | Fixed workflows | Low | High | Assembly line |
| Nested Chat | Modular tasks | Medium | High | Project teams |
| Group Chat | Collaboration | Medium | Low | Team meeting |
| Context-Aware Routing | Adaptive workflows | Medium-High | Medium | Smart routing |
| Escalation | Tiered support | Medium | Medium | L1/L2/L3 support |
| Feedback Loop | Quality control | Medium-High | Medium | Review cycles |
| Hierarchical | Large organizations | High | High | Corporate structure |
| Organic | Dynamic teams | Medium | Low | Consulting pool |
| Pipeline | Processing stages | Medium | High | Manufacturing |
| Redundant | Critical validation | Medium | Medium | Jury/peer review |
| Star | Centralized control | Medium | High | Dispatch center |
| Triage | Request routing | Medium-High | Medium | ER triage |

## From Human Teams to Agent Teams

### Design Principles

When translating human workforce structures to agent systems, consider:

1. **Communication Overhead**
   - Human: Limited by meeting time, email delays, context switching
   - Agent: Near-instantaneous, but token costs matter
   - Design tip: Agents can handle more frequent coordination than humans

2. **Specialization vs Generalization**
   - Human: T-shaped skills (deep in one, broad in others)
   - Agent: Can be hyper-specialized without training overhead
   - Design tip: Create more specialized agents than you would hire specialists

3. **Decision Authority**
   - Human: Delegation requires trust and risk assessment
   - Agent: Delegation through explicit rules and conditions
   - Design tip: Make authority levels and escalation criteria explicit

4. **Learning and Adaptation**
   - Human: Learn from experience over time
   - Agent: Consistent behavior unless context/prompts change
   - Design tip: Build in explicit feedback mechanisms and context tracking

5. **Accountability and Oversight**
   - Human: Performance reviews, peer feedback
   - Agent: Logging, monitoring, quality gates
   - Design tip: Add checkpoints and validation steps

### Organizational Patterns to Agent Patterns

| Human Org Structure | Agent Pattern | Key Difference |
|---------------------|---------------|----------------|
| 1:1 Meeting | Two Agent Chat | Agents never tire of conversation |
| Assembly Line | Sequential Chat, Pipeline | No shift changes, perfect handoffs |
| Project Team | Nested Chat | Sub-teams work at machine speed |
| Standup Meeting | Group Chat | All participants fully present |
| Skill Marketplace | Organic | Instant matching, no negotiation |
| Support Tiers | Escalation | Instant escalation when criteria met |
| Peer Review | Feedback Loop | Faster iteration cycles |
| Corporation | Hierarchical | No office politics, clear delegation |
| Audit Team | Redundant | Perfect independence, no groupthink |
| Operations Center | Star | No context loss in coordination |
| Intake Process | Triage | Consistent classification |

### Common Design Mistakes

**Mistake 1: Over-orchestration**
- Don't: Create 10-agent hierarchies for simple tasks
- Do: Use two-agent chat when that's sufficient

**Mistake 2: Under-specified roles**
- Don't: Generic "assistant" agents without clear expertise
- Do: Define specific system messages and descriptions

**Mistake 3: Ignoring human involvement**
- Don't: Fully automate critical decisions without oversight
- Do: Include UserProxyAgent for approval steps

**Mistake 4: Missing quality gates**
- Don't: Let agents chain indefinitely without validation
- Do: Add checkpoints, max rounds, and exit conditions

**Mistake 5: Human-centric assumptions**
- Don't: Assume agents need breaks, motivation, or conflict resolution
- Do: Focus on clear routing logic and context management

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

### For Developers New to Multi-Agent Systems

1. **Start with basics**: Run the basic patterns in order (1-4)
   - Think: "How would I organize a human team for this task?"

2. **Understand concepts**: Study agent types, transitions, and context
   - Map: Agent roles → Job descriptions
   - Map: Transitions → Handoffs and escalations
   - Map: Context → Shared project knowledge

3. **Explore advanced patterns**: Choose patterns relevant to your use case
   - Ask: "What organizational structure handles this in the real world?"

4. **Customize**: Modify examples to fit your specific requirements
   - Start with the human workflow you want to automate
   - Identify roles, responsibilities, and decision points
   - Translate to agent definitions and transitions

5. **Combine patterns**: Mix and match concepts from different patterns
   - Just as companies combine org structures (matrix organizations, etc.)
   - Agents can follow hybrid patterns for complex scenarios

### For Engineering Leaders and Architects

Think of agent patterns as:
- **Technical Architecture**: How agents communicate and coordinate
- **Organizational Design**: How you'd structure a team to solve the problem
- **Process Engineering**: The workflow and quality gates

Ask yourself:
1. "How would I organize a human team for this?"
2. "Where are the bottlenecks and dependencies?"
3. "What decisions need oversight vs. automation?"
4. "How would we handle errors and exceptions?"

Then translate those answers directly into agent patterns.

## Why the Workforce Analogy Matters

Multi-agent systems can seem abstract and overwhelming. By grounding them in familiar human organizational patterns, you gain:

**1. Intuitive Design**: You already know how to organize teams - just apply that knowledge to agents.

**2. Communication**: Explaining "we're using a hierarchical pattern with escalation" is clearer than describing the technical implementation.

**3. Pattern Recognition**: When you see a new problem, ask "how would humans solve this?" and you'll know which pattern to use.

**4. Debugging**: If your agent system isn't working, think about what would fail in the human equivalent. Missing handoff? Unclear authority? No quality control?

**5. Scaling**: Organizational design principles (span of control, delegation, specialization) apply directly to agent systems.

### The Future of Work

As AI agents become more capable, the patterns that worked for human organizations will increasingly apply to hybrid human-agent teams. Understanding these patterns now prepares you for:

- **Augmented teams**: Humans and agents working together using the same organizational patterns
- **Dynamic allocation**: Agents handling routine work, escalating to humans for edge cases
- **Organizational learning**: Patterns that work for agents inform better human team structures

The skills you develop designing agent systems - clear role definition, explicit decision criteria, well-defined handoffs - are the same skills that make human teams excel.

## Resources
- [About AG2](https://ag2.ai/)
- [AG2 OSS Documentation](https://docs.ag2.ai/)
- [AG2 GitHub Repository](https://github.com/ag2ai/ag2)
- [Ag2 Group Chat Patterns](https://docs.ag2.ai/latest/docs/user-guide/advanced-concepts/pattern-cookbook/overview/)

## Contributing

This is a tutorial collection for learning AG2 patterns. Feel free to:
- Experiment with the examples
- Create variations for different use cases
- Share insights and improvements

## License

Part of the build-with-ag2 tutorial collection.
