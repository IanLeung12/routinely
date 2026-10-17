# Test report
- main: 13032a4 (T118: pattern library page)
- run: 2026-10-17 11:05 UTC (OFFLINE_MODE=true, LIVE_API unset)

## Levels
- 1 Unit (scripts/ci.sh): PASS
- 2 Simulation (scripts/e2e.sh): PASS, 25/25 scenarios (adds meds_abandoned, meds_self_corrected)
- Smoke (scripts/smoke.sh, stack up): PASS, all checks
- 3 UI walkthrough: PASS (demo path end to end)
  - unit overview: status chips, top pattern, sparklines, All/Flagged/Watch filter, demo banner
  - Mrs. K detail: baseline chart + threshold, slow drift, heat calendar, sessions, care records
  - live session: stand-in skeleton tracked (T207 fixed), steps go green, teabag missed (red), pour repeated (amber), errors with times, session summary vs usual, "Flagged for review / Open alert"
  - alert: now lists the live session's own errors (skipped teabag 1:10, repeated pour 1:30) alongside the earlier session's (T155 fixed)
  - evidence: replay plays with skeleton + object boxes; "Today / Usual" caption readable (T208 fixed)
  - "Consistent with ..." patterns + rule-outs, suggested checks, Copy summary
  - "Confirmed": "Marked as confirmed", threshold 2.4 → 2.3
  - pattern library page (T118) renders with signals, rule-outs, sources
- 4 Robustness: PASS
  - corrupted frames (truncated line / garbage lines / empty file) via e2e.sh: clean line-numbered error, no traceback
  - same files as /ws/live scenarios: socket closed with 4404, API keeps serving
  - API killed: dashboard falls back to mock data (live view labelled "Mock data"), no crash

## Open bug tasks
- none
