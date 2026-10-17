#!/usr/bin/env bash
# End-to-end deployment check; requires a Docker host, uv, Python and curl.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
export OFFLINE_MODE=true LIVE_API=0 CORS_ORIGINS=http://localhost:5173
export VITE_API_URL=http://localhost:8000
test_env=$(mktemp)
trap 'rm -f "$test_env"' EXIT
printf 'OFFLINE_MODE=true\nLIVE_API=0\n' > "$test_env"
# Override env_file too: tests must not inherit real provider keys from .env.
test_override=$(mktemp --suffix=.yml)
printf 'services:\n  api:\n    env_file: !override ["%s"]\n' "$test_env" > "$test_override"
compose=(docker compose --env-file "$test_env" -p routine-watch-deploy-test
  -f deploy/docker-compose.yml -f "$test_override")
cleanup() {
  local status=$?
  "${compose[@]}" down -v || status=$?
  rm -f "$test_env" "$test_override"
  return "$status"
}
trap cleanup EXIT
(cd pipeline && uv sync --frozen --extra dev --no-extra capture)
"${compose[@]}" up -d --build --wait
echo '== non-root API and no embedded environment file'
"${compose[@]}" exec -T api python -c '
import os
from pathlib import Path
assert os.getuid() != 0
assert not list(Path("/app").rglob(".env"))
assert Path("/app/.data/replays").is_dir()
Path("/app/.data/replays/write-check").write_text("skeleton-only")
'
echo '== CORS and nginx routing'
curl -fsS -D - -o /dev/null -H 'Origin: http://localhost:5173' \
  http://localhost:8000/health | tr -d '\r' | grep -i '^access-control-allow-origin: http://localhost:5173$'
index=$(curl -fsS http://localhost:5173/)
fallback=$(curl -fsS http://localhost:5173/residents/mrs-k)
test "$index" = "$fallback"
test "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:5173/assets/missing.js)" = 404
echo '== full API/dashboard smoke'
DASHBOARD_PORT=5173 bash scripts/smoke.sh http://localhost:8000
echo 'deploy: all checks passed'
