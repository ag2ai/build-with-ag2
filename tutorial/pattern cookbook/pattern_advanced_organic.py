from autogen import ConversableAgent, UserProxyAgent, LLMConfig
from autogen.agentchat import initiate_group_chat
from autogen.agentchat.group.patterns import AutoPattern
from dotenv import load_dotenv
import os
load_dotenv()

# Setup LLM configuration
llm_config = llm_config = LLMConfig(config_list={"api_type": "openai", "model": "gpt-5-nano","api_key":os.getenv("OPENAI_API_KEY")})

# Create specialized agents with descriptions that help the GROUP_MANAGER route appropriately
project_manager = ConversableAgent(
   name="project_manager",
   system_message="""You are a skilled project manager specializing in software development projects.
   You excel at creating project plans, setting milestones, managing timelines, allocating resources,
   conducting status meetings, and solving organizational problems.

   When responding to queries about project planning, timelines, resource allocation, risk management,
   or general project coordination, provide clear, structured guidance.

   You must utilize your experts: developer, qa_engineer, ui_ux_designer, and technical_writer to get the job done.
   """,
   description="""Answers questions about project planning, timelines,
   resource allocation, risk management, project coordination, team organization, and status updates.
   Call on this agent when the conversation involves planning, scheduling, task prioritization,
   or overall project management concerns.""",
   llm_config=llm_config
)

developer = ConversableAgent(
   name="developer",
   system_message="""You are an expert software developer proficient in multiple programming languages
   and frameworks. You write clean, efficient code and can design robust software architectures.

   When asked for code solutions, architectural guidance, or implementation advice, provide
   practical, well-documented examples and explain your reasoning.

   You specialize in Python, JavaScript, cloud architecture, databases, and API development.
   """,
   description="""Answers questions about code implementation, programming languages,
   software architecture, technical solutions, APIs, databases, debugging, and development best practices.
   Call on this agent when the conversation involves writing or reviewing code, technical design decisions,
   or implementation approaches.""",
   llm_config=llm_config
)

qa_engineer = ConversableAgent(
   name="qa_engineer",
   system_message="""You are a thorough QA engineer who specializes in software testing, quality
   assurance, and bug detection. You're skilled in creating test plans, writing test cases,
   performing manual and automated testing, and ensuring software meets quality standards.

   When addressing testing concerns, provide systematic approaches to verify functionality
   and identify potential issues.
   """,
   description="""Answers questions about testing strategies, test cases,
   quality assurance, bug detection, test automation, user acceptance testing, and software quality.
   Call on this agent when the conversation involves testing methodologies, quality concerns,
   finding bugs, or validating software functionality.""",
   llm_config=llm_config
)

ui_ux_designer = ConversableAgent(
   name="ui_ux_designer",
   system_message="""You are a creative UI/UX designer with expertise in creating intuitive,
   accessible, and aesthetically pleasing user interfaces. You understand design principles,
   user research methodologies, and can create wireframes and mockups.

   When discussing design matters, focus on user-centered approaches and visual solutions
   that enhance user experience.
   """,
   description="""Answers questions about user interface design, user experience,
   visual design, wireframing, prototyping, usability, accessibility, and design systems.
   Call on this agent when the conversation involves design decisions, user interactions,
   visual elements, or user experience concerns.""",
   llm_config=llm_config
)

technical_writer = ConversableAgent(
   name="technical_writer",
   system_message="""You are a skilled technical writer specializing in software documentation.
   You excel at creating clear, concise, and comprehensive documentation for various audiences,
   including user guides, API documentation, and technical specifications.

   When creating documentation, focus on clarity, completeness, and accessibility for the
   intended audience.
   """,
   description="""Answers questions about documentation, user guides,
   technical specifications, API docs, knowledge bases, and information architecture.
   Call on this agent when the conversation involves creating or improving documentation,
   explaining complex concepts, or organizing information for different audiences.""",
   llm_config=llm_config
)

# Create a user agent
user = UserProxyAgent(
    name="user_proxy",
    human_input_mode="ALWAYS",
    code_execution_config=False
)

# Create the agent pattern - AutoPattern uses the internal group chat manager
# to select agents automatically based on descriptions
agent_pattern = AutoPattern(
  initial_agent=project_manager,
    agents=[project_manager, developer, qa_engineer, ui_ux_designer, technical_writer],
    group_manager_args={"llm_config": llm_config},
    user_agent=user,
)

# Initiate the group chat with the pattern
result, final_context, last_agent = initiate_group_chat(
    pattern=agent_pattern,
    messages="We need to create a new web application for inventory management. Let's start with a project plan.",
    max_rounds=15,
)