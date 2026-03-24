# A2UI Flutter Demo — AG2 + A2A + A2UI

A demo showcasing **AG2's A2UIAgent** generating rich, interactive UI over the **A2A protocol**, rendered natively in **Flutter** using the official **genui** framework with the **A2UI v0.9** protocol.

## What This Demo Shows

1. A Python backend using AG2's `A2UIAgent` wrapped in an `A2aAgentServer`
2. A Flutter chat app that connects to the A2A server, sends messages via JSON-RPC, and renders A2UI surfaces as native Flutter widgets
3. Custom A2UI components (LinkedInPost, XPost) registered with the genui catalog system
4. Bidirectional interaction — button taps in the UI send actions back to the agent

### Architecture

```
┌──────────────────┐         A2A JSON-RPC         ┌─────────────────────┐
│  Flutter App     │ ──────────────────────────── │  AG2 A2A Server     │
│                  │  X-A2A-Extensions: a2ui/v0.9 │                     │
│  genui Surface   │ ◄────────────────────────────│  A2UIAgent          │
│  genui_a2a       │   TextPart + DataPart(a2ui)  │  A2UIAgentExecutor  │
│  (v0.9 renderer) │                              │  (auto-detected)    │
└──────────────────┘                              └─────────────────────┘
```

---

## Prerequisites

- **Python 3.10+**
- **Flutter SDK 3.35+** ([install guide](https://docs.flutter.dev/get-started/install))
- **Gemini API key** (A2UIAgent works best with Gemini models)
- **AG2 with A2UI support** — the `feat/a2ui-support` branch of [ag2ai/ag2](https://github.com/ag2ai/ag2)

---

## Backend Setup

### 1. Create a Python virtual environment

```bash
cd a2ui/flutter
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
```

### 2. Install dependencies

The backend requires AG2 with the `a2ui` and `a2a` extras, plus `gemini` for the Gemini LLM:

```bash
# Install from the feat/a2ui-support branch (A2UIAgent is not yet in a published release)
pip install "ag2[a2ui,a2a,gemini] @ git+https://github.com/ag2ai/ag2.git@feat/a2ui-support"
pip install python-dotenv uvicorn
```

Or if you have a local clone of the ag2 repo on the `feat/a2ui-support` branch:

```bash
pip install -e "/path/to/ag2[a2ui,a2a,gemini]"
pip install python-dotenv uvicorn
```

### 3. Set your Gemini API key

Create a `.env` file (or copy from `.env.example`):

```bash
cp .env.example .env
# Edit .env and set your key:
# GOOGLE_GEMINI_API_KEY=your-key-here
```

### 4. Run the backend

```bash
python backend.py
```

Verify the agent card:

```bash
curl http://localhost:9000/.well-known/agent-card.json | python -m json.tool
```

You should see the A2UI v0.9 extension in `capabilities.extensions`:

```json
{
  "uri": "https://a2ui.org/a2a-extension/a2ui/v0.9",
  "description": "Provides agent-driven UI using the A2UI v0.9 JSON format."
}
```

---

## Flutter Frontend Setup

### 1. Install Flutter dependencies

```bash
cd flutter_demo
flutter pub get
```

### About `genui` and `genui_a2a`

This demo uses two packages from the [flutter/genui](https://github.com/flutter/genui) project:

- **`genui`** — The core Flutter GenUI framework. Provides the `Surface` widget, `SurfaceController`, `Conversation` facade, `BasicCatalogItems` (Text, Button, Card, Column, Row, Image, Divider, TextField, ChoicePicker, etc.), and the `CatalogItem` API for registering custom components.

- **`genui_a2a`** — The A2A transport integration for genui. Provides `A2uiAgentConnector` which handles A2A JSON-RPC communication with SSE streaming, A2UI v0.9 message parsing, and extension negotiation. This is the v0.9-compatible successor to the `genui_a2ui` package on pub.dev (which only supports v0.8).

**`genui_a2a` is not yet published on pub.dev.** The `pubspec.yaml` references it as a git dependency:

```yaml
dependencies:
  genui:
    git:
      url: https://github.com/flutter/genui.git
      ref: 938a49d72208a67f67581ebe2a4f8c1bf9c26a18
      path: packages/genui
  genui_a2a:
    git:
      url: https://github.com/flutter/genui.git
      ref: 938a49d72208a67f67581ebe2a4f8c1bf9c26a18
      path: packages/genui_a2a

dependency_overrides:
  genui:
    git:
      url: https://github.com/flutter/genui.git
      ref: 938a49d72208a67f67581ebe2a4f8c1bf9c26a18
      path: packages/genui
```

The `dependency_overrides` section is necessary because `genui_a2a` declares `genui: ^0.7.0` pointing to pub.dev, but both packages need to come from the same git commit to have compatible APIs.

Once `genui_a2a` is published to pub.dev, the git references can be replaced with simple version constraints.

### 2. Run the Flutter app

With the backend running on port 9000:

```bash
# Web (easiest for development)
flutter run -d chrome

# macOS desktop
flutter run -d macos

# iOS simulator
flutter run -d ios
```

**Note:** When running on web, the backend includes CORS middleware. For mobile/desktop, the app connects directly to `localhost:9000`.

---

## What to Expect

1. Click the **"Try Demo"** button on the empty chat screen — it sends a pre-loaded H2Oh marketing brief
2. The A2UIAgent generates A2UI v0.9 operations (`createSurface`, `updateComponents`, `updateDataModel`)
3. The genui `Surface` widget renders three preview cards inline in the chat:
   - **Email preview** — basic catalog components (Card, Text, Image, Button, Divider)
   - **LinkedIn preview** — custom `LinkedInPost` component with author info, hashtags, engagement metrics
   - **X/Twitter preview** — custom `XPost` component with handle, verified badge, engagement metrics
4. Click **"Approve"** to see a scheduling surface with time-picker buttons and a custom time selector
5. Click a schedule button to trigger an agent tool call that confirms the posts are scheduled
6. Click **"Rewrite"** to regenerate all previews with a different creative angle

You can also type your own messages in the chat input at any time.

---

## Project Structure

```
a2ui/flutter/
├── README.md                 # This file
├── backend.py                # AG2 A2A server with A2UIAgent
├── social_catalog.json       # Custom A2UI catalog (LinkedInPost, XPost)
├── requirements.txt          # Python dependencies
├── .env.example              # Template for Gemini API key
├── images/                   # Static images served by the backend
│   ├── bottle-hero.png       # Product hero image
│   └── AG2-square.png        # Brand avatar image
└── flutter_demo/             # Flutter project
    ├── pubspec.yaml
    └── lib/
        ├── main.dart                          # App entry, genui wiring
        ├── models/
        │   └── chat_message.dart             # Chat message types
        ├── state/
        │   └── chat_state.dart               # ChangeNotifier state
        └── widgets/
            ├── chat_screen.dart              # Chat UI (message list + input)
            ├── message_bubble.dart           # Text message display
            ├── surface_widget.dart           # genui Surface wrapper
            └── custom/
                ├── linkedin_post_item.dart   # Custom: LinkedIn post CatalogItem
                └── x_post_item.dart          # Custom: X/Twitter post CatalogItem
```

---

## AG2 Features Used

- **[A2UIAgent](https://docs.ag2.ai/docs/user-guide/reference-agents/a2uiagent)** — Generates A2UI v0.9 operations from natural language, with schema validation and retry
- **[A2A Server](https://docs.ag2.ai/docs/user-guide/a2a/server)** — Wraps any AG2 agent as an A2A-compliant server with auto-detection for A2UIAgent
- **[A2UI Protocol](https://a2ui.org/)** — Open protocol for agent-generated rich UI (v0.9)
