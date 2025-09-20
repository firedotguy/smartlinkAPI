#!/usr/bin/env bash
# prod.sh — start uvicorn in background (nohup) for production
# Usage:
#   sudo cp prod.sh /usr/local/bin/ && sudo chmod +x /usr/local/bin/prod.sh
#   cd /path/to/project && ./prod.sh start
#
# Commands:
#   ./prod.sh start
#   ./prod.sh stop
#   ./prod.sh restart
#   ./prod.sh status [LINES]   # LINES - optional number of log lines. default 200. 0 = all.

set -euo pipefail

# CONFIG — подстрой под своё окружение:
VENV="/home/noc/smartlinkAPI/venv"
WORKDIR="/home/noc/smartlinkAPI"
APP_MODULE="main:app"
HOST="127.0.0.1"
PORT=8000
DEFAULT_TAIL_LINES=200

# Determine "real" user (works if script run with sudo)
if [ -n "${SUDO_USER:-}" ]; then
  RUN_AS="${SUDO_USER}"
else
  RUN_AS="${USER:-$(whoami)}"
fi

# Home dir of run-as user
HOME_DIR="$(eval echo "~${RUN_AS}")"

# Log dir and files (no ~ in strings)
LOGDIR="${HOME_DIR}/logs"
LOGFILE="${LOGDIR}/fastapi.out"
PIDFILE="${LOGDIR}/fastapi.pid"

UVICORN_BIN="${VENV%/}/bin/uvicorn"

start() {
  echo "Starting FastAPI (prod) in background..."

  # prepare log dir
  if [ ! -d "${LOGDIR}" ]; then
    sudo mkdir -p "${LOGDIR}"
    sudo chown "${RUN_AS}:${RUN_AS}" "${LOGDIR}"
    sudo chmod 755 "${LOGDIR}"
  fi

  # go to workdir
  cd "${WORKDIR}"

  # activate venv if exists
  if [ -f "${VENV%/}/bin/activate" ]; then
    # shellcheck source=/dev/null
    . "${VENV%/}/bin/activate"
  fi

  # stop existing (use PIDFILE if exists)
  if [ -f "${PIDFILE}" ]; then
    oldpid="$(cat "${PIDFILE}")" || true
    if [ -n "${oldpid}" ] && ps -p "${oldpid}" > /dev/null 2>&1; then
      echo "Killing existing pid ${oldpid}..."
      kill "${oldpid}" || true
      sleep 0.5
    fi
    rm -f "${PIDFILE}" || true
  else
    # fallback: pkill by pattern (less preferred)
    pkill -f "uvicorn ${APP_MODULE}" || true
  fi

  # start uvicorn using venv binary if available, otherwise rely on PATH
  if [ -x "${UVICORN_BIN}" ]; then
    UVICORN_CMD="${UVICORN_BIN}"
  else
    UVICORN_CMD="uvicorn"
  fi

  # run in background and record pid
  nohup ${UVICORN_CMD} "${APP_MODULE}" \
    --host "${HOST}" --port "${PORT}" \
    --proxy-headers \
    > "${LOGFILE}" 2>&1 &

  echo $! > "${PIDFILE}"
  sleep 0.5

  echo "Started. PID: $(cat "${PIDFILE}")"
  echo "Logs: ${LOGFILE}"
  ps -o pid,cmd -p "$(cat "${PIDFILE}")" || true
}

stop() {
  echo "Stopping FastAPI (prod)..."
  if [ -f "${PIDFILE}" ]; then
    pid="$(cat "${PIDFILE}" 2>/dev/null || true)"
    if [ -n "${pid}" ] && ps -p "${pid}" > /dev/null 2>&1; then
      kill "${pid}" || true
      sleep 0.5
      echo "Stopped pid ${pid}."
    else
      echo "PID ${pid} not running or missing; attempting pkill fallback..."
      pkill -f "uvicorn ${APP_MODULE}" || true
    fi
    rm -f "${PIDFILE}" || true
  else
    echo "No pidfile found; attempting pkill fallback..."
    pkill -f "uvicorn ${APP_MODULE}" || true
  fi
}

status() {
  # accept optional first arg as lines to tail
  local lines="${1:-$DEFAULT_TAIL_LINES}"

  echo "Status:"
  if [ -f "${PIDFILE}" ]; then
    pid="$(cat "${PIDFILE}" 2>/dev/null || true)"
    if [ -n "${pid}" ] && ps -p "${pid}" > /dev/null 2>&1; then
      echo "Process running: PID ${pid}"
      ps -o pid,cmd -p "${pid}" || true
    else
      echo "PID file exists but process not running (PID: ${pid})"
    fi
  else
    echo "No pidfile. Attempting to find process by pattern:"
    pgrep -af "uvicorn ${APP_MODULE}" || echo "No running process found."
  fi

  echo
  # Show logs according to requested lines
  if [ -f "${LOGFILE}" ]; then
    if [[ ! "${lines}" =~ ^[0-9]+$ ]]; then
      echo "Invalid lines value: ${lines}. Must be an integer >= 0."
      return 1
    fi

    if [ "${lines}" -eq 0 ]; then
      echo "Showing entire logfile: ${LOGFILE}"
      cat "${LOGFILE}" || true
    else
      echo "Last ${lines} log lines (${LOGFILE}):"
      tail -n "${lines}" "${LOGFILE}" || true
    fi
  else
    echo "Logfile not found: ${LOGFILE}"
  fi
}

case "${1:-}" in
  start) start ;;
  stop) stop ;;
  restart) stop; sleep 1; start ;;
  status) status "${2:-}" ;;
  *) echo "Usage: $0 {start|stop|restart|status [LINES]}" ; exit 1 ;;
esac
