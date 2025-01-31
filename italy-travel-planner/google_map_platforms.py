import json
import os
from pydantic import BaseModel
import requests
from autogen import SwarmResult


class Event(BaseModel):
    type: str  # Attraction, Restaurant, Travel
    location: str
    city: str
    description: str


class Day(BaseModel):
    events: list[Event]


class Itinerary(BaseModel):
    days: list[Day]


def _fetch_travel_time(origin: str, destination: str) -> dict:
    """Retrieves route information using Google Maps Directions API.
    API documentation at https://developers.google.com/maps/documentation/directions/get-directions
    """
    endpoint = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": destination,
        "mode": "walking",  # driving (default), bicycling, transit
        "key": os.environ.get("GOOGLE_MAP_API_KEY"),
    }

    response = requests.get(endpoint, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return {
            "error": "Failed to retrieve the route information",
            "status_code": response.status_code,
        }


def update_itinerary_with_travel_times(context_variables: dict) -> SwarmResult:
    """Update the complete itinerary with travel times between each event."""
    """
    Retrieves route information using Google Maps Directions API.
    API documentation at https://developers.google.com/maps/documentation/directions/get-directions
    """

    # Ensure that we have a structured itinerary, if not, back to the structured_output_agent to make it
    if context_variables.get("structured_itinerary") is None:
        return SwarmResult(
            agent="structured_output_agent",
            values="Structured itinerary not found, please create the structured output, structured_output_agent.",
        )
    elif "timed_itinerary" in context_variables:
        return SwarmResult(
            values="Timed itinerary already done, inform the customer that their itinerary is ready!"
        )

    # Process the itinerary, converting it back to an object and working through each event to work out travel time and distance
    itinerary_object = Itinerary.model_validate(
        json.loads(context_variables["structured_itinerary"])
    )
    for day in itinerary_object.days:
        events = day.events
        new_events = []
        pre_event, cur_event = None, None
        event_count = len(events)
        index = 0
        while index < event_count:
            if index > 0:
                pre_event = events[index - 1]

            cur_event = events[index]
            if pre_event:
                origin = ", ".join([pre_event.location, pre_event.city])
                destination = ", ".join([cur_event.location, cur_event.city])
                maps_api_response = _fetch_travel_time(
                    origin=origin, destination=destination
                )
                try:
                    leg = maps_api_response["routes"][0]["legs"][0]
                    travel_time_txt = (
                        f"{leg['duration']['text']}, ({leg['distance']['text']})"
                    )
                    new_events.append(
                        Event(
                            type="Travel",
                            location=f"walking from {pre_event.location} to {cur_event.location}",
                            city=cur_event.city,
                            description=travel_time_txt,
                        )
                    )
                except Exception:
                    print(
                        f"Note: Unable to get travel time from {origin} to {destination}"
                    )
            new_events.append(cur_event)
            index += 1
        day.events = new_events

    context_variables["timed_itinerary"] = itinerary_object.model_dump()

    return SwarmResult(
        context_variables=context_variables,
        values="Timed itinerary added to context with travel times",
    )
