import asyncio

import streamlit as st

from ag2 import Agent
from ag2.config import OpenAIConfig
from ag2.knowledge import MemoryKnowledgeStore
from ag2.network import (
    EV_CHANNEL_CLOSED,
    EV_PACKET,
    Hub,
    HubClient,
    HumanClient,
    LocalLink,
    Passport,
    Resume,
    TransitionGraph,
)

from agent_utils import system_messages  # import the agents' system prompts

# Agents speak once each, in this order, then the channel terminates.
AGENT_NAMES = ["story_agent", "gameplay_agent", "visuals_agent", "tech_agent"]

# Maps each agent to its output slot in st.session_state and its section title.
SECTION_INFO = {
    "story_agent": ("story", "Story Design"),
    "gameplay_agent": ("gameplay", "Gameplay Mechanics"),
    "visuals_agent": ("visuals", "Visual and Audio Design"),
    "tech_agent": ("tech", "Technical Recommendations"),
}


def build_prompt(agent_name: str) -> str:
    """System prompt for one agent of the team."""
    section_title = SECTION_INFO[agent_name][1]
    return f"""{system_messages[agent_name].strip()}

You are one agent in a four-agent game design team collaborating on a single
game concept. The brief and the sections your teammates wrote before you
appear in the conversation. Write only your own section of the report, do not
include any other parts, and do not use XML tags. Build on what your teammates
have already written and stay consistent with it.

Start your response with: '## {section_title}'.
"""


async def run_game_design_team(
    task: str, api_key: str, model: str, base_url: str | None = None
) -> dict[str, str]:
    """Run the pipeline: story -> gameplay -> visuals -> tech, one turn each.

    The brief is seeded by a HumanClient (a non-LLM participant), so the
    workflow channel routes it to the story agent, which starts the pipeline.
    Each agent's reply lands on the channel, so the next agent sees it.

    ``base_url`` points the OpenAI-compatible client at another provider,
    e.g. https://openrouter.ai/api/v1 for OpenRouter.
    """
    config = OpenAIConfig(model=model, api_key=api_key, base_url=base_url)

    hub = await Hub.open(MemoryKnowledgeStore(), ttl_sweep_interval=0)
    link = LocalLink(hub)
    user_hc = HubClient(link, hub=hub)
    agent_hcs = [HubClient(link, hub=hub) for _ in AGENT_NAMES]

    try:
        # Non-LLM seeder: its only job is to post the brief as its turn.
        user = await user_hc.register_human(Passport(name="user", kind="human"))

        # Build each Agent, then register it with the hub (attach no plugin
        # tools — these are pure pipeline workers, routing is in the graph).
        clients = {}
        for agent_name, hc in zip(AGENT_NAMES, agent_hcs):
            agent = Agent(agent_name, prompt=build_prompt(agent_name), config=config)
            clients[agent_name] = await hc.register(
                agent, Passport(name=agent_name), Resume(), attach_plugin=False
            )

        # user (brief) -> story -> gameplay -> visuals -> tech -> terminate.
        graph = TransitionGraph.sequence(
            [user.agent_id] + [clients[name].agent_id for name in AGENT_NAMES]
        )

        channel = await user.open(
            type="workflow",
            target=[clients[name].agent_id for name in AGENT_NAMES],
            knobs={"graph": graph.to_dict()},
        )
        await channel.send(task)

        # The last step's transition terminates the channel automatically
        # with reason "sequence_complete" — wait for that envelope.
        await user.next_envelope(
            predicate=lambda e: e.event_type == EV_CHANNEL_CLOSED,
            timeout=600.0,
        )

        # Collect each agent's section from the channel's write-ahead log.
        output = {key: "" for _, (key, _) in SECTION_INFO.items()}
        wal = await hub.read_wal(channel.channel_id)
        for envelope in wal:
            if envelope.event_type != EV_PACKET:
                continue
            for agent_name, client in clients.items():
                if envelope.sender_id == client.agent_id:
                    output[SECTION_INFO[agent_name][0]] = envelope.event_data.get(
                        "body", ""
                    )
        return output
    finally:
        await user_hc.close()
        for hc in agent_hcs:
            await hc.close()
        await hub.close()


# Initialize session state
if "output" not in st.session_state:
    st.session_state.output = {"story": "", "gameplay": "", "visuals": "", "tech": ""}

# Sidebar for provider, API key, and model input
st.sidebar.title("API key")
provider = st.sidebar.segmented_control(
    "Provider", ["OpenAI", "OpenRouter"], default="OpenAI"
)

if provider == "OpenRouter":
    api_key = st.sidebar.text_input("OpenRouter API key", type="password")
    # OpenRouter model ids are <vendor>/<model>, e.g. openai/gpt-4o-mini
    model = st.sidebar.text_input("Model", "openai/gpt-4o-mini")
    # OpenRouter exposes an OpenAI-compatible API
    base_url = "https://openrouter.ai/api/v1"
else:
    api_key = st.sidebar.text_input("OpenAI API key", type="password")
    model = "gpt-4o-mini"
    base_url = None

# Add guidance in sidebar
st.sidebar.success(
    """
✨ **Getting Started**

Please provide inputs and features for your dream game! Consider:
- The overall vibe and setting
- Core gameplay elements
- Target audience and platforms
- Visual style preferences
- Technical requirements

The AI agents will collaborate to develop a comprehensive game concept based on your specifications.
"""
)

# Main app UI
st.title("🎮 AI Game Design Agent Team")

# Add agent information below title
st.info(
    """
**Meet Your AI Game Design Team:**

🎭 **Story Agent** - Crafts compelling narratives and rich worlds

🎮 **Gameplay Agent** - Creates engaging mechanics and systems

🎨 **Visuals Agent** - Shapes the artistic vision and style

⚙️ **Tech Agent** - Provides technical direction and solutions

These agents collaborate to create a comprehensive game concept based on your inputs.
"""
)

# User inputs
st.subheader("Game Details")
col1, col2 = st.columns(2)

with col1:
    background_vibe = st.text_input("Background Vibe", "Epic fantasy with dragons")
    game_type = st.selectbox(
        "Game Type",
        [
            "RPG",
            "Action",
            "Adventure",
            "Puzzle",
            "Strategy",
            "Simulation",
            "Platform",
            "Horror",
        ],
    )
    target_audience = st.selectbox(
        "Target Audience",
        [
            "Kids (7-12)",
            "Teens (13-17)",
            "Young Adults (18-25)",
            "Adults (26+)",
            "All Ages",
        ],
    )
    player_perspective = st.selectbox(
        "Player Perspective",
        ["First Person", "Third Person", "Top Down", "Side View", "Isometric"],
    )
    multiplayer = st.selectbox(
        "Multiplayer Support",
        [
            "Single Player Only",
            "Local Co-op",
            "Online Multiplayer",
            "Both Local and Online",
        ],
    )

with col2:
    game_goal = st.text_input("Game Goal", "Save the kingdom from eternal winter")
    art_style = st.selectbox(
        "Art Style",
        [
            "Realistic",
            "Cartoon",
            "Pixel Art",
            "Stylized",
            "Low Poly",
            "Anime",
            "Hand-drawn",
        ],
    )
    platform = st.multiselect(
        "Target Platforms",
        ["PC", "Mobile", "PlayStation", "Xbox", "Nintendo Switch", "Web Browser"],
    )
    development_time = st.slider("Development Time (months)", 1, 36, 12)
    cost = st.number_input("Budget (USD)", min_value=0, value=10000, step=5000)

# Additional details
st.subheader("Detailed Preferences")
col3, col4 = st.columns(2)

with col3:
    core_mechanics = st.multiselect(
        "Core Gameplay Mechanics",
        [
            "Combat",
            "Exploration",
            "Puzzle Solving",
            "Resource Management",
            "Base Building",
            "Stealth",
            "Racing",
            "Crafting",
        ],
    )
    mood = st.multiselect(
        "Game Mood/Atmosphere",
        [
            "Epic",
            "Mysterious",
            "Peaceful",
            "Tense",
            "Humorous",
            "Dark",
            "Whimsical",
            "Scary",
        ],
    )

with col4:
    inspiration = st.text_area("Games for Inspiration (comma-separated)", "")
    unique_features = st.text_area("Unique Features or Requirements", "")

depth = st.selectbox("Level of Detail in Response", ["Low", "Medium", "High"])

# Button to start the agent collaboration
if st.button("Generate Game Concept"):
    # Check if API key is provided
    if not api_key:
        st.error(f"Please enter your {provider} API key.")
    else:
        with st.spinner("🤖 AI Agents are collaborating on your game concept..."):
            # Prepare the task based on user inputs
            task = f"""
            Create a game concept with the following details:
            - Background Vibe: {background_vibe}
            - Game Type: {game_type}
            - Game Goal: {game_goal}
            - Target Audience: {target_audience}
            - Player Perspective: {player_perspective}
            - Multiplayer Support: {multiplayer}
            - Art Style: {art_style}
            - Target Platforms: {", ".join(platform)}
            - Development Time: {development_time} months
            - Budget: ${cost:,}
            - Core Mechanics: {", ".join(core_mechanics)}
            - Mood/Atmosphere: {", ".join(mood)}
            - Inspiration: {inspiration}
            - Unique Features: {unique_features}
            - Detail Level: {depth}
            """

            st.session_state.output = asyncio.run(
                run_game_design_team(task, api_key, model, base_url)
            )

        # Display success message after completion
        st.success("✨ Game concept generated successfully!")

        # Display the individual outputs in expanders
        with st.expander("Story Design"):
            st.markdown(st.session_state.output["story"])

        with st.expander("Gameplay Mechanics"):
            st.markdown(st.session_state.output["gameplay"])

        with st.expander("Visual and Audio Design"):
            st.markdown(st.session_state.output["visuals"])

        with st.expander("Technical Recommendations"):
            st.markdown(st.session_state.output["tech"])
