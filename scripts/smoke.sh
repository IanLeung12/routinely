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

if body=$(get "$API_URL/health"); then
  pass "GET /health -> $body"
else
  fail "GET /health: no response from $API_URL (is 'scripts/dev.sh up' running?)"
fi

if residents=$(get "$API_URL/residents"); then
  if python3 -c '
import json, sys
data = json.loads(sys.argv[1])
assert isinstance(data, list) and data, "empty list"
assert any(r.get("id") == "mrs-k" for r in data), "mrs-k not found"
' "$residents" 2>/dev/null; then
    pass "GET /residents -> non-empty, mrs-k present"
  else
    fail "GET /residents: response was not a non-empty list containing mrs-k"
  fi
else
  fail "GET /residents: no response"
fi

if body=$(get "$API_URL/residents/mrs-k"); then
  if python3 -c '
import json, sys
data = json.loads(sys.argv[1])
assert data.get("id") == "mrs-k"
' "$body" 2>/dev/null; then
    pass "GET /residents/mrs-k"
  else
    fail "GET /residents/mrs-k: unexpected body"
  fi
else
  fail "GET /residents/mrs-k: no response"
fi

if body=$(get "$API_URL/handoff"); then
  if python3 -c '
import json, sys
data = json.loads(sys.argv[1])
assert data.get("window_hours") == 12, "window_hours not 12"
assert isinstance(data.get("residents"), list) and data["residents"], "empty residents"
assert isinstance(data.get("summary"), str) and data["summary"], "empty summary"
' "$body" 2>/dev/null; then
    pass "GET /handoff"
  else
    fail "GET /handoff: unexpected body $body"
  fi
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
if "$PIPELINE_PYTHON" -c '
import asyncio, sys
import websockets

async def main(url):
    async with websockets.connect(url) as ws:
        async for _ in ws:
            pass

asyncio.run(main(sys.argv[1]))
' "$ws_url" 2>/dev/null; then
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
    if python3 -c '
import json, sys
data = json.loads(sys.argv[1])
assert data.get("frames"), "empty frames"
' "$body2" 2>/dev/null; then
      pass "GET /sessions/$session_id/replay"
    else
      fail "GET /sessions/$session_id/replay: no frames in response"
    fi
  else
    fail "GET /sessions/$session_id/replay: no response"
  fi

  if body3=$(get "$API_URL/residents/$resident_id/normal_replay?t_start=$t_start&t_end=$t_end"); then
    if python3 -c '
import json, sys
data = json.loads(sys.argv[1])
assert data.get("frames"), "empty frames"
' "$body3" 2>/dev/null; then
      pass "GET /residents/$resident_id/normal_replay"
    else
      fail "GET /residents/$resident_id/normal_replay: no frames in response"
    fi
  else
    fail "GET /residents/$resident_id/normal_replay: no response"
  fi
else
  fail "GET /sessions/<id>/replay and /residents/<id>/normal_replay: no alert error to derive session/resident/time window from"
fi

if body4=$(curl "${CURL_OPTS[@]}" -X POST "$API_URL/demo/reset" 2>/dev/null); then
  if python3 -c '
import json, sys
data = json.loads(sys.argv[1])
assert data == {"ok": True}
' "$body4" 2>/dev/null; then
    pass "POST /demo/reset -> $body4"
  else
    fail "POST /demo/reset: unexpected body $body4"
  fi
else
  fail "POST /demo/reset: no response (needs OFFLINE_MODE=true or DEMO_RESET=1 on the server)"
fi

if [ "$failures" -eq 0 ]; then
  echo "smoke: all checks passed"
  exit 0
fi
echo "smoke: $failures check(s) failed" >&2
exit 1
