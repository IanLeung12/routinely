# Test report
- main: e38f907 (web: bundle budget 94 KB; includes invite-as-supporter, live picker from /routines, protein shake tweaks)
- run: 2026-10-18T07:45Z (OFFLINE_MODE=true, LIVE_API unset)

## Levels
- 1 Unit (scripts/ci.sh): PASS (CI OK; in-ci e2e 43/43)
- 2 Simulation (scripts/e2e.sh): PASS, 43/43 scenarios
- Smoke (scripts/smoke.sh): PASS
- Integration (scripts/integration.sh): PASS
- 3 UI walkthrough: PASS (SPEC §10 path)
  - unit overview: 6 residents with status chips; role chooser on first open
  - live replay (Making tea): skipped teabag 1:10, repeated pour 1:30 → Mrs. K flagged → Open alert
  - alert/evidence: What changed, Consistent with (delirium, sundowning), errors, evidence, suggested checks; Confirmed → threshold 2.4 → 2.3; no console errors
  - live picker is now a dropdown fed by /routines: Make a protein shake / Making tea / Medication with water / Make toast. Protein shake replay runs (7-step map, skipped "Scoop powder" 0:22); Make toast (no recording) shows camera.sh hint instead of crashing
- 4 Robustness: PASS (e2e corrupted-frames cases pass)

## Open bug tasks
- none
