"""Commentary engine.

Listens to CaseMemory deltas and asks the commentator Actor for a
one-liner each time something dramatic happens. The generated lines are
published on an in-process queue that the frontend subscribes to via
/commentary/stream.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any

from autogen.beta import Actor

from .memory import CASE_MEMORY


@dataclass
class CommentaryLine:
    timestamp: float
    seed: str
    text: str


class CommentaryEngine:
    def __init__(self, commentator: Actor, *, cadence_seconds: float = 8.0) -> None:
        self._commentator = commentator
        self._cadence = cadence_seconds
        self._queue: asyncio.Queue = asyncio.Queue()
        self._lines: list[CommentaryLine] = []
        self._subs: list[asyncio.Queue] = []
        self._last_fire: float = 0.0
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._worker())
        CASE_MEMORY.subscribe(self._on_change)

    def stop(self) -> None:
        CASE_MEMORY.unsubscribe(self._on_change)
        if self._task:
            self._task.cancel()
            self._task = None

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subs.append(q)
        # Replay history
        for line in self._lines:
            q.put_nowait(line)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        try:
            self._subs.remove(q)
        except ValueError:
            pass

    def _on_change(self, kind: str, payload: dict[str, Any]) -> None:
        # Seed the queue with a short description of the event
        if kind == "fact":
            seed = (
                f"Suspect {payload['suspect']} was just forced to surrender "
                f"their {payload['data_source']} records. Here are the rows: "
                f"{payload['result'][:220]}."
            )
        elif kind == "turn":
            seed = (
                f"The detective questioned {payload['suspect']}: "
                f"'{payload['question'][:120]}'. Reply: "
                f"{payload['answer'][:160]}"
            )
        else:
            return
        self._queue.put_nowait((kind, seed))

    async def _worker(self) -> None:
        while True:
            try:
                kind, seed = await self._queue.get()
            except asyncio.CancelledError:
                break
            # Rate-limit
            now = time.time()
            if now - self._last_fire < self._cadence:
                # Drop lower-priority events during cooldown
                if kind == "turn":
                    continue
            self._last_fire = time.time()
            try:
                reply = await self._commentator.ask(seed)
                text = (reply.body or "").strip()
            except Exception as e:  # pragma: no cover
                text = f"(commentary error: {e})"
            if not text:
                continue
            line = CommentaryLine(timestamp=time.time(), seed=seed, text=text)
            self._lines.append(line)
            for q in list(self._subs):
                try:
                    q.put_nowait(line)
                except Exception:
                    pass


_ENGINE: CommentaryEngine | None = None


def set_engine(engine: CommentaryEngine) -> None:
    global _ENGINE
    _ENGINE = engine


def get_engine() -> CommentaryEngine | None:
    return _ENGINE
