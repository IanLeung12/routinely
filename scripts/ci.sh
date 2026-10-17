#!/usr/bin/env bash
# Single CI entrypoint, used by GitHub Actions and by agents locally.
# Runs whatever exists; tasks extend this as the stack lands.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

echo "== repo tooling"
python3 -m py_compile scripts/tasks.py
bash -n scripts/worker.sh

for proj in $(find . -maxdepth 2 -name pyproject.toml -not -path "./.tasks/*"); do
  d=$(dirname "$proj"); echo "== python: $d"
  command -v uv >/dev/null || python3 -m pip install -q uv
  (cd "$d" && uv sync -q --all-extras && uv run --with ruff ruff check . \
     && { [ ! -d tests ] || uv run --with pytest pytest -q; })
done

for pkg in */package.json; do
  [ -f "$pkg" ] || continue
  d=$(dirname "$pkg"); echo "== node: $d"
  (cd "$d" && npm ci --no-audit --no-fund && npm run lint --if-present && npm test --if-present && npm run build --if-present)
done

echo "CI OK"
