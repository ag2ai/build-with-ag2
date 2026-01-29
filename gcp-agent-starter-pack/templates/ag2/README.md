# AG2 Agent Template for Google Cloud

A remote template for [agent-starter-pack](https://github.com/GoogleCloudPlatform/agent-starter-pack) that creates an [AG2](https://ag2.ai) agent deployed on Google Cloud Run with [A2A protocol](https://a2a-protocol.org/) support.

## Quick Start

```bash
uvx agent-starter-pack create my-agent \
  -a https://github.com/ag2ai/build-with-ag2/tree/main/gcp-agent-starter-pack/templates/ag2
```

## What You Get

- **AG2 `ConversableAgent`** with Google Gemini (Vertex AI or API key)
- **A2A protocol** support using AG2's native `A2aAgentServer`
- **Cloud Run** deployment with Terraform
- **CI/CD** with Cloud Build or GitHub Actions
- **OpenTelemetry** tracing and Cloud Logging
- Example tools (weather, time)

## Architecture

This template uses `custom_a2a` as its `base_template`, which provides the "bring your own framework" A2A infrastructure. AG2's native A2A support (`A2aAgentServer`) handles the protocol implementation.

### Key Files

| File | Purpose |
|------|---------|
| `app/agent.py` | AG2 ConversableAgent with tools |
| `app/fast_api_app.py` | FastAPI + AG2 A2aAgentServer |
| `deployment/` | Terraform for Cloud Run (from base template) |

## Local Development

### Prerequisites

Set up a Google Gemini API key for AG2 to use Google Gemini models:

```bash
export GOOGLE_GEMINI_API_KEY="your-api-key"
```

Documentation for using [Google Vertex AI with AG2 agents](https://docs.ag2.ai/latest/docs/user-guide/models/google-vertexai/).

### Running Locally

After generating your project:

```bash
cd my-agent
make install    # Install dependencies
make run        # Run locally on port 8000
make test       # Run tests
make playground # Interactive testing
```

Or run directly:

```bash
uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8000
```

## Customization

Edit `app/agent.py` to modify your agent:

- Change the system message and persona
- Add or replace tools using `@agent.register_for_llm` and `@agent.register_for_execution`
- Configure LLM parameters (model, temperature, etc.)
- Switch to multi-agent patterns with group chat

See [AG2 documentation](https://docs.ag2.ai) for advanced patterns.

## A2A Protocol

The agent is served via the A2A protocol, enabling:

- **Cross-framework communication**: Connect with agents built in other frameworks
- **Remote tool execution**: Tools run on the server, results returned to clients
- **Human-in-the-loop**: Support for human input via A2A input requests

### Testing with curl

```bash
# Check agent card
curl http://localhost:8000/.well-known/agent.json

# Send a message
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "id": "1",
    "params": {
      "message": {
        "messageId": "msg-1",
        "role": "user",
        "parts": [{"kind": "text", "text": "What is the weather in San Francisco?"}]
      }
    }
  }'
```

### Testing with Python A2A Client

```python
import asyncio
from autogen.a2a import A2aRemoteAgent

async def main():
    remote = A2aRemoteAgent(name="client", url="http://localhost:8000")
    response = await remote.a_run(message="What's the weather in SF?")

    # Consume events to populate messages
    async for event in response.events:
        pass

    # Access the response messages
    if response.messages:
        print(response.messages[-1].get("content"))

asyncio.run(main())
```

## Learn More

- [AG2 Documentation](https://docs.ag2.ai)
- [AG2 A2A Guide](https://docs.ag2.ai/latest/docs/user-guide/a2a/)
- [Agent Starter Pack Docs](https://googlecloudplatform.github.io/agent-starter-pack/)
- [A2A Protocol](https://a2a-protocol.org/)
