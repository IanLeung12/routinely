#!/usr/bin/env bash
# Single CI entrypoint, used by GitHub Actions and by agents locally.
# Runs whatever exists; tasks extend this as the stack lands.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
export LIVE_API=0

echo "== repo tooling"
python3 -m py_compile scripts/tasks.py scripts/codemap.py scripts/mergeq.py scripts/metrics.py
bash -n scripts/integration.sh
python3 scripts/codemap.py >/dev/null
bash -n scripts/worker.sh
bash -n scripts/e2e.sh
bash -n scripts/smoke.sh

for proj in $(find . -maxdepth 2 -name pyproject.toml -not -path "./.tasks/*"); do
  d=$(dirname "$proj"); echo "== python: $d"
  command -v uv >/dev/null || python3 -m pip install -q uv
  # --no-extra capture: mediapipe/opencv are only needed with a camera or a video
  # file, and nothing in CI has either. Capture imports them lazily (T039).
  (cd "$d" && uv sync -q --all-extras --no-extra capture \
     && uv run --with ruff ruff check . \
     && { [ ! -d tests ] || uv run --with pytest pytest -q; })
done

for pkg in */package.json; do
  [ -f "$pkg" ] || continue
  d=$(dirname "$pkg"); echo "== node: $d"
  (cd "$d" && npm ci --no-audit --no-fund && npm run lint --if-present && npm test --if-present && npm run build --if-present)
done

echo "== e2e: scenario replay"
bash scripts/e2e.sh

echo "CI OK"
