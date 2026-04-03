#!/usr/bin/env bash
set -euo pipefail

echo "=================================================="
echo "AI-DAN Local Startup (Mac/Linux)"
echo "=================================================="
echo

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is not installed or not on PATH."
  echo "Install Python 3.11+ and try again."
  exit 1
fi

echo "[1/3] Running environment setup..."
bash "${SCRIPT_DIR}/setup_env.sh"
echo

echo "[2/3] Starting AI-DAN backend (FastAPI)..."
cd "${REPO_ROOT}"
UVICORN_HOST="${UVICORN_HOST:-127.0.0.1}"
python3 -m uvicorn main:app --host "${UVICORN_HOST}" --port 8000 --reload &
BACKEND_PID=$!
echo "Backend started (PID: ${BACKEND_PID})"
echo "Backend URL: http://localhost:8000"
echo "Backend docs: http://localhost:8000/docs"
echo

sleep 2
if ! kill -0 "${BACKEND_PID}" >/dev/null 2>&1; then
  echo "[ERROR] Backend failed to start. Check logs above and try again."
  exit 1
fi

cleanup() {
  echo
  echo "Stopping AI-DAN services..."
  if kill -0 "${BACKEND_PID}" >/dev/null 2>&1; then
    kill "${BACKEND_PID}" >/dev/null 2>&1 || true
  fi
  echo "Stopped."
}

trap cleanup EXIT INT TERM

echo "[3/3] Starting AI-DAN Command Center (Streamlit)..."
echo "Frontend URL: http://localhost:8501"
echo
STREAMLIT_SERVER_ADDRESS="${STREAMLIT_SERVER_ADDRESS:-127.0.0.1}"
python3 -m streamlit run frontend/command_center.py --server.port 8501 --server.address "${STREAMLIT_SERVER_ADDRESS}"
