#!/usr/bin/env bash

set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
RAG_DIR="$ROOT_DIR/rag-service"
BACKEND_DIR="$ROOT_DIR/backend-node"
FRONTEND_DIR="$ROOT_DIR/frontend"

cd "$ROOT_DIR"

if ! command -v node >/dev/null 2>&1; then
  echo "Node.js is required but not installed or not on PATH."
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required but not installed or not on PATH."
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required but not installed or not on PATH. See https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi

if command -v lsof >/dev/null 2>&1; then
  lsof -ti :4000 | xargs -r kill -9 || true
fi

uv sync --project "$RAG_DIR"

echo "Starting RAG service..."
(
  cd "$RAG_DIR"
  uv run --project "$RAG_DIR" uvicorn main:app --host 0.0.0.0 --port 8001
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
