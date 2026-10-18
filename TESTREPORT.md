# Test report
- main: 6bae59e (T464: protein shake routine - task graph, detector classes, synthetic scenarios)
- run: 2026-10-18T05:30Z (OFFLINE_MODE=true, LIVE_API unset)

## Levels
- 1 Unit (scripts/ci.sh): PASS (CI OK; in-ci e2e 43/43)
- 2 Simulation (scripts/e2e.sh): PASS, 43/43 scenarios (5 new protein_shake_* from T464)
- Smoke (scripts/smoke.sh): PASS (stack up)
- Integration (scripts/integration.sh): PASS
- 3 UI walkthrough: PASS (SPEC §10 path + person check-in)
  - unit overview: residents with status chips; role chooser on first open
  - live replay (Making tea): missed teabag 1:10, repeated pour 1:30, Finished in 1m 43s · 2 errors → Flagged for review → Open alert; the flag also starts Mrs. K's check-in and the supporter alarm shows
  - alert/evidence: What changed, Consistent with (delirium, sundowning), errors, evidence replay, suggested checks; Confirmed → threshold 2.4 → 2.3; no console errors
  - person check-in (T465 fixed): with My routine already open (person `sam`), POST /checkins/demo → "Can you check in?" 0:16 + "I'm okay" appears within ~4 s, no reload
  - live routine picker shows Making tea / Medication with water only; protein shake (T464) is pipeline + scenarios only
- 4 Robustness: PASS (e2e corrupted-frames cases pass)

## Open bug tasks
- none
