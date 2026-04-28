# ruff: noqa: E402
# load_dotenv() must run before the autogen imports so provider-specific
# clients (Gemini, OpenAI) see GEMINI_API_KEY / etc. at construction time.
import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from autogen.beta.ag_ui.stream import AGUIStream

from .agents.commentator import build_commentator
from .agents.detective import build_detective
from .agents.suspect import build_suspect
from .cases.blackwood_estate import (
    ALL_PROFILES,
    CASE_BANNER,
    CASE_TITLE,
    MURDER_LOCATION,
    MURDER_WINDOW,
    VICTIM,
    format_suspect_summary,
)
from .clock import GAME_CLOCK
from .commentary import CommentaryEngine, set_engine
from .config import GAME_DURATION_SECONDS
from .game_master import GAME_MASTER
from .memory import CASE_MEMORY, _to_plain

APP_DIR = Path(__file__).parent
STATIC_DIR = APP_DIR / "static"
IMAGES_DIR = APP_DIR.parent / "Images"


def create_app() -> Starlette:
    from contextlib import asynccontextmanager

    suspects = {p.name: build_suspect(p) for p in ALL_PROFILES}
    detective = build_detective(suspects)
    commentator = build_commentator()
    engine = CommentaryEngine(commentator)
    set_engine(engine)

    # Reset game clock on app boot
    GAME_CLOCK.reset(GAME_DURATION_SECONDS)

    routes: list = []
    for name, actor in suspects.items():
        routes.append(Route(f"/agent/{name}", AGUIStream(actor).build_asgi()))

    routes.append(Route("/agent/detective", AGUIStream(detective).build_asgi()))
    routes.append(Route("/agent/commentator", AGUIStream(commentator).build_asgi()))
    routes.append(Route("/case", case_info))
    routes.append(Route("/suspects", suspects_info))
    routes.append(Route("/reset", reset_game, methods=["POST"]))
    routes.append(Route("/notebook/stream", notebook_stream))
    routes.append(Route("/notebook/snapshot", notebook_snapshot))
    routes.append(Route("/commentary/stream", commentary_stream))
    routes.append(Route("/clock/stream", clock_stream))
    routes.append(
        Mount("/images", app=StaticFiles(directory=IMAGES_DIR), name="images")
    )
    routes.append(
        Mount("/", app=StaticFiles(directory=STATIC_DIR, html=True), name="static")
    )

    @asynccontextmanager
    async def lifespan(app):
        await engine.start()
        try:
            yield
        finally:
            engine.stop()

    return Starlette(routes=routes, lifespan=lifespan)


async def case_info(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "title": CASE_TITLE,
            "victim": VICTIM,
            "murder_window": list(MURDER_WINDOW),
            "murder_location": MURDER_LOCATION,
            "banner": f"/images/{CASE_BANNER}",
            "game_over": GAME_MASTER.is_terminated,
            "clock_remaining": GAME_CLOCK.remaining(),
            "clock_duration": GAME_CLOCK.duration,
        }
    )


async def suspects_info(request: Request) -> JSONResponse:
    return JSONResponse(format_suspect_summary())


async def reset_game(request: Request) -> JSONResponse:
    GAME_CLOCK.reset(GAME_DURATION_SECONDS)
    GAME_MASTER.reset()
    CASE_MEMORY.reset()
    return JSONResponse({"ok": True, "clock_remaining": GAME_CLOCK.remaining()})


async def notebook_snapshot(request: Request) -> StreamingResponse:  # type: ignore[override]
    payload = {
        "turns": [_to_plain(t) for t in CASE_MEMORY.interrogation_log],
        "facts": [_to_plain(f) for f in CASE_MEMORY.verified_facts],
    }

    async def one():
        yield json.dumps(payload)

    return StreamingResponse(one(), media_type="application/json")


async def notebook_stream(request: Request) -> StreamingResponse:
    queue: asyncio.Queue = asyncio.Queue()

    def on_change(kind: str, payload: dict) -> None:
        queue.put_nowait((kind, payload))

    CASE_MEMORY.subscribe(on_change)

    async def gen():
        try:
            snapshot = {
                "turns": [_to_plain(t) for t in CASE_MEMORY.interrogation_log],
                "facts": [_to_plain(f) for f in CASE_MEMORY.verified_facts],
            }
            yield f"event: snapshot\ndata: {json.dumps(snapshot)}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    kind, payload = await asyncio.wait_for(queue.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                yield f"event: {kind}\ndata: {json.dumps(payload)}\n\n"
        finally:
            CASE_MEMORY.unsubscribe(on_change)

    return StreamingResponse(gen(), media_type="text/event-stream")


async def commentary_stream(request: Request) -> StreamingResponse:
    from .commentary import get_engine

    engine = get_engine()
    if engine is None:

        async def empty():
            yield "event: error\ndata: no engine\n\n"

        return StreamingResponse(empty(), media_type="text/event-stream")

    q = engine.subscribe()

    async def gen():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    line = await asyncio.wait_for(q.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                payload = {"timestamp": line.timestamp, "text": line.text}
                yield f"event: commentary\ndata: {json.dumps(payload)}\n\n"
        finally:
            engine.unsubscribe(q)

    return StreamingResponse(gen(), media_type="text/event-stream")


async def clock_stream(request: Request) -> StreamingResponse:
    async def gen():
        while True:
            if await request.is_disconnected():
                break
            rem = GAME_CLOCK.remaining()
            payload = {
                "remaining": rem,
                "duration": GAME_CLOCK.duration,
                "expired": GAME_CLOCK.expired,
            }
            yield f"event: tick\ndata: {json.dumps(payload)}\n\n"
            if rem <= 0:
                break
            await asyncio.sleep(1.0)

    return StreamingResponse(gen(), media_type="text/event-stream")


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
