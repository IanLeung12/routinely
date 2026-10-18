#!/usr/bin/env bash
# Single CI entrypoint, used by GitHub Actions and by agents locally.
# Runs whatever exists; tasks extend this as the stack lands.
#
#   scripts/ci.sh              everything (what GitHub runs, split into parallel jobs)
#   scripts/ci.sh --changed    only the parts your branch touches vs origin/main, no e2e:
#                              the fast local check for workers; PR CI still runs it all
#   CI_PARTS="python web" scripts/ci.sh   pick parts: tooling python web e2e
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
export LIVE_API=0

PARTS=${CI_PARTS:-tooling python web e2e}
if [ "${1:-}" = --changed ]; then
  git fetch -q origin main 2>/dev/null || true
  CHANGED=$( { git diff --name-only origin/main...HEAD; git diff --name-only HEAD; git ls-files --others --exclude-standard; } 2>/dev/null | sort -u)
  PARTS=""
  grep -qE '^(scripts/|tests/)' <<<"$CHANGED" && PARTS="$PARTS tooling"
  grep -qE '^pipeline/' <<<"$CHANGED" && PARTS="$PARTS python"
  grep -qE '^web/' <<<"$CHANGED" && PARTS="$PARTS web"
  # contracts are shared: a change on either side checks both
  grep -qE 'contracts\.(py|ts)$' <<<"$CHANGED" && PARTS="$PARTS python web"
  [ -z "$PARTS" ] && { echo "ci --changed: nothing testable changed"; echo "CI OK"; exit 0; }
  echo "ci --changed: running$PARTS (PR CI runs everything, including e2e)"
fi
want() { case " $PARTS " in *" $1 "*) return 0;; *) return 1;; esac; }

if want tooling; then
echo "== repo tooling"
python3 -m py_compile scripts/tasks.py scripts/codemap.py scripts/mergeq.py scripts/metrics.py
bash -n scripts/integration.sh
python3 scripts/codemap.py >/dev/null
bash -n scripts/worker.sh
bash -n scripts/camera.sh
bash -n scripts/e2e.sh
bash -n scripts/smoke.sh
bash -n scripts/preflight.sh

echo "== repo tooling: tests/"
command -v uv >/dev/null || python3 -m pip install -q uv
uv run --with pytest --no-project python -m pytest -q tests
fi

if want python; then
for proj in $(find . -maxdepth 2 -name pyproject.toml -not -path "./.tasks/*"); do
  d=$(dirname "$proj"); echo "== python: $d"
  command -v uv >/dev/null || python3 -m pip install -q uv
  # --no-extra capture: mediapipe/opencv are only needed with a camera or a video
  # file, and nothing in CI has either. Capture imports them lazily (T039).
  (cd "$d" && uv sync -q --all-extras --no-extra capture \
     && uv run --with ruff ruff check . \
     && { [ ! -d tests ] || uv run --with pytest pytest -q; })
done
fi

if want web; then
for pkg in */package.json; do
  [ -f "$pkg" ] || continue
  d=$(dirname "$pkg"); echo "== node: $d"
  # check:bundle is the first-load JS budget (T260); --if-present so only web/ runs it.
  (cd "$d" && npm ci --no-audit --no-fund && npm run lint --if-present && npm test --if-present && npm run build --if-present && npm run check:bundle --if-present)
done
fi

if want e2e; then
echo "== e2e: scenario replay"
bash scripts/e2e.sh
fi

echo "CI OK"
