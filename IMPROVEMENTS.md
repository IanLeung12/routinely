# IMPROVEMENTS

Retro agent's experiments on the agent loop. One line each; judged on later runs.

## Open experiments
- E3 (2026-10-17): 36/~280 worker logs end with "I'll wait for the CI/monitor notification" (background ci.sh, Monitor, ScheduleWakeup, waiting on mergeq) → released as no-progress + 15 min backoff; 9 early ends in 6 h → worker.md: name the banned background tools, foreground ci.sh/`gh pr checks --watch` with 600 s timeout, stop at in-review instead of waiting for merge (PR #269). Watch: early_session_ends/6 h, 9 → ≤2.
- E4 (2026-10-17): same failure despite prompt rule → MODELS.md claude flags `--disallowedTools Monitor ScheduleWakeup`, light-worker.md same wording (PR #271; takes effect on worker restart). Watch: worker logs ending in "wait…" without `T<n> in-review|done|blocked`, 36 → 0.

## Closed
- E1 (2026-10-17): T071 blocked with finished work stranded locally because local Vitest timed out in unrelated tests (max_API_light 25% first-try, 2 releases, Windows) → worker.md step 4: push when the only failures are outside the area and also fail on clean origin/main; PR CI gates (PR #113). **Kept (10:55):** max_API_light first-try now 90%; T071/T096 later merged; no new blocks for local-only CI failures.
- E2 (2026-10-17): tasks.py parses acceptance bullets (`- x: y`) as fields, so notes land mid-acceptance (T071) and a `- status:` bullet could hijack status → board task T133. **Kept (10:55):** T133 merged first try; no notes inside task bodies since.
