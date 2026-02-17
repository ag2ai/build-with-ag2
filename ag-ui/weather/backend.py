"""Agent chat with weather tool and AG2 pixel-art theme."""

from __future__ import annotations

from typing import Annotated

import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from autogen import ConversableAgent, LLMConfig
from autogen.ag_ui import AGUIStream
from dotenv import load_dotenv

load_dotenv()


def get_weather_condition(code: int) -> str:
    """Map WMO weather code to human-readable condition."""
    conditions = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Foggy", 48: "Depositing rime fog",
        51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
        61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
        80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
        95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
    }
    return conditions.get(code, "Unknown")


async def get_weather(
    location: Annotated[str, "City name to get weather for"],
) -> dict[str, str | float]:
    """Get current weather for a location using the Open-Meteo API."""
    async with httpx.AsyncClient() as client:
        geocoding_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1"
        geocoding_response = await client.get(geocoding_url)
        geocoding_data = geocoding_response.json()

        if not geocoding_data.get("results"):
            return {"error": f"Location '{location}' not found"}

        result = geocoding_data["results"][0]
        lat, lon, name = result["latitude"], result["longitude"], result["name"]

        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,apparent_temperature,relative_humidity_2m,"
            f"wind_speed_10m,wind_gusts_10m,weather_code"
        )
        weather_response = await client.get(weather_url)
        current = weather_response.json()["current"]

        return {
            "temperature": current["temperature_2m"],
            "feelsLike": current["apparent_temperature"],
            "humidity": current["relative_humidity_2m"],
            "windSpeed": current["wind_speed_10m"],
            "windGust": current["wind_gusts_10m"],
            "conditions": get_weather_condition(current["weather_code"]),
            "location": name,
        }


agent = ConversableAgent(
    name="ag2_assistant",
    system_message=(
        "You are AG2's friendly AI assistant. AG2 is the open-source AgentOS for "
        "building production-ready multi-agent AI systems. You're knowledgeable about "
        "AG2, AI agents, and Python programming. Be concise, helpful, and friendly. "
        "When showing code, use markdown code blocks with language tags. "
        "You can also check the weather for any city using the get_weather tool."
    ),
    llm_config=LLMConfig({"model": "gpt-5-mini", "stream": True}),
    functions=[get_weather],
)

stream = AGUIStream(agent)
agentic_chat_app = FastAPI()

agentic_chat_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

assets_dir = Path(__file__).parent / "assets"
agentic_chat_app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
agentic_chat_app.mount("/chat", stream.build_asgi())


@agentic_chat_app.get("/")
async def serve_frontend():
    return FileResponse(Path(__file__).parent / "frontend.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(agentic_chat_app, host="0.0.0.0", port=8456)
