#!/usr/bin/env bash
# prod.sh — start uvicorn in background (nohup) for production
# Usage:
#   sudo cp prod.sh /usr/local/bin/ && sudo chmod +x /usr/local/bin/prod.sh
#   cd /path/to/project && ./prod.sh start
#
# Commands: ./prod.sh start|stop|status|restart

set -euo pipefail

VENV="/home/noc/smartlinkAPI/venv/"
WORKDIR="/home/noc/smartlinkAPI/"
APP_MODULE="main:app"
HOST="127.0.0.1"
PORT=8000
LOGDIR="~/logs/"
LOGFILE="${LOGDIR}/fastapi.out"

start() {
  echo "Starting FastAPI (prod) in background..."
  # prepare log dir
  if [ ! -d "${LOGDIR}" ]; then
    sudo mkdir -p "${LOGDIR}"
    sudo chown "$USER":"$USER" "${LOGDIR}"
  fi

  cd "${WORKDIR}"
  if [ -f "${VENV}/bin/activate" ]; then
    # shellcheck source=/dev/null
    . "${VENV}/bin/activate"
  fi

  # stop existing
  pkill -f "uvicorn ${APP_MODULE}" || true

  nohup uvicorn ${APP_MODULE} \
    --host ${HOST} --port ${PORT} \
    --proxy-headers \
    > "${LOGFILE}" 2>&1 &

  sleep 0.5
  echo "Started. Logs: ${LOGFILE}"
  ps aux | grep -E "uvicorn .*${APP_MODULE}" | grep -v grep || true
}

stop() {
  echo "Stopping FastAPI (prod)..."
  pkill -f "uvicorn ${APP_MODULE}" || true
  sleep 0.5
  echo "Stopped."
}

status() {
  echo "Status:"
  ps aux | grep -E "uvicorn .*${APP_MODULE}" | grep -v grep || echo "No running process found."
  echo "Last 200 log lines:"
  tail -n 200 "${LOGFILE}" || true
}

case "${1:-}" in
  start) start ;;
  stop) stop ;;
  restart) stop; sleep 1; start ;;
  status) status ;;
  *) echo "Usage: $0 {start|stop|restart|status}" ; exit 1 ;;
esac
