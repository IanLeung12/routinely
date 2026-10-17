#!/usr/bin/env bash
# Worker loop: claim a task (no tokens spent), run one fresh agent session on it, repeat.
#
#   AGENT=max TOOL=claude CLASS=light scripts/worker.sh
#   AGENT=ian-codex TOOL=codex CLASS=heavy scripts/worker.sh
#
# AGENT  your name on the board (required)
# TOOL   claude | codex (default claude)
# CLASS  light | standard | heavy: the most expensive tasks you'll take (default light)
# FLAGS  override the model flags from MODELS.md (optional)
# ONCE=1 do a single task then exit. IDLE=300 seconds to wait when the board is empty.
#
# Run each worker in its own clone (or `git worktree add ../htv-w1`) so branches don't collide.
set -euo pipefail
: "${AGENT:?set AGENT=yourname}"
TOOL=${TOOL:-claude}; CLASS=${CLASS:-light}; IDLE=${IDLE:-300}
cd "$(git rev-parse --show-toplevel)"

FLAGS=${FLAGS:-$(sed -n "s|^- $TOOL/$CLASS: ||p" MODELS.md)}
MODEL="$TOOL $FLAGS"
PROMPT_FILE=prompts/worker.md; [ "$CLASS" = light ] && PROMPT_FILE=prompts/light-worker.md

while true; do
  if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    echo "working tree dirty; commit or stash first"; exit 1
  fi
  git fetch -q origin && git switch -q --detach origin/main
  TASK=$(python3 scripts/tasks.py auto --class "$CLASS" --agent "$AGENT")
  if [ "$TASK" = NO_TASK ]; then
    [ -n "${ONCE:-}" ] && { echo "no task"; exit 0; }
    echo "$(date -u +%H:%M) no claimable $CLASS task; sleeping ${IDLE}s"; sleep "$IDLE"; continue
  fi
  ID=$(printf '%s\n' "$TASK" | sed -n '1s/^### \(T[0-9]*\).*/\1/p')
  echo "$(date -u +%H:%M) $AGENT took $ID ($MODEL)"
  PROMPT=$(TASK="$TASK" ID="$ID" AGENT="$AGENT" CLASS="$CLASS" MODEL="$MODEL" python3 - "$PROMPT_FILE" <<'PY'
import os, sys
s = open(sys.argv[1]).read()
for k in ("TASK", "ID", "AGENT", "CLASS", "MODEL"):
    s = s.replace("{{%s}}" % k, os.environ[k])
print(s)
PY
)
  mkdir -p .worker-logs
  LOG=".worker-logs/$ID-$(date -u +%m%d-%H%M).log"
  # shellcheck disable=SC2086
  if [ "$TOOL" = codex ]; then
    codex exec --dangerously-bypass-approvals-and-sandbox $FLAGS "$PROMPT" 2>&1 | tee "$LOG" || true
  else
    claude -p --dangerously-skip-permissions $FLAGS "$PROMPT" 2>&1 | tee "$LOG" || true
  fi
  git switch -q --detach origin/main 2>/dev/null || true
  [ -n "${ONCE:-}" ] && exit 0
done
