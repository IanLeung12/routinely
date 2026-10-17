# IMPROVEMENTS

Retro agent's experiments on the agent loop. One line each; judged on later runs.

## Open experiments
- E3 (2026-10-17): 36/~280 worker logs end with "I'll wait for the CI/monitor notification" (background ci.sh, Monitor, ScheduleWakeup, waiting on mergeq) → released as no-progress + 15 min backoff; 9 early ends in 6 h → worker.md: name the banned background tools, foreground ci.sh/`gh pr checks --watch` with 600 s timeout, stop at in-review instead of waiting for merge (PR #269). Watch: early_session_ends/6 h, 9 → ≤2.
- E4 (2026-10-17): same failure despite prompt rule → MODELS.md claude flags `--disallowedTools Monitor ScheduleWakeup`, light-worker.md same wording (PR #271; takes effect on worker restart). Watch: worker logs ending in "wait…" without `T<n> in-review|done|blocked`, 36 → 0.
  - 17:00 check: early ends 3 in last 3 h (was 9/6 h): better, not at target; keep. E4 flag never applied: running workers started before PR #271 (FLAGS read once) and w1's launcher FLAGS override omits it; 2 post-14:00 sessions (T187, T307 on w4) still ended "waiting for monitor".
- E5 (2026-10-17): E4 flag not reaching workers → board task T342 (worker.sh always adds `--disallowedTools Monitor ScheduleWakeup` for claude, re-reads MODELS.md flags per loop). Watch: post-merge worker logs ending in "wait…" without `T<n> in-review|done|blocked`, 2/58 since 14:05 → 0.
- E6 (2026-10-17): LESSONS.md at 40/40 cap (oldest drop off) with 2 duplicate pairs (dev.sh ports, Windows Vitest workers) and 2 one-off task notes (T310 filter, LiveSession area) → merged/pruned to 36 (board commit). Watch: lesson count stays ≤40 without losing pre-cap lessons; no repeat of the dev.sh-port mistake.

## Closed
- E1 (2026-10-17): T071 blocked with finished work stranded locally because local Vitest timed out in unrelated tests (max_API_light 25% first-try, 2 releases, Windows) → worker.md step 4: push when the only failures are outside the area and also fail on clean origin/main; PR CI gates (PR #113). **Kept (10:55):** max_API_light first-try now 90%; T071/T096 later merged; no new blocks for local-only CI failures.
- E2 (2026-10-17): tasks.py parses acceptance bullets (`- x: y`) as fields, so notes land mid-acceptance (T071) and a `- status:` bullet could hijack status → board task T133. **Kept (10:55):** T133 merged first try; no notes inside task bodies since.
