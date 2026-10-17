# Test report
- main: 8c81e18 (T369: privacy panel usable at phone width (375px))
- run: 2026-10-17 UTC (OFFLINE_MODE=true, LIVE_API unset)

## Levels
- 1 Unit (scripts/ci.sh): PASS
- 2 Simulation (scripts/e2e.sh): PASS, 38/38 scenarios
- Smoke (scripts/smoke.sh, stack up): PASS, all checks
- Integration (scripts/integration.sh): FLAKY
  - cold run (nothing up) failed again "dashboard did not render (no 'Routine Watch' in DOM)"; immediate re-run OK. Second sighting → tracked by T367 (P0, todo).
  - run while a dev stack is up fails ("API already running ... timed out waiting for API at :8100") and its EXIT trap tears down the dev stack → filed T388.
- 3 UI walkthrough: PASS, demo path re-walked (UI changed: filter counts, handoff print, replay player, session list mobile)
  - Reset → overview "4 on watch · 2 normal", filters All (6)/Flagged (0)/Watch (4)/Paused (0) → Mrs. K detail (baseline chart, threshold 2.4, heat calendar, session list)
  - live session: task map turns green, skipped teabag 1:10 + repeated pour 1:30 shown → "Flagged for review" + Open alert; overview flips to "1 flagged", Flagged (1)
  - alert view: 4 timestamped errors, replay Play advances, "Consistent with" patterns + rule-outs, suggested checks
  - Confirmed → threshold 2.4 → 2.3, "Marked as confirmed"; title "Alert · Mrs. K — Routine Watch"
  - shift handoff: 3 of 6 to review, Print handoff button, chips readable
  - no captured console errors
- 4 Robustness: PASS (not re-run; e2e corrupted-frames cases still pass)

## Open bug tasks
- T367 (P0, integration cold-start render)
- T388 (P1, integration.sh vs running dev stack)
