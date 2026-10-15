#!/usr/bin/env bash
# Mantis Mobile Forensics - Development Mode Launcher
# Runs the Python FastAPI backend and React Vite frontend concurrently.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=========================================================="
echo "  Mantis Mobile Forensics (MMF) - Development Mode"
echo "=========================================================="

export PYTHONPATH="${ROOT_DIR}/packages/mmf_core/src:${ROOT_DIR}/apps/api/src:${PYTHONPATH:-}"
export MMF_DATA_DIR="${ROOT_DIR}/data"
export MMF_SESSION_TOKEN="dev_session_token_123456"

mkdir -p "${MMF_DATA_DIR}"

cleanup() {
    echo ""
    echo "[DEV] Shutting down development services..."
    if [ -n "${BACKEND_PID:-}" ]; then
        kill "${BACKEND_PID}" 2>/dev/null || true
    fi
    if [ -n "${FRONTEND_PID:-}" ]; then
        kill "${FRONTEND_PID}" 2>/dev/null || true
    fi
    wait 2>/dev/null || true
    echo "[DEV] Services stopped safely."
}
trap cleanup EXIT INT TERM

echo "[DEV] Starting FastAPI Forensic Backend on 127.0.0.1:8765..."
python3 -m mmf_api.main --host 127.0.0.1 --port 8765 --token "${MMF_SESSION_TOKEN}" --data-dir "${MMF_DATA_DIR}" &
BACKEND_PID=$!

# Wait for backend to be ready
echo "[DEV] Waiting for forensic API health check..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:8765/health >/dev/null 2>&1; then
        echo "[DEV] Forensic API is ready and healthy."
        break
    fi
    sleep 0.5
done

echo "[DEV] Starting Vite React development server on 127.0.0.1:5173..."
cd "${ROOT_DIR}/apps/web"
npx vite --host 127.0.0.1 --port 5173 &
FRONTEND_PID=$!

echo "=========================================================="
echo "  MMF Dev Server Running:"
echo "  - Frontend: http://127.0.0.1:5173"
echo "  - Backend:  http://127.0.0.1:8765"
echo "  - Docs:     http://127.0.0.1:8765/docs"
echo "  Press Ctrl+C to stop both services."
echo "=========================================================="

wait
