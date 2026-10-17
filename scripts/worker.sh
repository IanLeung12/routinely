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
# MAX_TASKS=n stop after n tasks. BACKOFF=900 seconds to pause after a run that made no progress
# (e.g. usage/rate limit hit); the task is released back to todo so nobody waits on it.
#
# Run each worker in its own clone (or `git worktree add ../htv-w1`) so branches don't collide.
set -euo pipefail
: "${AGENT:?set AGENT=yourname}"
TOOL=${TOOL:-claude}; CLASS=${CLASS:-light}; IDLE=${IDLE:-300}; BACKOFF=${BACKOFF:-900}; DONE_COUNT=0
cd "$(git rev-parse --show-toplevel)"

FLAGS=${FLAGS:-$(sed -n "s|^- $TOOL/$CLASS: ||p" MODELS.md)}
MODEL="$TOOL $FLAGS"
PROMPT_FILE=prompts/worker.md; [ "$CLASS" = light ] && PROMPT_FILE=prompts/light-worker.md

SELF_SUM=$(cksum < scripts/worker.sh)
while true; do
  if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    echo "working tree dirty; commit or stash first"; exit 1
  fi
  git fetch -q origin && git switch -q --detach origin/main
  # Pick up a newer worker.sh from main automatically (between tasks only).
  if [ "$(cksum < scripts/worker.sh)" != "$SELF_SUM" ]; then echo "$(date -u +%H:%M) worker.sh updated; restarting"; exec bash scripts/worker.sh; fi
  python3 scripts/tasks.py reconcile >/dev/null 2>&1 || true   # merged PRs -> done (cheap, no LLM)
  TASK=$(python3 scripts/tasks.py auto --class "$CLASS" --agent "$AGENT")
  if [ "$TASK" = NO_TASK ]; then
    [ -n "${ONCE:-}" ] && { echo "no task"; exit 0; }
    echo "$(date -u +%H:%M) no claimable $CLASS task; sleeping ${IDLE}s"; sleep "$IDLE"; continue
  fi
  ID=$(printf '%s\n' "$TASK" | sed -n '1s/^### \(T[0-9]*\).*/\1/p')
  echo "$(date -u +%H:%M) $AGENT took $ID ($MODEL)"
  PROMPT=$(TASK="$TASK" ID="$ID" AGENT="$AGENT" CLASS="$CLASS" MODEL="$MODEL" python3 - "$PROMPT_FILE" <<'PY'
import os, re, sys
s = open(sys.argv[1]).read()
for k in ("TASK", "ID", "AGENT", "CLASS", "MODEL"):
    s = s.replace("{{%s}}" % k, os.environ[k])
# Attach the area guide(s) matching the task's `area:` line (prompts/areas/*.md).
m = re.search(r"^- area: (.*)$", os.environ["TASK"], re.M)
area = m.group(1) if m else ""
rules = [("web", r"\bweb/"), ("pipeline", r"\bpipeline/|tests/scenarios"), ("infra", r"\bscripts/|\.github/|deploy")]
guides = [g for g, pat in rules if re.search(pat, area) and os.path.exists(f"prompts/areas/{g}.md")]
for g in guides:
    s += "\n\n---\n" + open(f"prompts/areas/{g}.md").read()
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
  # No progress (still 'claimed', no PR)? Release the task and back off: usually a usage limit.
  ST=$(python3 scripts/tasks.py show "$ID" | sed -n 's/^- status: //p')
  PR=$(python3 scripts/tasks.py show "$ID" | sed -n 's/^- pr: //p')
  if [ "$ST" = claimed ] && { [ -z "$PR" ] || [ "$PR" = "—" ] || [ "$PR" = "-" ]; }; then
    python3 scripts/tasks.py set "$ID" status=todo owner=— claimed=— note="released by $AGENT: run ended without progress" --agent "$AGENT" >/dev/null
    echo "$(date -u +%H:%M) $ID released (no progress; limit hit?); backing off ${BACKOFF}s"
    sleep "$BACKOFF"
  fi
  DONE_COUNT=$((DONE_COUNT+1))
  [ -n "${ONCE:-}" ] && exit 0
  [ -n "${MAX_TASKS:-}" ] && [ "$DONE_COUNT" -ge "$MAX_TASKS" ] && { echo "reached MAX_TASKS=$MAX_TASKS"; exit 0; }
done
