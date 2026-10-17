# Test report
- main: 5fb35ad (T418: BarChart)
- run: 2026-10-17T21:45Z (OFFLINE_MODE=true, LIVE_API unset)

## Levels
- 1 Unit (scripts/ci.sh): PASS
- 2 Simulation (scripts/e2e.sh): PASS, 38/38 scenarios
- Smoke (scripts/smoke.sh, stack up): PASS, all checks
- Integration (scripts/integration.sh): PASS, twice (cold + with dev stack up). T426 fix holds; no flake this run.
- 3 UI walkthrough: PASS (UI changed: role chooser, "Viewing as" toggle, People I support, My routine)
  - new role chooser ("Who is this for?") renders cleanly; "Someone I support" → unit overview "4 on watch · 2 normal"
  - Mrs. K detail: baseline chart (threshold 2.4), daily-scores calendar, sessions, care records
  - live replay (tea_skip_teabag_pour_twice): skipped teabag 1:10, repeated pour 1:30, "Finished in 1m 43s · 2 errors" → Flagged for review, overview "1 flagged"
  - alert: 4 timestamped errors, care records, time-of-day breakdown, skeleton replay + ghost, "Consistent with" + rule-outs, suggested checks
  - Confirmed → threshold 2.4 → 2.3; Mrs. K detail baseline now shows 2.3 (T414 fixed)
  - "Myself" view: My routine shell only (who can see, invite); status/notes not wired yet (T409 in flight, not a bug)
  - note: switching views restarts the live replay from the start (by design of remount; not filed)
  - no captured console errors
- 4 Robustness: PASS (not re-run separately; e2e corrupted-frames cases pass)

## Open bug tasks
- none
