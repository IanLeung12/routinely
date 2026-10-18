#!/usr/bin/env bash
# One command to bring the local stack (API + dashboard) up and down.
# Used by humans and the tester; works with no API keys.
#
#   scripts/dev.sh up       start API + dashboard in the background, wait until
#                           healthy, print DASHBOARD_URL=... and API_URL=...
#   scripts/dev.sh down     stop both, free their ports
#   scripts/dev.sh status   show whether each is running
#
# Ports: API_PORT (default 8000), DASHBOARD_PORT (default 5173).
# LAN=1 scripts/dev.sh up   also serve other devices on the same Wi-Fi (prints LAN_DASHBOARD_URL).
# Logs: .dev/api.log, .dev/web.log. PIDs: .dev/api.pid, .dev/web.pid.
# Set DEV_DIR to use a different pid/log directory, e.g. to run a second,
# independent stack (on different ports) without it mistaking the default
# stack's pid files for its own, or stopping them on `down`.
#
# DASHBOARD_MODE=dev (default) runs the Vite dev server, which optimises
# dependencies lazily on first request - fine for humans iterating, but a
# render check right after `up` can race a cold optimisation pass.
# DASHBOARD_MODE=preview builds the dashboard once and serves the static
# `dist/` via `vite preview` instead, so there is nothing left to warm up.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
REPO_ROOT="$(pwd)"

API_PORT=${API_PORT:-8000}
DASHBOARD_PORT=${DASHBOARD_PORT:-5173}
API_URL="http://localhost:${API_PORT}"
DASHBOARD_URL="http://localhost:${DASHBOARD_PORT}"
DASHBOARD_MODE=${DASHBOARD_MODE:-dev}
# LAN=1: also serve to phones/laptops on the same Wi-Fi. The dashboard binds 0.0.0.0
# and calls the API at this machine's LAN address. The camera preview stays
# 127.0.0.1-only by design (SPEC section 12): other devices get skeleton only.
LAN=${LAN:-0}
VITE_HOST_ARGS=()
if [ "$LAN" = 1 ]; then
  LAN_IP=${LAN_IP:-$(python3 -c "import socket;s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.connect(('10.255.255.255',1));print(s.getsockname()[0])" 2>/dev/null || echo 127.0.0.1)}
  VITE_HOST_ARGS=(--host 0.0.0.0)
  export VITE_API_URL=${VITE_API_URL:-http://$LAN_IP:$API_PORT}
  export CORS_ORIGINS=${CORS_ORIGINS:-$DASHBOARD_URL,http://127.0.0.1:${DASHBOARD_PORT},http://$LAN_IP:${DASHBOARD_PORT}}
fi

DEV_DIR=${DEV_DIR:-.dev}
API_PID_FILE="$DEV_DIR/api.pid"
WEB_PID_FILE="$DEV_DIR/web.pid"
API_LOG="$DEV_DIR/api.log"
WEB_LOG="$DEV_DIR/web.log"
# Outside web/ and namespaced by DEV_DIR so two stacks (e.g. a human's dev
# server and the integration check) never race on the same build output.
WEB_DIST_DIR="$REPO_ROOT/$DEV_DIR/web-dist"

# No API keys needed: OFFLINE_MODE defaults on so the pipeline uses mock data.
export OFFLINE_MODE=${OFFLINE_MODE:-true}
export LIVE_API=${LIVE_API:-0}
export VITE_API_URL=${VITE_API_URL:-$API_URL}
export CORS_ORIGINS=${CORS_ORIGINS:-$DASHBOARD_URL,http://127.0.0.1:${DASHBOARD_PORT}}

mkdir -p "$DEV_DIR"

is_running() {
  [ -f "$1" ] && kill -0 "$(cat "$1")" 2>/dev/null
}

wait_for() {
  local url="$1" label="$2"
  for _ in $(seq 1 60); do
    curl -fsS -o /dev/null "$url" 2>/dev/null && return 0
    sleep 1
  done
  echo "timed out waiting for $label at $url" >&2
  return 1
}

start_api() {
  if is_running "$API_PID_FILE"; then
    echo "API already running (pid $(cat "$API_PID_FILE"))"
    return
  fi
  command -v uv >/dev/null || python3 -m pip install -q uv
  : >"$API_LOG"
  (cd pipeline && uv sync -q --all-extras) >>"$API_LOG" 2>&1
  (
    cd pipeline
    exec uv run uvicorn routine_watch.api:app --host 0.0.0.0 --port "$API_PORT"
  ) >>"$API_LOG" 2>&1 &
  echo $! >"$API_PID_FILE"
}

start_web() {
  if is_running "$WEB_PID_FILE"; then
    echo "dashboard already running (pid $(cat "$WEB_PID_FILE"))"
    return
  fi
  : >"$WEB_LOG"
  if [ ! -d web/node_modules ]; then
    (cd web && npm ci --no-audit --no-fund) >>"$WEB_LOG" 2>&1
  fi
  if [ "$DASHBOARD_MODE" = "preview" ]; then
    (cd web && node_modules/.bin/tsc -b && node_modules/.bin/vite build --outDir "$WEB_DIST_DIR" --emptyOutDir) >>"$WEB_LOG" 2>&1
    (
      cd web
      # Run vite directly (not via `npm run`) so this PID is the actual port listener.
      exec node_modules/.bin/vite preview ${VITE_HOST_ARGS[@]+"${VITE_HOST_ARGS[@]}"} --port "$DASHBOARD_PORT" --strictPort --outDir "$WEB_DIST_DIR"
    ) >>"$WEB_LOG" 2>&1 &
  else
    (
      cd web
      # Run vite directly (not via `npm run`) so this PID is the actual port listener.
      exec node_modules/.bin/vite ${VITE_HOST_ARGS[@]+"${VITE_HOST_ARGS[@]}"} --port "$DASHBOARD_PORT" --strictPort
    ) >>"$WEB_LOG" 2>&1 &
  fi
  echo $! >"$WEB_PID_FILE"
}

stop_proc() {
  local pid_file="$1"
  [ -f "$pid_file" ] || return 0
  local pid
  pid=$(cat "$pid_file")
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    for _ in $(seq 1 10); do
      kill -0 "$pid" 2>/dev/null || break
      sleep 0.5
    done
    kill -9 "$pid" 2>/dev/null || true
  fi
  rm -f "$pid_file"
}

free_port() {
  local port="$1"
  local pids
  pids=$(lsof -ti "tcp:$port" 2>/dev/null || true)
  [ -n "$pids" ] || return 0
  kill $pids 2>/dev/null || true
  sleep 1
  pids=$(lsof -ti "tcp:$port" 2>/dev/null || true)
  [ -n "$pids" ] || return 0
  kill -9 $pids 2>/dev/null || true
}

cmd_up() {
  start_api
  start_web
  wait_for "$API_URL/health" "API"
  wait_for "$DASHBOARD_URL" "dashboard"
  echo "DASHBOARD_URL=$DASHBOARD_URL"
  echo "API_URL=$API_URL"
  if [ "$LAN" = 1 ]; then
    echo "LAN_DASHBOARD_URL=http://$LAN_IP:$DASHBOARD_PORT   (open on a phone/laptop on the same Wi-Fi)"
  fi
}

cmd_down() {
  stop_proc "$API_PID_FILE"
  stop_proc "$WEB_PID_FILE"
  free_port "$API_PORT"
  free_port "$DASHBOARD_PORT"
  echo "stopped"
}

cmd_status() {
  if is_running "$API_PID_FILE"; then
    echo "API: up ($API_URL, pid $(cat "$API_PID_FILE"))"
  else
    echo "API: down"
  fi
  if is_running "$WEB_PID_FILE"; then
    echo "dashboard: up ($DASHBOARD_URL, pid $(cat "$WEB_PID_FILE"))"
  else
    echo "dashboard: down"
  fi
}

case "${1:-}" in
  up) cmd_up ;;
  down) cmd_down ;;
  status) cmd_status ;;
  *)
    echo "usage: $0 {up|down|status}" >&2
    exit 1
    ;;
esac
