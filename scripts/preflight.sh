#!/usr/bin/env bash
# One command that says "ready to demo" (SPEC §10 fallback, §13 risks).
#
# Runs the checks a human would otherwise run by hand, in order, and prints a
# ✓/✗ line per step. Stops at the first ✗ with a one-line fix hint, so nobody
# has to remember or re-run the rest to find the real problem. Never calls a
# paid API: it refuses outright if LIVE_API=1.
#
#   scripts/preflight.sh            run every check for real
#   scripts/preflight.sh --dry-run  list every step without running any of
#                                    them (still refuses if LIVE_API=1)
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"

DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

API_PORT=${API_PORT:-8000}
DASHBOARD_PORT=${DASHBOARD_PORT:-5173}
API_URL="http://localhost:${API_PORT}"
DEMO_RESIDENT=mrs-k

STEP_NAMES=(
  "LIVE_API unset and OFFLINE_MODE=true"
  "scripts/dev.sh up"
  "scripts/smoke.sh"
  "scripts/e2e.sh"
  "POST /demo/reset; GET /residents shows $DEMO_RESIDENT on watch"
)

ok() { echo "✓ $1"; }
bad() {
  echo "✗ $1" >&2
  echo "  fix: $2" >&2
  exit 1
}

check_live_api() {
  if [ "${LIVE_API:-0}" = "1" ]; then
    bad "${STEP_NAMES[0]}" \
      "unset LIVE_API (or set it to 0); preflight never calls a paid API"
  fi
  export OFFLINE_MODE=${OFFLINE_MODE:-true}
  export LIVE_API=0
  ok "${STEP_NAMES[0]}"
}

if [ "$DRY_RUN" -eq 1 ]; then
  check_live_api
  for name in "${STEP_NAMES[@]:1}"; do
    echo "- $name"
  done
  exit 0
fi

check_live_api

if scripts/dev.sh up >/tmp/preflight-dev-up.log 2>&1; then
  ok "${STEP_NAMES[1]}"
else
  bad "${STEP_NAMES[1]}" \
    "check .dev/api.log and .dev/web.log; last lines: $(tail -3 /tmp/preflight-dev-up.log | tr '\n' ' ')"
fi

if smoke_out=$(scripts/smoke.sh "$API_URL" 2>&1); then
  ok "${STEP_NAMES[2]}"
else
  bad "${STEP_NAMES[2]}" \
    "run scripts/smoke.sh directly for the full output; last line: $(printf '%s\n' "$smoke_out" | tail -1)"
fi

if e2e_out=$(scripts/e2e.sh 2>&1); then
  summary=$(printf '%s\n' "$e2e_out" | grep -E '^[0-9]+/[0-9]+ scenarios passed$' | tail -1)
  ok "${STEP_NAMES[3]} (${summary:-ran})"
else
  bad "${STEP_NAMES[3]}" \
    "run scripts/e2e.sh directly for the full diff; last line: $(printf '%s\n' "$e2e_out" | tail -1)"
fi

if ! curl -fsS --max-time 5 -X POST "$API_URL/demo/reset" >/tmp/preflight-reset.log 2>&1; then
  bad "${STEP_NAMES[4]}" \
    "POST $API_URL/demo/reset failed; the running API needs OFFLINE_MODE=true or DEMO_RESET=1"
fi

if ! residents=$(curl -fsS --max-time 5 "$API_URL/residents" 2>/dev/null); then
  bad "${STEP_NAMES[4]}" "GET $API_URL/residents failed; is scripts/dev.sh up running?"
fi

if python3 -c "
import json, sys
data = json.loads(sys.argv[1])
assert any(r.get('id') == sys.argv[2] and r.get('status') == 'watch' for r in data)
" "$residents" "$DEMO_RESIDENT" 2>/dev/null; then
  ok "${STEP_NAMES[4]}"
else
  bad "${STEP_NAMES[4]}" \
    "GET $API_URL/residents did not show $DEMO_RESIDENT on watch; body: $residents"
fi

echo "ready to demo"
