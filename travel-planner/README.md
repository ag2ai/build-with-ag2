# Trip Planning

- This code is forked from the [trip planning notebook](https://docs.ag2.ai/notebooks/agentchat_swarm_graphrag_trip_planner#trip-planning-with-a-falkordb-graphrag-agent-using-a-swarm) from AG2.
- By [Mark](https://github.com/marklysze)
- Last revision: 03/09/2026 — migrated to AG2 0.9+ API

A trip planning swarm that creates an itinerary together with a customer. The end result is an itinerary with route times and distances calculated between activities.

## Details

The following diagram outlines the key components of the Swarm, with highlights being:

- FalkorDB agent using a GraphRAG database of restaurants and attractions
- Structured Output agent that will enforce a strict format for the accepted itinerary
- Routing agent that utilises the Google Maps API to calculate distances between activities
- Swarm orchestration utilising context variables

![Swarm Diagram](./trip_planner_data/travel-planning-overview.png)

## AG2 Features

- [Swarm Orchestration](https://docs.ag2.ai/docs/user-guide/advanced-concepts/swarm/deep-dive)
- [GraphRAG](https://github.com/ag2ai/ag2/blob/main/notebook/agentchat_graph_rag_falkordb.ipynb)
- [Structured Output](https://docs.ag2.ai/docs/use-cases/notebooks/notebooks/agentchat_structured_outputs#structured-output)

## TAGS

TAGS: trip planning, swarm, graphrag, structured output, itinerary planning, travel automation, routing agent, falkordb, google maps integration

## Installation

Requires Python >= 3.12.

### 1. Install dependencies

```bash
uv sync
```

Or with pip:

```bash
pip install "ag2[graph-rag-falkor-db]>=0.9.9" python-dotenv requests
```

### 2. Start FalkorDB

FalkorDB is required to run the GraphRAG agent. Start it with Docker:

```bash
docker run -d --name travel-planner-falkordb -p 6379:6379 falkordb/falkordb:latest
```

> **Note**: If port 6379 is already in use by another project, use a different port (e.g. `-p 6381:6379`) and set `FALKORDB_PORT=6381` in your `.env` file.

### 3. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in:
- `OPENAI_API_KEY` — required
- `FALKORDB_PORT` — change if you used a different port above
- `GOOGLE_MAP_API_KEY` — optional, needed for travel time calculation between locations

## Running the code

```bash
python main.py
```

You can interact with the system through the command line to plan a trip to Rome. Modify the initial message at the bottom of `main.py` to plan a trip to another city.

> **Tip**: After the first run, the FalkorDB graph is already populated. Switch `init_db` to `connect_db` in `main.py` for faster subsequent runs.

## Contact

- AG2 Documentation: https://docs.ag2.ai/docs/Home
- AG2 GitHub: https://github.com/ag2ai/ag2
- Discord: https://discord.gg/pAbnFJrkgZ

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](../LICENSE) for details.
