"""Data-analysis agent on AG2 Beta with a Daytona sandbox.

A single Beta `Agent` equipped with five tools that drive a fresh Daytona
sandbox: `run_python`, `list_files`, `read_text_file`, `get_artifact`, and
`get_loaded_dataset`. Exposed through `autogen.beta.ag_ui.AGUIStream`; the
frontend renders code, stdout, and inline plots as the agent iterates.
"""

from __future__ import annotations

import asyncio
import base64
import os
from contextlib import asynccontextmanager
from pathlib import Path

from daytona import AsyncDaytona, DaytonaConfig
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from autogen.beta import Agent, tool
from autogen.beta.ag_ui import AGUIStream
from autogen.beta.config import GeminiConfig, OpenAIConfig, VertexAIConfig
from autogen.beta.config.config import ModelConfig

load_dotenv()


# ---------------------------------------------------------------------------
# Sandbox singleton
# ---------------------------------------------------------------------------
#
# A single long-lived sandbox is created lazily on the first tool call and
# reused across every turn. The dataset is uploaded to `/home/daytona/data/`
# once via the `/upload` endpoint (or the `/sample` endpoint), and the agent
# calls `get_loaded_dataset()` to discover its path.


class SandboxState:
    def __init__(self) -> None:
        self._client: AsyncDaytona | None = None
        self._sandbox = None
        self._lock = asyncio.Lock()
        self.loaded_dataset: str | None = None  # absolute path inside sandbox

    async def get(self):
        async with self._lock:
            if self._sandbox is not None:
                return self._sandbox
            api_key = os.environ.get("DAYTONA_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "DAYTONA_API_KEY is required. Copy .env.example to .env and add your key."
                )
            self._client = AsyncDaytona(DaytonaConfig(api_key=api_key))
            self._sandbox = await self._client.create()
            # Pre-create a data dir and an artifacts dir — keeps paths predictable.
            await self._sandbox.process.exec("mkdir -p /home/daytona/data /home/daytona/artifacts")
            return self._sandbox

    async def shutdown(self) -> None:
        if self._sandbox is not None:
            try:
                await self._sandbox.delete()
            except Exception:  # noqa: BLE001
                pass
        if self._client is not None:
            try:
                await self._client.close()
            except Exception:  # noqa: BLE001
                pass


SANDBOX = SandboxState()


# ---------------------------------------------------------------------------
# Tools (shared across turns)
# ---------------------------------------------------------------------------

_ARTIFACT_DIR = "/home/daytona/artifacts"


@tool
async def get_loaded_dataset() -> str:
    """Return the absolute path of the dataset the user uploaded to the sandbox.

    Call this FIRST at the start of every analysis. If no dataset is loaded yet
    the tool returns a message asking the user to upload one.
    """
    if not SANDBOX.loaded_dataset:
        return "[no dataset loaded — ask the user to upload a CSV or click the sample button]"
    return SANDBOX.loaded_dataset


@tool
async def run_python(code: str) -> dict:
    """Execute Python code inside the Daytona sandbox.

    The sandbox has pandas, numpy, matplotlib, and seaborn pre-installed. Any
    plot you save under `/home/daytona/artifacts/<name>.png` (or `.svg`) will
    appear as a card in the UI — always call `plt.savefig(...)` BEFORE
    `plt.show()` or `plt.close()` and give each plot a descriptive filename.

    Returns {stdout, stderr, exit_code, new_artifacts: [filename, ...]}.
    """
    sandbox = await SANDBOX.get()

    before = await _list_artifact_names(sandbox)

    # Prepend a bit of boilerplate so matplotlib always uses a headless backend
    # and sits in the artifacts directory — stops the LLM from having to
    # remember this every call.
    preamble = (
        "import os, matplotlib\n"
        "matplotlib.use('Agg')\n"
        "import matplotlib.pyplot as plt\n"
        f"os.makedirs('{_ARTIFACT_DIR}', exist_ok=True)\n"
    )
    response = await sandbox.process.code_run(preamble + code)

    after = await _list_artifact_names(sandbox)
    new_artifacts = sorted(after - before)

    result = getattr(response, "result", "") or ""
    exit_code = getattr(response, "exit_code", 0)
    # The SDK folds stdout+stderr into `result`; expose it as stdout so the
    # agent gets the single thing it actually wants to read.
    return {
        "stdout": _truncate(result, 12_000),
        "stderr": "",
        "exit_code": exit_code,
        "new_artifacts": new_artifacts,
    }


@tool
async def list_files(path: str = "/home/daytona") -> list[str]:
    """List files under a path inside the sandbox (non-recursive)."""
    sandbox = await SANDBOX.get()
    response = await sandbox.process.exec(f"ls -1 {path!s}")
    out = getattr(response, "result", "") or ""
    return [line for line in out.splitlines() if line.strip()]


@tool
async def read_text_file(path: str, max_bytes: int = 8_000) -> str:
    """Read a text file from the sandbox (first `max_bytes` bytes)."""
    sandbox = await SANDBOX.get()
    data = await sandbox.fs.download_file(path)
    if isinstance(data, str):
        data = data.encode()
    return _truncate(data[:max_bytes].decode("utf-8", errors="replace"), max_bytes)


@tool
async def get_artifact(filename: str) -> dict:
    """Return a saved artifact (PNG/SVG/CSV/etc.) as base64.

    Pass the bare filename (e.g. `survival_by_class.png`) produced by a prior
    `run_python` call. The UI renders returned images inline as plot cards.
    """
    sandbox = await SANDBOX.get()
    path = f"{_ARTIFACT_DIR}/{filename}"
    raw = await sandbox.fs.download_file(path)
    # Daytona returns bytes; defend against any SDK quirk that hands back str.
    if isinstance(raw, str):
        raw = raw.encode("latin-1")
    if not raw:
        return {
            "filename": filename,
            "error": f"artifact is empty or missing at {path}",
        }
    return {
        "filename": filename,
        "mime": _guess_mime(filename),
        "bytes": len(raw),
        "base64": base64.b64encode(raw).decode(),
    }


# ---------------------------------------------------------------------------
# LLM provider
# ---------------------------------------------------------------------------


_PROVIDER_DEFAULTS = {
    "vertexai": {"model": "gemini-3.1-pro-preview"},
    "gemini": {"model": "gemini-2.5-pro", "env": "GEMINI_API_KEY"},
    "openai": {"model": "gpt-4o", "env": "OPENAI_API_KEY"},
}


def build_config() -> ModelConfig:
    provider = os.environ.get("LLM_PROVIDER", "vertexai").lower()
    if provider not in _PROVIDER_DEFAULTS:
        raise SystemExit(f"LLM_PROVIDER must be one of {list(_PROVIDER_DEFAULTS)}")

    model = os.environ.get("MODEL", _PROVIDER_DEFAULTS[provider]["model"])

    if provider == "vertexai":
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
        if not project:
            raise SystemExit(
                "GOOGLE_CLOUD_PROJECT is required for LLM_PROVIDER=vertexai. "
                "Run `gcloud auth application-default login` and set GOOGLE_CLOUD_PROJECT."
            )
        return VertexAIConfig(
            model=model,
            project=project,
            location=location,
            credentials=os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or None,
            streaming=True,
        )

    env = _PROVIDER_DEFAULTS[provider]["env"]
    if not os.environ.get(env):
        raise SystemExit(
            f"{env} is required for LLM_PROVIDER={provider}. "
            f"Copy .env.example to .env and add your key."
        )

    if provider == "openai":
        return OpenAIConfig(model=model, streaming=True)
    return GeminiConfig(model=model, streaming=True)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


SYSTEM_PROMPT = (
    "You are a senior data analyst. You have one tool that runs Python inside\n"
    "an isolated Daytona sandbox with pandas, numpy, matplotlib, and seaborn\n"
    "pre-installed.\n\n"
    "CRITICAL: each `run_python` call starts a FRESH Python process — variables\n"
    "do NOT persist between calls. So write SELF-CONTAINED cells, but keep them\n"
    "tight: load the CSV once at the top, then do the analysis. Do NOT split\n"
    "`import pandas`, `df = pd.read_csv(...)`, and the actual work into three\n"
    "separate calls — put them in one call.\n\n"
    "Workflow:\n"
    "  1. Call `get_loaded_dataset` ONCE to find the CSV path.\n"
    "  2. First `run_python` call: load the CSV, print `df.shape`, `df.head(3)`,\n"
    "     and `df.dtypes` so you learn the schema. Be brief — don't dump\n"
    "     `df.info()` unless you need it.\n"
    "  3. Subsequent calls: each one answers ONE sub-question end-to-end.\n"
    "     Re-load the df at the top of the cell, then do the analysis + save\n"
    "     any plots. Aim for 15–30 lines per cell.\n"
    "  4. For every plot: save to `/home/daytona/artifacts/<snake_case>.png`\n"
    "     with `plt.savefig(..., bbox_inches='tight', dpi=110); plt.close()`.\n"
    "     After the tool returns, IMMEDIATELY call `get_artifact` on every\n"
    "     filename in `new_artifacts` — this is what renders the plot in the\n"
    "     UI. Do NOT skip this step.\n"
    "  5. Write a concise final report in markdown with **Findings** (3–6\n"
    "     bullets, each with a concrete number) and **Caveats**.\n\n"
    "Rules:\n"
    "  - ALWAYS print the numbers you claim in the report — read the stdout;\n"
    "    do not fabricate values.\n"
    "  - If code errors, read the traceback and fix it in the next call.\n"
    "  - Never use `input()` or anything interactive.\n"
    "  - Use a figsize of ~(7, 4.5) and readable fonts."
)


agent = Agent(
    name="data_analyst",
    prompt=SYSTEM_PROMPT,
    config=build_config(),
    tools=[get_loaded_dataset, run_python, list_files, read_text_file, get_artifact],
)


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await SANDBOX.shutdown()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

stream = AGUIStream(agent)
app.mount("/chat", stream.build_asgi())

_here = Path(__file__).parent
app.mount("/assets", StaticFiles(directory=_here / "assets"), name="assets")


@app.get("/")
async def serve_frontend() -> FileResponse:
    return FileResponse(_here / "frontend.html")


@app.get("/healthz")
async def healthz() -> dict:
    provider = os.environ.get("LLM_PROVIDER", "vertexai").lower()
    return {
        "ok": True,
        "provider": provider,
        "model": os.environ.get("MODEL", _PROVIDER_DEFAULTS[provider]["model"]),
        "dataset": SANDBOX.loaded_dataset,
    }


@app.post("/upload")
async def upload_dataset(file: UploadFile) -> JSONResponse:
    raw = await file.read()
    sandbox = await SANDBOX.get()
    safe_name = Path(file.filename or "dataset.csv").name.replace(" ", "_")
    remote = f"/home/daytona/data/{safe_name}"
    await sandbox.fs.upload_file(raw, remote)
    SANDBOX.loaded_dataset = remote
    return JSONResponse({"path": remote, "size": len(raw), "filename": safe_name})


@app.post("/sample")
async def load_sample() -> JSONResponse:
    sample_path = _here / "data" / "titanic.csv"
    raw = sample_path.read_bytes()
    sandbox = await SANDBOX.get()
    remote = "/home/daytona/data/titanic.csv"
    await sandbox.fs.upload_file(raw, remote)
    SANDBOX.loaded_dataset = remote
    return JSONResponse({"path": remote, "size": len(raw), "filename": "titanic.csv"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _list_artifact_names(sandbox) -> set[str]:
    response = await sandbox.process.exec(f"ls -1 {_ARTIFACT_DIR} 2>/dev/null || true")
    out = getattr(response, "result", "") or ""
    return {line.strip() for line in out.splitlines() if line.strip()}


def _truncate(s: str, limit: int) -> str:
    if len(s) <= limit:
        return s
    return s[:limit] + f"\n…[truncated {len(s) - limit} chars]"


def _guess_mime(filename: str) -> str:
    ext = filename.lower().rsplit(".", 1)[-1]
    return {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "svg": "image/svg+xml",
        "csv": "text/csv",
        "json": "application/json",
        "txt": "text/plain",
    }.get(ext, "application/octet-stream")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8766"))
    uvicorn.run(app, host="0.0.0.0", port=port)
