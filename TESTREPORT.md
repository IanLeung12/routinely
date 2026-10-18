# Test report
- main: 3a522b0 (T451: Check-in UI (person side): countdown, "I'm okay" + PIN pad)
- run: 2026-10-18T01:45Z (OFFLINE_MODE=true, LIVE_API unset)

## Levels
- 1 Unit (scripts/ci.sh): FAIL (load flake). pytest 1626 passed / 1 skipped; vitest 970 passed / 2 failed (MyRoutine "nobody else can see this", AlertView.keyboard "tabs to Confirmed"), both findBy 1 s timeouts on lazy chunks at load avg ~17; both pass in isolation, GitHub CI on main green → T459
- 2 Simulation (scripts/e2e.sh): PASS, 38/38 scenarios
- Smoke (scripts/smoke.sh): PASS
- Integration (scripts/integration.sh): PASS
- 3 UI walkthrough: FAIL (supervisor alarm banner, T457; core SPEC §10 path passes)
  - every supporter screen shows "Safety alarms could not refresh… Retrying…": UI polls `/checkins/active?person=X&supporter=nurse-ana` → 422 (known, T457 P0 claimed)
  - unit overview "4 on watch · 2 normal", Mrs. K detail baseline (threshold 2.4) + daily scores
  - live replay: Finished in 1m 43s · 2 errors → Flagged for review → Open alert
  - alert/evidence: 4 timestamped errors, Consistent with patterns, replay controls, suggested checks; Confirmed → threshold 2.4 → 2.3
  - routine builder: Making toast → Draft routine renders node map + step editor, Save routine lands in Routines list (T455 fixed)
  - person check-in (T451): POST /checkins/demo person=sam → Myself shows countdown ring + I'm okay → PIN pad → 1234 → "Thanks, you're checked in"; stacked check-ins show the stale one at 0:00 → T460
- 4 Robustness: PASS (e2e corrupted-frames cases pass)

## Open bug tasks
- T457 (alarm UI vs real check-in API, P0, claimed)
- T459 (web test flake under load, P1)
- T460 (person sees stale check-in when several open, P1)
