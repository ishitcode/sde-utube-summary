#!/usr/bin/env bash

set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
RAG_DIR="$ROOT_DIR/rag-service"
BACKEND_DIR="$ROOT_DIR/backend-node"
FRONTEND_DIR="$ROOT_DIR/frontend"
RAG_VENV_PYTHON="$RAG_DIR/.venv/bin/python"

cd "$ROOT_DIR"

if ! command -v node >/dev/null 2>&1; then
  echo "Node.js is required but not installed or not on PATH."
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required but not installed or not on PATH."
  exit 1
fi

if command -v python3.12 >/dev/null 2>&1; then
  PYTHON_BIN="python3.12"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Python is required but not installed or not on PATH."
  exit 1
fi

if command -v lsof >/dev/null 2>&1; then
  lsof -ti :4000 | xargs -r kill -9 || true
fi

if [ ! -f "$RAG_VENV_PYTHON" ]; then
  "$PYTHON_BIN" -m venv "$RAG_DIR/.venv"
fi

"$RAG_VENV_PYTHON" -m pip install -r "$RAG_DIR/requirements.txt"

echo "Starting RAG service..."
(
  cd "$RAG_DIR"
  "$RAG_VENV_PYTHON" -m uvicorn main:app --host 0.0.0.0 --port 8001
) &

RAG_PID=$!

sleep 2

echo "Starting Node backend..."
(
  cd "$BACKEND_DIR"
  npm start
) &

NODE_PID=$!

sleep 2

echo "Starting frontend..."
(
  cd "$FRONTEND_DIR"
  npm run dev -- --host 0.0.0.0
) &

FRONTEND_PID=$!

echo "All services launched."
echo "RAG service PID: $RAG_PID"
echo "Node backend PID: $NODE_PID"
echo "Frontend PID: $FRONTEND_PID"
echo "Press Ctrl+C to stop all services."

cleanup() {
  kill "$RAG_PID" "$NODE_PID" "$FRONTEND_PID" 2>/dev/null || true
  exit 0
}

trap cleanup INT TERM

wait "$RAG_PID" "$NODE_PID" "$FRONTEND_PID"
