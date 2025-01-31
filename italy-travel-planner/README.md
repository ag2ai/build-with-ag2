# Italy Travel Planner

An interactive travel planning system specifically designed for Italian destinations, combining AG2's powerful agent swarm capabilities with a user-friendly Streamlit interface.

## Features

- 🤖 Multi-agent system with specialized roles:
  - Travel Planner Agent: Creates customized Italian travel itineraries
  - GraphRAG Agent: Provides detailed information about Italian attractions and restaurants
  - Structured Output Agent: Formats itineraries into structured JSON messages
  - Route Timing Agent: Calculates travel times between locations

- 💬 Real-time chat interface for interactive trip planning
- 🗺️ Integration with Google Maps for accurate travel times
- 📊 Structured message format for clear communication
- 🎨 Modern Streamlit UI with AG2 branding

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/ag2ai/build-with-ag2.git
   cd build-with-ag2/italy-travel-planner
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   - Create an `OAI_CONFIG_LIST` file with your OpenAI API key
   - Set up your Google Maps API key in the environment

4. Start the application:
   ```bash
   streamlit run main.py
   ```

## Usage

1. Open the application in your browser
2. Enter your travel plans in the chat interface
3. Interact with the AI agents to refine your itinerary
4. Review and confirm your travel plans
5. Receive a structured itinerary with travel times

## Contact

For more information or questions:
- AG2 Documentation: https://docs.ag2.ai/docs/Home
- AG2 GitHub: https://github.com/ag2ai/ag2
- Discord: https://discord.gg/pAbnFJrkgZ

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](../LICENSE) for details.
