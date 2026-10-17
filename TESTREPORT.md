# Test report
- main: dc9a6ef (T314: scenarios tea_two_errors_one_session and tea_long_pause_not_error)
- run: 2026-10-17 UTC (OFFLINE_MODE=true, LIVE_API unset)

## Levels
- 1 Unit (scripts/ci.sh): PASS
- 2 Simulation (scripts/e2e.sh): PASS, 33/33 scenarios (4 new: meds_pill_substitution, meds_two_errors_one_session, tea_long_pause_not_error, tea_two_errors_one_session)
- Smoke (scripts/smoke.sh, stack up): PASS, all checks (incl. new feedback contract check)
- Integration (scripts/integration.sh): PASS ("OK integration (api + dashboard + live ws)"), run before dev.sh up
- 3 UI walkthrough: PASS, full demo path re-walked
  - Reset demo → overview 4 on watch · 2 normal → Mrs. K detail (baseline chart, threshold 2.4, monitoring "On", recent changes, consent)
  - live session (real-time speed, ~1m45s) → "Flagged for review" + Open alert; overview flips to 1 flagged
  - alert view: 4 timestamped errors, replay Play, patterns "Consistent with" + rule-outs, suggested checks
  - Confirmed → threshold 2.4 → 2.3, "Marked as confirmed"; title "Alert · Mrs. K — Routine Watch"
  - no captured console errors
  - note (not filed, pre-existing): Mrs. K header packs the monitoring switch + recent-changes block between name and status chip; readable but cramped
- 4 Robustness: PASS (not re-run; e2e corrupted-frames cases still pass)

## Open bug tasks
- none
