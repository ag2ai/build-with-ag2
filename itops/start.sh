#!/usr/bin/env bash
#
# Stand up the IT-Ops Triage demo: backend (FastAPI/WebSocket on :8000) +
# frontend (Vite dev server on :5173). Installs deps if missing, frees the
# ports, starts both, and stops both on Ctrl+C.
#
#   ./start.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

BACKEND_PORT=8000
FRONTEND_PORT=5173

# ── Ensure Python deps (.venv with fastapi/uvicorn) ──────────────────────
if [ ! -x ".venv/bin/python" ] || ! .venv/bin/python -c "import uvicorn, fastapi" >/dev/null 2>&1; then
  echo "→ Installing Python deps (uv sync)…"
  uv sync
fi

# ── Ensure frontend deps ─────────────────────────────────────────────────
if [ ! -d "frontend/node_modules" ]; then
  echo "→ Installing frontend deps (npm install)…"
  ( cd frontend && npm install )
fi

# ── Warn if no Gemini key (agents need it) ───────────────────────────────
if ! { [ -f .env ] && grep -qiE 'GEMINI_API_KEY|GOOGLE_API_KEY' .env; } \
   && [ -z "${GEMINI_API_KEY:-}${GOOGLE_API_KEY:-}" ]; then
  echo "⚠  No Gemini key found — set GEMINI_API_KEY (or GOOGLE_API_KEY) in .env, or agents will fail."
fi

# ── Free the ports (kill anything already listening) ─────────────────────
lsof -ti:"$BACKEND_PORT"  2>/dev/null | xargs kill 2>/dev/null || true
lsof -ti:"$FRONTEND_PORT" 2>/dev/null | xargs kill 2>/dev/null || true
sleep 1

# ── Stop both on exit ────────────────────────────────────────────────────
cleanup() {
  trap - INT TERM EXIT
  echo
  echo "→ Stopping…"
  kill "${BACKEND_PID:-}" "${FRONTEND_PID:-}" 2>/dev/null || true
  lsof -ti:"$BACKEND_PORT"  2>/dev/null | xargs kill 2>/dev/null || true
  lsof -ti:"$FRONTEND_PORT" 2>/dev/null | xargs kill 2>/dev/null || true
}
trap cleanup INT TERM EXIT

# ── Start both ───────────────────────────────────────────────────────────
echo "→ Starting backend  on http://127.0.0.1:${BACKEND_PORT}"
( cd it_ops_app && exec ../.venv/bin/python -m uvicorn server:app --host 127.0.0.1 --port "$BACKEND_PORT" ) &
BACKEND_PID=$!

echo "→ Starting frontend on http://localhost:${FRONTEND_PORT}"
( cd frontend && exec npm run dev ) &
FRONTEND_PID=$!

cat <<EOF

  ✅ Up:
     Frontend → http://localhost:${FRONTEND_PORT}   (open this; click "Start Simulation")
     Backend  → http://127.0.0.1:${BACKEND_PORT}

  Logs from both stream below. Press Ctrl+C to stop both.

EOF

wait
