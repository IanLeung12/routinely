# Test report
- main: 1d6ee98 (T271: exclude paused residents from the handoff quiet count)
- run: 2026-10-17 13:10 UTC (OFFLINE_MODE=true, LIVE_API unset)

## Levels
- 1 Unit (scripts/ci.sh): PASS
- 2 Simulation (scripts/e2e.sh): PASS, 25/25 scenarios
- Smoke (scripts/smoke.sh, stack up): PASS, all checks
- Integration (scripts/integration.sh): PASS ("OK integration (api + dashboard + live ws)"); T270 looks resolved on this sha
- 3 UI walkthrough: PASS (demo path end to end)
  - unit overview: status chips, patterns, sparklines, filters, demo banner
  - Mrs. K detail: baseline chart + threshold, heat calendar, sessions, care records
  - monitoring switch (T243) now writes real state: Paused → "No camera data is processed while paused", "Recent changes: Paused by nurse · time" (T262); resume adds "Resumed by nurse"
  - live panel while paused (after reload/remount): "Monitoring is paused for room 204" + "Check again" button (T266). Note: toggling the switch doesn't update an already-open live panel until remount or Check again (by design)
  - shift handoff: names paused room 204, "3 residents with nothing to review" (T259/T271)
  - live session: steps go green, teabag missed 1:10, pour repeated 1:30, summary vs usual, "Flagged for review / Open alert"
  - alert: 4 errors across 2 sessions, skeleton replay, "Consistent with ..." + rule-outs, suggested checks
  - "Confirmed": "Marked as confirmed", threshold 2.4 → 2.3
- 4 Robustness: PASS (not re-run this time; e2e corrupted-frames cases still pass)

## Open bug tasks
- T270 (integration failing @21fc468) — passes @1d6ee98, noted on task for orchestrator to close
