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
# GET /residents, GET /residents/mrs-k, GET /residents/mrs-k/feedback,
# GET /alerts, GET /alerts/<first id>, GET /people/<first person>/replays,
# GET /routines, GET /routines/<first id>, POST /routines/draft (from a
# sentence; SKIPped if the stack has no drafter), GET /monitoring,
# GET /rooms/<demo room>/monitoring/history and that the dashboard
# (DASHBOARD_PORT, default 5173) returns HTML, and that its public landing
# page at /landing.html also returns HTML containing "Routine Watch" and
# differs from the dashboard's own response (Vite's dev server falls back to
# index.html for any unknown path, so a landing page missing from the build
# would otherwise still answer 200 with HTML). Also validates the
# residents/resident/feedback/handoff/alert-detail/monitoring/room-history
# bodies against their schemas in `contracts/`, and the first message of a
# fresh `/ws/live` session against `contracts/live_message.schema.json` (SKIP, not
# FAIL, if jsonschema or websockets isn't importable). Prints PASS/FAIL per
# check and exits non-zero if any failed.
# Never sets LIVE_API, never POSTs feedback. Drafting a routine keeps nothing (only
# POST /routines does, and this never calls it). POSTs /demo/reset once, last, since
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

# Validates $body against the JSON Schema at $schema_file (one of
# contracts/*.schema.json) using jsonschema from the pipeline venv. Validates
# every element if $body is a JSON list (e.g. GET /residents' rows), the whole
# body otherwise. Prints SKIP instead of FAIL if jsonschema isn't importable,
# since the running stack catching contract drift is the point, not pinning
# down which Python has the dev dependency.
check_schema() {
  local label="$1" body="$2" schema_file="$3"
  local out status
  out=$("$PIPELINE_PYTHON" -c "
import json, sys
try:
    from jsonschema import Draft202012Validator
except ImportError:
    sys.exit(2)
schema = json.load(open(sys.argv[2]))
data = json.loads(sys.argv[1])
validator = Draft202012Validator(schema)
for item in (data if isinstance(data, list) else [data]):
    validator.validate(item)
" "$body" "$schema_file" 2>&1)
  status=$?
  if [ "$status" -eq 0 ]; then
    pass "$label"
  elif [ "$status" -eq 2 ]; then
    echo "SKIP: $label (jsonschema not importable)"
  else
    fail "$label: $out"
  fi
}

# Connects to $ws_url, reads just the first message (a fresh connection's is
# always session_start) with a 5s timeout, and validates it against
# $schema_file. SKIPs instead of FAILing if websockets or jsonschema isn't
# importable from the pipeline venv.
check_live_message_schema() {
  local label="$1" ws_url="$2" schema_file="$3"
  local out status
  out=$("$PIPELINE_PYTHON" -c "
import asyncio, json, sys
try:
    import websockets
except ImportError:
    sys.exit(2)
try:
    from jsonschema import Draft202012Validator
except ImportError:
    sys.exit(2)

async def first_message(url):
    async with websockets.connect(url, open_timeout=5, close_timeout=5) as ws:
        return await asyncio.wait_for(ws.recv(), timeout=5)

message = asyncio.run(first_message(sys.argv[1]))
schema = json.load(open(sys.argv[2]))
Draft202012Validator(schema).validate(json.loads(message))
" "$ws_url" "$schema_file" 2>&1)
  status=$?
  if [ "$status" -eq 0 ]; then
    pass "$label"
  elif [ "$status" -eq 2 ]; then
    echo "SKIP: $label (websockets or jsonschema not importable)"
  else
    fail "$label: $out"
  fi
}

if body=$(get "$API_URL/health"); then
  pass "GET /health -> $body"
else
  fail "GET /health: no response from $API_URL (is 'scripts/dev.sh up' running?)"
fi

demo_room=""
demo_person=""
if residents=$(get "$API_URL/residents"); then
  check_json "GET /residents -> non-empty, mrs-k present" "$residents" \
    "isinstance(data, list) and data and any(r.get('id') == 'mrs-k' for r in data)"
  check_schema "GET /residents rows match schema" "$residents" "contracts/resident_summary.schema.json"
  demo_room=$(python3 -c '
import json, sys
data = json.loads(sys.argv[1])
print(data[0]["room"])
' "$residents" 2>/dev/null) || demo_room=""
  demo_person=$(python3 -c '
import json, sys
data = json.loads(sys.argv[1])
print(data[0]["id"])
' "$residents" 2>/dev/null) || demo_person=""
else
  fail "GET /residents: no response"
fi

if body=$(get "$API_URL/residents/mrs-k"); then
  check_json "GET /residents/mrs-k" "$body" "data.get('id') == 'mrs-k'"
  check_schema "GET /residents/mrs-k matches schema" "$body" "contracts/resident.schema.json"
else
  fail "GET /residents/mrs-k: no response"
fi

# What nurses said about this resident (SPEC Nice to have 8). Smoke never POSTs
# feedback, so on a fresh stack this is the empty record - which is a real answer
# and still has to validate, fields and all.
if body=$(get "$API_URL/residents/mrs-k/feedback"); then
  check_json "GET /residents/mrs-k/feedback" "$body" \
    "data.get('resident_id') == 'mrs-k' and isinstance(data.get('answers'), list) and isinstance(data.get('pattern_weights'), dict) and isinstance(data.get('pattern_names'), dict)"
  check_schema "GET /residents/mrs-k/feedback matches schema" "$body" "contracts/resident_feedback.schema.json"
else
  fail "GET /residents/mrs-k/feedback: no response"
fi

if body=$(get "$API_URL/handoff"); then
  check_json "GET /handoff" "$body" \
    "data.get('window_hours') == 12 and isinstance(data.get('residents'), list) and data['residents'] and isinstance(data.get('summary'), str) and data['summary']"
  check_schema "GET /handoff matches schema" "$body" "contracts/handoff.schema.json"
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
    check_schema "GET /alerts/$first_alert_id matches schema" "$alert_body" "contracts/alert_detail.schema.json"
  else
    fail "GET /alerts/$first_alert_id: no response"
  fi
else
  fail "GET /alerts/<first id>: no alert id to test (empty /alerts, or /alerts failed)"
fi

dashboard_body=""
if body=$(get "$DASHBOARD_URL"); then
  if printf '%s' "$body" | grep -qi '<html'; then
    pass "GET $DASHBOARD_URL -> HTML"
  else
    fail "GET $DASHBOARD_URL: response did not look like HTML"
  fi
  dashboard_body="$body"
else
  fail "GET $DASHBOARD_URL: no response (is 'scripts/dev.sh up' running?)"
fi

# Vite's dev server falls back to serving index.html for any unknown path, so
# a landing page that's gone missing from the build still answers 200 with
# HTML; compare against $dashboard_body (the dashboard's own response, above)
# to tell a real landing page apart from that fallback.
if body=$(get "$DASHBOARD_URL/landing.html"); then
  if printf '%s' "$body" | grep -qi '<html' && printf '%s' "$body" | grep -q 'Routine Watch' \
    && [ "$body" != "$dashboard_body" ]; then
    pass "GET $DASHBOARD_URL/landing.html -> HTML"
  else
    fail "GET $DASHBOARD_URL/landing.html: response did not look like the landing page"
  fi
else
  fail "GET $DASHBOARD_URL/landing.html: no response (is 'scripts/dev.sh up' running?)"
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

# This person's own kept replays (SPEC section 17), which the replays screen opens
# with. A demo person's library is generated the first time it is asked for, so a
# fresh stack has rows in it - but an empty library is a real answer too (somebody
# who has never gone wrong has one), so this holds the shape, not the count.
if [ -n "$demo_person" ]; then
  if body=$(get "$API_URL/people/$demo_person/replays"); then
    check_json "GET /people/$demo_person/replays" "$body" \
      "isinstance(data, dict) and data.get('person_id') == sys.argv[2] and isinstance(data.get('replays'), list)" \
      "$demo_person"
  else
    fail "GET /people/$demo_person/replays: no response"
  fi
else
  echo "SKIP: GET /people/<person id>/replays (no person id from /residents)"
fi

# The routine builder's library (SPEC section 12). The built-in routines ship as
# data (`tasks/*.yaml`), so this is never empty on a stack that can read them.
first_routine_id=""
if routines=$(get "$API_URL/routines"); then
  check_json "GET /routines -> non-empty, every row has an id and a title" "$routines" \
    "isinstance(data, list) and data and all(r.get('id') and r.get('title') for r in data)"
  first_routine_id=$(python3 -c '
import json, sys
data = json.loads(sys.argv[1])
print(data[0]["id"])
' "$routines" 2>/dev/null) || first_routine_id=""
else
  fail "GET /routines: no response"
fi

if [ -n "$first_routine_id" ]; then
  if body=$(get "$API_URL/routines/$first_routine_id"); then
    check_json "GET /routines/$first_routine_id -> has a task graph" "$body" \
      "isinstance(data.get('task_graph'), dict) and data['task_graph'].get('steps')"
  else
    fail "GET /routines/$first_routine_id: no response"
  fi
else
  fail "GET /routines/<first id>: no routine id to test (empty /routines, or /routines failed)"
fi

# Drafting a routine from a sentence. Offline the drafter is the canned one, so
# this costs nothing and reaches no model; smoke never sets LIVE_API. Read without
# curl's -f so the status code comes back instead of an error: a stack built
# without a drafter route at all answers 501/503, which is a SKIP rather than a
# failure, and anything else is worth seeing the body of.
draft_answer=$(curl -sS --max-time 10 --connect-timeout 3 -w '\n%{http_code}' -X POST \
  -F 'description=Make a cup of tea: fill the kettle, put a teabag in the cup, then pour' \
  "$API_URL/routines/draft" 2>/dev/null)
draft_status="${draft_answer##*$'\n'}"
draft_body="${draft_answer%$'\n'*}"
case "$draft_status" in
  200)
    check_json "POST /routines/draft -> task graph" "$draft_body" \
      "isinstance(data.get('draft'), dict) and isinstance(data.get('task_graph'), dict) and data['task_graph'].get('steps')"
    ;;
  501 | 503)
    echo "SKIP: POST /routines/draft (this stack has no drafter: HTTP $draft_status)"
    ;;
  '' | 000)
    fail "POST /routines/draft: no response"
    ;;
  *)
    fail "POST /routines/draft: expected 200, got $draft_status${draft_body:+ -> $draft_body}"
    ;;
esac

if body=$(get "$API_URL/monitoring"); then
  check_json "GET /monitoring -> $body" "$body" "isinstance(data.get('paused_rooms'), list)"
  check_schema "GET /monitoring matches schema" "$body" "contracts/monitoring.schema.json"
else
  fail "GET /monitoring: no response"
fi

if [ -n "$demo_room" ]; then
  if body=$(get "$API_URL/rooms/$demo_room/monitoring/history"); then
    check_json "GET /rooms/$demo_room/monitoring/history" "$body" "data.get('room') == sys.argv[2]" "$demo_room"
    check_schema "GET /rooms/$demo_room/monitoring/history matches schema" "$body" "contracts/room_monitoring_history.schema.json"
  else
    fail "GET /rooms/$demo_room/monitoring/history: no response"
  fi
else
  echo "SKIP: GET /rooms/<room>/monitoring/history (no demo_room)"
fi

live_message_ws_url="${API_URL/http/ws}/ws/live?scenario=tea_skip_teabag_pour_twice&speed=20"
check_live_message_schema "first /ws/live message matches schema" "$live_message_ws_url" "contracts/live_message.schema.json"

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
