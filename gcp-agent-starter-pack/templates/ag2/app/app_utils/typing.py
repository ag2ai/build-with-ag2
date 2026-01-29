"""Type definitions for the application."""

from pydantic import BaseModel


class Feedback(BaseModel):
    """Feedback model for logging user feedback."""

    session_id: str | None = None
    message: str | None = None
    rating: int | None = None
    metadata: dict | None = None
