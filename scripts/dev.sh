#!/usr/bin/env bash
# dev.sh — run uvicorn for local development
# Usage:
#   chmod +x dev.sh
#   ./dev.sh

set -euo pipefail


VENV="./venv"
APP_MODULE="main:app"
HOST="127.0.0.1"
PORT=8000

# activate venv if exists
if [ -f "${VENV}/bin/activate" ]; then
  # shellcheck source=/dev/null
  . "${VENV}/bin/activate"
else
  echo "Warning: virtualenv not found at ${VENV}. Continuing with system python."
fi

echo "Starting uvicorn (dev) ${APP_MODULE} on ${HOST}:${PORT} (reload, debug logs)"
uvicorn ${APP_MODULE} --host ${HOST} --port ${PORT} --reload --log-level debug
