#!/usr/bin/env bash
# Integration check: does the whole stack actually come up and serve the demo on current main?
# Unit tests and scenarios run in CI; this checks the running system end to end, offline, no keys.
#
#   scripts/integration.sh        exit 0 = healthy; prints one line per failed check
#
# Uses its own ports (API 8100, dashboard 5273) and its own DEV_DIR so it can
# run next to a dev stack without mistaking it for already up, or stopping it.
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"
export API_PORT=${API_PORT:-8100} DASHBOARD_PORT=${DASHBOARD_PORT:-5273} OFFLINE_MODE=true LIVE_API=0
export DEV_DIR=${DEV_DIR:-.dev-integration}
API="http://localhost:$API_PORT"; WEB="http://localhost:$DASHBOARD_PORT"
fails=()
fail() { fails+=("$1"); }
demo_room=""

# Searching a captured page/DOM is a plain string match, never
# `echo "$dom" | grep -q X`: with `set -o pipefail` grep -q exits at its first
# match, echo then dies of SIGPIPE, and the pipeline reports 141 even though the
# text was right there. That is how the dashboard render check below failed on
# about half of its runs while the dashboard was fine (T367).
contains() {
  case "$1" in *"$2"*) return 0 ;; *) return 1 ;; esac
}

# contains(), case-insensitive, over several needles.
contains_any_ci() {
  local haystack=${1,,} phrase
  shift
  for phrase in "$@"; do
    contains "$haystack" "${phrase,,}" && return 0
  done
  return 1
}

# Resume the demo room no matter how the script exits (success, a failed check,
# or dev.sh up itself failing before demo_room is even known) so a broken pause
# switch never leaves the room paused for whatever runs after this script.
trap 'curl -fsS --max-time 5 -X PUT -H "Content-Type: application/json" -d "{\"on\": true}" "$API/rooms/$demo_room/monitoring" >/dev/null 2>&1 || true; scripts/dev.sh down >/dev/null 2>&1' EXIT
if ! scripts/dev.sh up >/tmp/integration-up.log 2>&1; then
  echo "FAIL dev.sh up: $(tail -3 /tmp/integration-up.log | tr '\n' ' ')"
  echo "  api log: $(tail -5 "$DEV_DIR/api.log" 2>/dev/null | tr '\n' ' ')"
  exit 1
fi

json() { curl -fsS --max-time 10 "$API$1" 2>/dev/null; }
json /health >/dev/null || fail "GET /health"
n=$(json /residents | python3 -c 'import sys,json;d=json.load(sys.stdin);print(len(d if isinstance(d,list) else d.get("residents",[])))' 2>/dev/null)
[ "${n:-0}" -ge 1 ] || fail "GET /residents returned no residents"
rid=$(json /residents | python3 -c 'import sys,json;d=json.load(sys.stdin);d=d if isinstance(d,list) else d.get("residents",[]);print(d[0].get("id") or d[0].get("resident_id"))' 2>/dev/null)
[ -n "$rid" ] && { json "/residents/$rid" >/dev/null || fail "GET /residents/$rid"; }
demo_room=$(json /residents | python3 -c 'import sys,json;d=json.load(sys.stdin);d=d if isinstance(d,list) else d.get("residents",[]);print(d[0].get("room",""))' 2>/dev/null)
json /alerts >/dev/null || fail "GET /alerts"
index=$(curl -fsS --max-time 10 "$WEB/" 2>/dev/null) || index=""
contains "$index" '<div id="root"' || fail "dashboard index.html"

# dev.sh waits for index.html, which Vite serves before it has transformed a
# single module. Ask for the entry module too (web/index.html's script src): a
# cold Vite optimises deps while answering that first request and then tells the
# page to reload, which would otherwise land in the middle of the DOM dump
# below. Not a check - if this path ever moves, the checks still speak.
curl -fsS --max-time 60 -o /dev/null "$WEB/src/main.tsx" || true

# Live session WebSocket: at least one message within 10 s.
(cd pipeline && timeout 20 uv run python - "$API_PORT" <<'PY') || fail "WebSocket /ws/live sent nothing"
import asyncio, sys
async def main():
    try:
        import websockets
    except ImportError:
        print("skip ws check: websockets not installed")
        return
    async with websockets.connect(f"ws://localhost:{sys.argv[1]}/ws/live?scenario=tea_skip_teabag_pour_twice&speed=20", open_timeout=10) as ws:
        await asyncio.wait_for(ws.recv(), 10)
asyncio.run(main())
PY

# Pause/resume via the room monitoring switch (T244/T249/T266/T275): pausing the
# demo resident's room must make /ws/live send "paused" as its first message
# instead of starting a session, and resuming must let a fresh connection stream
# normally again.
ws_first_message_type() {
  (cd pipeline && timeout 20 uv run python - "$API_PORT" <<'PY'
import asyncio, json, sys
async def main():
    try:
        import websockets
    except ImportError:
        print("SKIP")
        return
    url = f"ws://localhost:{sys.argv[1]}/ws/live?scenario=tea_skip_teabag_pour_twice&speed=20"
    async with websockets.connect(url, open_timeout=10) as ws:
        msg = await asyncio.wait_for(ws.recv(), 10)
        print(json.loads(msg).get("type", ""))
asyncio.run(main())
PY
  ) 2>/dev/null
}

if [ -n "$demo_room" ]; then
  curl -fsS --max-time 10 -X PUT -H 'Content-Type: application/json' -d '{"on": false}' \
    "$API/rooms/$demo_room/monitoring" >/dev/null || fail "PUT /rooms/$demo_room/monitoring on=false"

  paused_type=$(ws_first_message_type)
  if [ "$paused_type" != "SKIP" ] && [ "$paused_type" != "paused" ]; then
    fail "paused room: /ws/live's first message was not 'paused' (got: ${paused_type:-none})"
  fi

  curl -fsS --max-time 10 -X PUT -H 'Content-Type: application/json' -d '{"on": true}' \
    "$API/rooms/$demo_room/monitoring" >/dev/null || fail "PUT /rooms/$demo_room/monitoring on=true"

  resumed_type=$(ws_first_message_type)
  if [ "$resumed_type" != "SKIP" ] && { [ -z "$resumed_type" ] || [ "$resumed_type" = "paused" ]; }; then
    fail "resumed room: fresh /ws/live connection did not stream a normal message (got: ${resumed_type:-none})"
  fi
else
  fail "could not determine demo room from GET /residents"
fi

# Rendered dashboard (needs a headless Chrome; skipped if none).
CHROME=${CHROME:-$(ls ~/.cache/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell 2>/dev/null | head -1)}
if [ -n "$CHROME" ]; then
  dom=""
  for attempt in 1 2 3; do
    dom=$("$CHROME" --no-sandbox --headless --virtual-time-budget=8000 --dump-dom "$WEB/" 2>/dev/null)
    contains "$dom" "Routine Watch" && break
    [ "$attempt" -lt 3 ] && sleep 3
  done
  contains "$dom" "Routine Watch" ||
    fail "dashboard did not render (no 'Routine Watch' in ${#dom} bytes of DOM; see $DEV_DIR/web.log)"
  contains_any_ci "$dom" "something went wrong" "uncaught" "cannot read prop" &&
    fail "dashboard rendered an error"
fi

if [ ${#fails[@]} -gt 0 ]; then
  printf 'FAIL %s\n' "${fails[@]}"
  exit 1
fi
echo "OK integration (api + dashboard + live ws)"
