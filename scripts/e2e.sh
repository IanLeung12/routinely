#!/usr/bin/env bash
# Replay every recorded scenario through the pipeline, offline.
#
# This is the simulation layer the tester runs before it trusts a change, and
# scripts/ci.sh calls it on every PR. It needs no camera, no keys and no network:
# nothing in a replay makes an API call, and OFFLINE_MODE/LIVE_API are set here so
# that stays true as the verifier and the summariser land.
#
#   scripts/e2e.sh                        every scenario in tests/scenarios/
#   scripts/e2e.sh tests/scenarios/tea_normal [...]   only the ones named
#
# Prints PASS or FAIL per scenario, with what differed, and exits non-zero if any
# scenario failed. Writing a scenario: tests/scenarios/README.md.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

export OFFLINE_MODE=true
export LIVE_API=0

scenarios=()
if [ "$#" -gt 0 ]; then
  for dir in "$@"; do
    case "$dir" in
      /*) scenarios+=("$dir") ;;
      *) scenarios+=("$PWD/$dir") ;;
    esac
  done
else
  while IFS= read -r dir; do
    scenarios+=("$dir")
  done < <(find "$PWD/tests/scenarios" -mindepth 1 -maxdepth 1 -type d | sort)
fi

if [ "${#scenarios[@]}" -eq 0 ]; then
  echo "no scenarios in tests/scenarios/" >&2
  exit 1
fi

command -v uv >/dev/null || python3 -m pip install -q uv
cd pipeline
uv sync -q --all-extras
exec uv run python -m routine_watch.replay --check "${scenarios[@]}"
