# Mastering Real-World Agentic AI Applications with AG2 (AutoGen)

A comprehensive tutorial series covering the fundamentals to advanced concepts of building agentic AI applications using AG2 (AutoGen).

## 🎯 Overview

This hands-on workshop series takes you through the complete journey of building intelligent AI agents that can work together, solve complex problems, and integrate with real-world applications. Whether you're new to agentic AI or looking to deepen your expertise, these modules provide practical examples and industry best practices.

## 📚 Course Modules

### Module 1: Introduction and Foundation of AI Agents

**File:** `module1_introduction/module1_introduction.ipynb`

- Understanding the agent paradigm
- Evolution from rule-based to AI-driven agents
- Value of agents in modern applications
- Multi-agent system architecture

### Module 2: Setup and Environment Configuration

**Directory:** `module2_setup/`

- Setting up AG2 development environment
- Configuration and dependencies
- First agent creation

### Module 3: Core Concepts and Architectures

**Directory:** `module3_core_concepts_and_architectures/`

- Agent communication patterns
- Message passing and protocols
- System design principles

### Module 4: Advanced Agent Design Patterns

**Directory:** `module4_advanced_agent_design_patterns/`

- Context-aware routing (`4.1_context_aware_routing.ipynb`)
- Escalation mechanisms (`4.2_escalation.ipynb`)
- Feedback loops (`4.3_feedback_loop.ipynb`)
- Hierarchical structures (`4.4_hirarchical.ipynb`)
- Organic agent interactions (`4.5_organic.ipynb`)
- Sequential processing (`4.6_sequential.ipynb`)
- Redundant systems (`4.7_redundent.ipynb`)
- Reasoning agents (`reasoning_agent.ipynb`)

### Module 5: Building Custom Agents

**Directory:** `module5_building_custom_agents/`

- Custom agent development
- Specialized agent behaviors
- Agent personality and capabilities

### Module 6: Integration with External Tools

**Directory:** `module6_integration_with_external_tools/`

- Tool calling and API integration
- External system connectivity
- Data processing and analysis

### Module 7: Real-World Example

**Directory:** `module7_real_world_examples/`

- Complete market analysis application (`marketanalysis/`)
- Streamlit integration (`marketanalysis_streamlit/`)
- End-to-end implementation

## 🚀 Getting Started

### Prerequisites

- Python 3.9 or higher (Python 3.12+ required for Module 6 MCP integration)
- Basic understanding of Python programming
- Familiarity with AI/ML concepts (helpful but not required)

### Installation

1. Clone this repository:

```bash
git clone <repository-url>
cd ag2-workshop
```

2. Install core dependencies (Modules 1–5, 7):

```bash
pip install "ag2[openai]" python-dotenv streamlit tavily-python
```

3. For Module 6 (MCP integration) — requires Python 3.12+:

```bash
pip install "ag2[openai,mcp]" python-dotenv streamlit arxiv wikipedia
```

4. Start with Module 1:

```bash
jupyter notebook module1_introduction/module1_introduction.ipynb
```

## 🔧 Key Technologies

- **AG2 (AutoGen)**: Multi-agent conversation framework
- **Streamlit**: Web application framework
- **Mesop**: Modern UI framework
- **Azure**: Cloud deployment platform

## 📖 Learning Path

1. **Beginner**: Start with Modules 1-3 to understand fundamentals
2. **Intermediate**: Progress through Modules 4-6 for advanced patterns
3. **Advanced**: Complete Module 7 for real-world production deployments

## 🎨 Features

- **Interactive Notebooks**: Hands-on Jupyter notebook tutorials
- **Real-World Examples**: Practical applications you can deploy
- **Multiple Deployment Options**: Local development to cloud production
- **Comprehensive Patterns**: 8 agent design patterns across 7 modules

## 🤝 Contributing

For questions or improvements, please refer to the main AG2 documentation and community resources.

## 📚 Additional Resources

- [AG2 Documentation](https://ag2ai.github.io/ag2/)
- [AG2/AutoGen Repository](https://github.com/ag2ai/ag2)

---

_This tutorial series provides hands-on experience with cutting-edge agentic AI development using AG2._
