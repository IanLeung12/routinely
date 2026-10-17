# Test report
- main: 477d383 (T353: one shared print stylesheet for alert view and resident detail)
- run: 2026-10-17 UTC (OFFLINE_MODE=true, LIVE_API unset)

## Levels
- 1 Unit (scripts/ci.sh): PASS
- 2 Simulation (scripts/e2e.sh): PASS, 34/34 scenarios
- Smoke (scripts/smoke.sh, stack up): PASS, all checks
- Integration (scripts/integration.sh): PASS ("OK integration (api + dashboard + live ws)")
  - note (not filed): first run, cold before dev.sh up, failed "dashboard did not render (no 'Routine Watch' in DOM)"; dashboard rendered fine in the browser and a re-run after dev.sh down passed. Likely Vite cold-start/dep-optimise timing; refile if it repeats.
- 3 UI walkthrough: PASS, full demo path re-walked (UI changed: sort/filter prefs, handoff delta, print stylesheet, heat calendar mobile)
  - Reset demo → overview 4 on watch · 2 normal, new sort/filter groups → Mrs. K detail (WATCH chip + Print beside name, baseline chart, threshold 2.4, heat calendar); earlier "cramped header" note resolved
  - live session (real-time, 1m43s) → "Flagged for review" + Open alert; overview flips to 1 flagged
  - alert view: 4 timestamped errors, replay Play, "Consistent with" patterns + rule-outs, suggested checks, Print button
  - Confirmed → threshold 2.4 → 2.3, "Marked as confirmed"; title "Alert · Mrs. K — Routine Watch"
  - no captured console errors
- 4 Robustness: PASS (not re-run; e2e corrupted-frames cases still pass)

## Open bug tasks
- none
