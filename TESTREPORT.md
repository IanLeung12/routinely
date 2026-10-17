# Test report
- main: 64ab65c (tasks.py auto: report why claims fail)
- run: 2026-10-17T23:05Z (OFFLINE_MODE=true, LIVE_API unset)

## Levels
- 1 Unit (scripts/ci.sh): FAIL (flaky). pytest 1438 passed; vitest 1 failed / 844 passed: `MyRoutine.test.tsx > says nobody else can see this…` times out waiting for the lazy "How this week looks" section (still "Loading your week…"). Fails 1 of 3 runs in isolation → T445.
- 2 Simulation (scripts/e2e.sh): PASS, 38/38 scenarios
- Smoke (scripts/smoke.sh, stack up): PASS, all checks
- Integration (scripts/integration.sh): PASS (with dev stack up)
- 3 UI walkthrough: PASS
  - role chooser → "I'm supporting someone" → unit overview "4 on watch · 2 normal"
  - Mrs. K detail: baseline chart (threshold 2.4), daily-scores calendar, sessions, care records
  - live replay: skipped teabag 1:10, repeated pour 1:30, "Finished in 1m 43s · 2 errors" → Flagged for review, overview "1 flagged"
  - alert/evidence: 4 timestamped errors, skeleton replay, "Consistent with" + rule-outs, care records, suggested checks
  - Confirmed → threshold 2.4 → 2.3
  - "Myself" view now wired (T409): "How this week looks" (today 4 min vs usual 3 min), weekly bar chart vs usual, recent sessions; renders cleanly
  - replay list (T430) / replay notes (T431) not reachable from the nav yet (components only)
  - no captured console errors
- 4 Robustness: PASS (not re-run separately; e2e corrupted-frames cases pass)

## Open bug tasks
- T445 (flaky MyRoutine unit test, P0)
