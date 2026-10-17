#!/usr/bin/env bash
# Hits every API route of a running stack, and checks the dashboard answers too.
#
# What the tester and the demo-day checklist run against `scripts/dev.sh up` to
# prove the stack answers correctly, without opening a browser.
#
#   scripts/smoke.sh [API_URL]   default http://localhost:${API_PORT:-8000}
#
# Plays mrs-k's tea_skip_teabag_pour_twice live session first (the same way the
# demo does) so a fresh stack has a flagged resident, then checks GET /health,
# GET /residents, GET /residents/mrs-k, GET /alerts, GET /alerts/<first id> and
# that the dashboard (DASHBOARD_PORT, default 5173) returns HTML. Prints
# PASS/FAIL per check and exits non-zero if any failed.
# Never sets LIVE_API, never POSTs feedback. POSTs /demo/reset once, last, since
# that one is meant to mutate state (it only answers when OFFLINE_MODE or
# DEMO_RESET is set, which `scripts/dev.sh` and the tester's stack always are).
set -uo pipefail

API_URL="${1:-http://localhost:${API_PORT:-8000}}"
DASHBOARD_URL="http://localhost:${DASHBOARD_PORT:-5173}"

PIPELINE_PYTHON="pipeline/.venv/bin/python3"
if [ ! -x "$PIPELINE_PYTHON" ]; then
  PIPELINE_PYTHON="python3"
fi

CURL_OPTS=(-fsS --max-time 5 --connect-timeout 3)
failures=0

pass() { echo "PASS: $1"; }
fail() {
  echo "FAIL: $1" >&2
  failures=$((failures + 1))
}

get() {
  curl "${CURL_OPTS[@]}" "$1" 2>/dev/null
}

# Runs a python assertion over the parsed JSON $body (as `data`); any further
# args are passed through to python as extra argv entries the expr can read
# via sys.argv[2], sys.argv[3], ... PASSes/FAILs $label accordingly.
check_json() {
  local label="$1" body="$2" expr="$3"
  shift 3
  if python3 -c "
import json, sys
data = json.loads(sys.argv[1])
assert $expr
" "$body" "$@" 2>/dev/null; then
    pass "$label"
  else
    fail "$label: unexpected body $body"
  fi
}

if body=$(get "$API_URL/health"); then
  pass "GET /health -> $body"
else
  fail "GET /health: no response from $API_URL (is 'scripts/dev.sh up' running?)"
fi

demo_room=""
if residents=$(get "$API_URL/residents"); then
  check_json "GET /residents -> non-empty, mrs-k present" "$residents" \
    "isinstance(data, list) and data and any(r.get('id') == 'mrs-k' for r in data)"
  demo_room=$(python3 -c '
import json, sys
data = json.loads(sys.argv[1])
print(data[0]["room"])
' "$residents" 2>/dev/null) || demo_room=""
else
  fail "GET /residents: no response"
fi

if body=$(get "$API_URL/residents/mrs-k"); then
  check_json "GET /residents/mrs-k" "$body" "data.get('id') == 'mrs-k'"
else
  fail "GET /residents/mrs-k: no response"
fi

if body=$(get "$API_URL/handoff"); then
  check_json "GET /handoff" "$body" \
    "data.get('window_hours') == 12 and isinstance(data.get('residents'), list) and data['residents'] and isinstance(data.get('summary'), str) and data['summary']"
else
  fail "GET /handoff: no response"
fi

if status=$(curl "${CURL_OPTS[@]}" -o /dev/null -w '%{http_code}' "$API_URL/handoff?hours=0" 2>/dev/null); then
  fail "GET /handoff?hours=0: expected failure (422), got 2xx"
elif [ "$status" = "422" ]; then
  pass "GET /handoff?hours=0 -> 422"
else
  fail "GET /handoff?hours=0: expected 422, got ${status:-no response}"
fi

ws_url="${API_URL/http/ws}/ws/live?scenario=tea_skip_teabag_pour_twice&speed=1000"
play_live_session() {
  "$PIPELINE_PYTHON" -c '
import asyncio, sys
import websockets

async def main(url):
    async with websockets.connect(url) as ws:
        async for _ in ws:
            pass

asyncio.run(main(sys.argv[1]))
' "$ws_url" 2>/dev/null
}

if play_live_session; then
  pass "live session played"
else
  fail "live session: could not play $ws_url"
fi

first_alert_id=""
if alerts=$(get "$API_URL/alerts"); then
  if first_alert_id=$(python3 -c '
import json, sys
data = json.loads(sys.argv[1])
assert isinstance(data, list), "not a list"
print(data[0]["alert_id"] if data else "")
' "$alerts" 2>/dev/null); then
    pass "GET /alerts -> ${first_alert_id:-(empty list)}"
  else
    fail "GET /alerts: response was not a JSON list of alerts"
  fi
else
  fail "GET /alerts: no response"
fi

alert_body=""
if [ -n "$first_alert_id" ]; then
  if alert_body=$(get "$API_URL/alerts/$first_alert_id"); then
    pass "GET /alerts/$first_alert_id"
  else
    fail "GET /alerts/$first_alert_id: no response"
  fi
else
  fail "GET /alerts/<first id>: no alert id to test (empty /alerts, or /alerts failed)"
fi

if body=$(get "$DASHBOARD_URL"); then
  if printf '%s' "$body" | grep -qi '<html'; then
    pass "GET $DASHBOARD_URL -> HTML"
  else
    fail "GET $DASHBOARD_URL: response did not look like HTML"
  fi
else
  fail "GET $DASHBOARD_URL: no response (is 'scripts/dev.sh up' running?)"
fi

replay_args=""
if [ -n "$first_alert_id" ] && [ -n "$alert_body" ]; then
  replay_args=$(python3 -c '
import json, sys
data = json.loads(sys.argv[1])
errors = data.get("errors") or []
if not errors:
    print("")
else:
    e = errors[0]
    print(data["resident_id"], e["session_id"], e["t_start"], e["t_end"])
' "$alert_body" 2>/dev/null) || replay_args=""
fi

if [ -n "$replay_args" ]; then
  read -r resident_id session_id t_start t_end <<<"$replay_args"

  if body2=$(get "$API_URL/sessions/$session_id/replay?t_start=$t_start&t_end=$t_end"); then
    check_json "GET /sessions/$session_id/replay" "$body2" "data.get('frames')"
  else
    fail "GET /sessions/$session_id/replay: no response"
  fi

  if body3=$(get "$API_URL/residents/$resident_id/normal_replay?t_start=$t_start&t_end=$t_end"); then
    check_json "GET /residents/$resident_id/normal_replay" "$body3" "data.get('frames')"
  else
    fail "GET /residents/$resident_id/normal_replay: no response"
  fi
else
  fail "GET /sessions/<id>/replay and /residents/<id>/normal_replay: no alert error to derive session/resident/time window from"
fi

if body=$(get "$API_URL/monitoring"); then
  check_json "GET /monitoring -> $body" "$body" "isinstance(data.get('paused_rooms'), list)"
else
  fail "GET /monitoring: no response"
fi

if body=$(curl "${CURL_OPTS[@]}" -X PUT -H 'Content-Type: application/json' -d '{"on": false}' "$API_URL/rooms/$demo_room/monitoring" 2>/dev/null); then
  pass "PUT /rooms/$demo_room/monitoring on=false -> $body"
else
  fail "PUT /rooms/$demo_room/monitoring on=false: no response"
fi

if body=$(get "$API_URL/monitoring"); then
  check_json "GET /monitoring shows $demo_room paused" "$body" \
    "sys.argv[2] in (data.get('paused_rooms') or [])" "$demo_room"
else
  fail "GET /monitoring after pause: no response"
fi

if status=$(curl "${CURL_OPTS[@]}" -o /dev/null -w '%{http_code}' -X PUT -H 'Content-Type: application/json' -d '{"on": false}' "$API_URL/rooms/not-a-real-room/monitoring" 2>/dev/null); then
  fail "PUT /rooms/not-a-real-room/monitoring: expected failure (404), got 2xx"
elif [ "$status" = "404" ]; then
  pass "PUT /rooms/not-a-real-room/monitoring -> 404"
else
  fail "PUT /rooms/not-a-real-room/monitoring: expected 404, got ${status:-no response}"
fi

if body=$(curl "${CURL_OPTS[@]}" -X PUT -H 'Content-Type: application/json' -d '{"on": true}' "$API_URL/rooms/$demo_room/monitoring" 2>/dev/null); then
  pass "PUT /rooms/$demo_room/monitoring on=true -> $body"
else
  fail "PUT /rooms/$demo_room/monitoring on=true: no response"
fi

if body=$(get "$API_URL/monitoring"); then
  check_json "GET /monitoring shows $demo_room resumed" "$body" \
    "sys.argv[2] not in (data.get('paused_rooms') or [])" "$demo_room"
else
  fail "GET /monitoring after resume: no response"
fi

# Always resume the demo room, even if a check above failed, so a broken pause
# switch doesn't leave the room paused for whatever runs after this script.
curl "${CURL_OPTS[@]}" -X PUT -H 'Content-Type: application/json' -d '{"on": true}' \
  "$API_URL/rooms/$demo_room/monitoring" >/dev/null 2>&1 || true

if body4=$(curl "${CURL_OPTS[@]}" -X POST "$API_URL/demo/reset" 2>/dev/null); then
  check_json "POST /demo/reset -> $body4" "$body4" "data == {'ok': True}"
else
  fail "POST /demo/reset: no response (needs OFFLINE_MODE=true or DEMO_RESET=1 on the server)"
fi

# Reset only forgets live sessions and feedback (its docstring), not the seeded
# demo history, so playing the same session again must still flag mrs-k and show
# up in /alerts afterwards.
if play_live_session; then
  if alerts_after_reset=$(get "$API_URL/alerts"); then
    check_json "GET /alerts after reset" "$alerts_after_reset" "isinstance(data, list) and len(data) > 0"
  else
    fail "GET /alerts after reset: no response"
  fi
else
  fail "GET /alerts after reset: could not replay $ws_url"
fi

if [ "$failures" -eq 0 ]; then
  echo "smoke: all checks passed"
  exit 0
fi
echo "smoke: $failures check(s) failed" >&2
exit 1
