"""Integration tests for the AG2 agent."""

from app.agent import root_agent


def test_agent_responds() -> None:
    """Test that the AG2 agent processes a message and returns a response."""
    result = root_agent.run(
        message="What's the weather in San Francisco?",
        max_turns=5,
    )

    # Consume events to populate messages
    for _ in result.events:
        pass

    assert result is not None
    assert len(result.messages) > 0

    # Verify we got a response with content
    has_content = False
    for msg in result.messages:
        if msg.get("content"):
            has_content = True
            break
    assert has_content, "Expected at least one message with content"


def test_agent_uses_weather_tool() -> None:
    """Test that the agent correctly uses the weather tool."""
    result = root_agent.run(
        message="What is the weather like in SF?",
        max_turns=5,
    )

    # Consume events to populate messages
    for _ in result.events:
        pass

    assert result is not None
    assert len(result.messages) > 0

    # Check that the response mentions weather-related content
    all_content = " ".join(
        msg.get("content", "") for msg in result.messages if msg.get("content")
    )

    # The weather tool returns "60 degrees and foggy" for SF
    assert (
        "60" in all_content or "foggy" in all_content
    ), f"Expected weather info in response. Got: {all_content[:200]}"


def test_agent_uses_time_tool() -> None:
    """Test that the agent correctly uses the time tool."""
    result = root_agent.run(
        message="What time is it right now?",
        max_turns=5,
    )

    # Consume events to populate messages
    for _ in result.events:
        pass

    assert result is not None
    assert len(result.messages) > 0

    # Check that the response mentions time-related content
    all_content = " ".join(
        msg.get("content", "") for msg in result.messages if msg.get("content")
    )

    # The time tool returns UTC time
    assert (
        "UTC" in all_content or ":" in all_content
    ), f"Expected time info in response. Got: {all_content[:200]}"
