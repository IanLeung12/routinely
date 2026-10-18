# Test report
- main: 2e488ba (T444: surface routine builder API refusals instead of a canned draft/fake save)
- run: 2026-10-18T00:25Z (OFFLINE_MODE=true, LIVE_API unset)

## Levels
- 1 Unit (scripts/ci.sh): PASS. pytest 1550 passed / 1 skipped; vitest 905 passed (130 files); e2e inside CI 38/38. (T445 flake fixed.)
- 2 Simulation (scripts/e2e.sh): PASS, 38/38 scenarios
- Smoke (scripts/smoke.sh, stack up): PASS, all checks
- Integration (scripts/integration.sh): PASS (with dev stack up)
- 3 UI walkthrough: FAIL (routine builder; core SPEC §10 path passes)
  - home now opens on "Myself" / My routine: how this week looks + weekly chart, renders cleanly
  - "Someone I support" → unit overview "4 on watch · 2 normal", 6 rows with chips + sparklines
  - Mrs. K detail: baseline (threshold 2.4), daily scores, sessions, care records
  - live replay: teabag missed, pour repeated, "Finished in 1m 43s · 2 errors" → Flagged for review + Open alert
  - alert/evidence: 4 timestamped errors, "Consistent with" patterns, replay with 0.5×/1×/2× speed, care records, suggested checks
  - Confirmed → threshold 2.4 → 2.3
  - New routine → example → Draft routine: whole app goes blank, `step.depends_on is undefined` (API sends `deps`) → T455
- 4 Robustness: PASS (not re-run separately; e2e corrupted-frames cases pass)

## Open bug tasks
- T455 (routine builder draft crashes the dashboard, P0)
