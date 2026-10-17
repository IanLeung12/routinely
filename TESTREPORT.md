# Test report
- main: 333d4de (T244: live screen says monitoring is paused instead of sitting empty)
- run: 2026-10-17 12:10 UTC (OFFLINE_MODE=true, LIVE_API unset)

## Levels
- 1 Unit (scripts/ci.sh): PASS
- 2 Simulation (scripts/e2e.sh): PASS, 25/25 scenarios
- Smoke (scripts/smoke.sh, stack up): PASS, all checks (incl. seeded alert survives /demo/reset)
- 3 UI walkthrough: PASS (demo path end to end)
  - unit overview: status chips, top pattern, sparklines, filters, demo banner
  - Mrs. K detail: baseline chart + threshold, slow drift, heat calendar, sessions, care records; new monitoring switch renders (UI-only until T243 lands; no PUT sent yet)
  - room paused via API (PUT /rooms/204/monitoring on=false): live screen shows "Monitoring is paused for room 204" (T244 works); /demo/reset resumes it (T192 works)
  - live session: steps go green, teabag missed, pour repeated, errors with times, summary vs usual, "Flagged for review / Open alert"
  - alert: 4 errors across 2 sessions, evidence replay with skeleton + boxes, "Consistent with ..." patterns + rule-outs, suggested checks
  - "Confirmed": "Marked as confirmed", threshold 2.4 → 2.3; feedback buttons now styled (T232 fixed)
  - no console errors
- 4 Robustness: PASS
  - corrupted frames (truncated / garbage lines / empty) via e2e.sh: clean line-numbered error, no traceback
  - API killed: dashboard falls back to mock data ("Mock data" label), no crash

## Open bug tasks
- none (T232 done)
