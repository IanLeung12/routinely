# Test report
- main: 84bcb55 (SPEC: people + supervisors, §17)
- run: 2026-10-17T20:19Z (OFFLINE_MODE=true, LIVE_API unset)

## Levels
- 1 Unit (scripts/ci.sh): PASS
- 2 Simulation (scripts/e2e.sh): PASS, 38/38 scenarios
- Smoke (scripts/smoke.sh, stack up): PASS, all checks
- Integration (scripts/integration.sh): FLAKY
  - cold run failed again "dashboard did not render (no 'Routine Watch' in DOM)"; immediate re-run OK. Tracked by T367 (P0, claimed).
  - T388 (dev-stack clash) is done.
- 3 UI walkthrough: PASS with one new P1 bug (UI changed: live camera source, session summary, landing page)
  - overview "4 on watch · 2 normal", filters All (6)/Flagged (0)/Watch (4)/Paused (0)
  - live replay (Making tea, recorded source): task map green, skipped teabag 1:10 + repeated pour 1:30, session summary "Finished in 1m 43s (usually ~2m 50s) · 2 errors" → "Flagged for review" + Open alert; overview flips to "1 flagged"
  - alert: 4 timestamped errors, care records, time-of-day strip, replay + ghost, "Consistent with" patterns + rule-outs
  - Confirmed → alert threshold 2.4 → 2.3, "Marked as confirmed"
  - Mrs. K detail after confirm still shows "flag threshold 2.4" on the baseline chart → filed T414 (P1)
  - new /landing.html renders cleanly
  - no captured console errors
- 4 Robustness: PASS (not re-run; e2e corrupted-frames cases still pass)

## Open bug tasks
- T367 (P0, integration cold-start render)
- T414 (P1, resident detail threshold not feedback-tuned)
