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

## Prerequisites

- Python 3.8 or higher
- Git
- OpenAI API key
- Google Maps API key

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

3. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

4. Set up FalkorDB:
   ```bash
   # Using Docker (recommended)
   docker run -p 6379:6379 -p 3000:3000 -it --rm falkordb/falkordb:latest
   ```
   For other installation methods, refer to [FalkorDB documentation](https://docs.falkordb.com/).

5. Set up environment variables:
   ```bash
   # Create OAI_CONFIG_LIST file
   echo '[{"model": "gpt-4", "api_key": "your-api-key"}]' > OAI_CONFIG_LIST

   # Set Google Maps API key (required for route timing)
   # Get your key at: https://developers.google.com/maps/documentation/directions/overview
   export GOOGLE_MAPS_API_KEY="your-google-maps-api-key"
   ```

6. Start the application:
   ```bash
   streamlit run main.py
   ```

## Development

- Run pre-commit checks:
  ```bash
  pre-commit run --all-files
  ```

- Format code:
  ```bash
  black .
  ruff .
  ```

## Usage

1. Open the application in your browser
2. Enter your travel plans in the chat interface
3. Interact with the AI agents to refine your itinerary
4. Review and confirm your travel plans
5. Receive a structured itinerary with travel times

## Example Interaction

```
User: "I want to plan a 3-day trip to Rome and Florence"

Travel Planner: "I'll help you plan your Italian adventure! Let me ask about your preferences:
- What types of attractions interest you (historical sites, museums, etc.)?
- Do you have any specific dining preferences?
- How would you like to split your time between Rome and Florence?"

[Agents collaborate to create a personalized itinerary with attractions, restaurants, and travel times]
```

## Contact

For more information or questions:
- AG2 Documentation: https://docs.ag2.ai/docs/Home
- AG2 GitHub: https://github.com/ag2ai/ag2
- Discord: https://discord.gg/pAbnFJrkgZ

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](../LICENSE) for details.
