# Test report
- main: 3976dad (T461: show the live camera/skeleton session on My routine)
- run: 2026-10-18T04:25Z (OFFLINE_MODE=true, LIVE_API unset)

## Levels
- 1 Unit (scripts/ci.sh): PASS. pytest 1628 passed / 1 skipped; vitest 987 passed (137 files); e2e inside ci OK. T459 flake fix holds under load
- 2 Simulation (scripts/e2e.sh): PASS, 38/38 scenarios
- Smoke (scripts/smoke.sh): PASS (needs the stack up; 24 connection-refused failures if run before `dev.sh up`)
- Integration (scripts/integration.sh): PASS
- 3 UI walkthrough: PASS (SPEC §10 path + supporter alarm); one P1 gap on the person check-in card → T465
  - unit overview: residents with status chips; "Safety alarms could not refresh" banner gone (T457 fixed)
  - live replay: missed teabag 1:10, repeated pour 1:30, Finished in 1m 43s · 2 errors → Flagged for review → Open alert
  - alert/evidence: What changed, Consistent with (delirium, sundowning), errors, evidence, suggested checks; Confirmed → threshold 2.4 → 2.3
  - supporter alarm: "Mrs. K hasn't checked in", escalation timeline, I'm on it → Acknowledged → Resolve → "check-in resolved"; /checkins/active empty afterwards
  - My routine (T461): "Your session" with live skeleton view + task map renders
  - person check-in: shows the live pending one (0:16, T460 fixed), but only after a reload; the card fetches once on mount → T465
- 4 Robustness: PASS (e2e corrupted-frames cases pass)

## Open bug tasks
- T465 (person check-in card doesn't pick up a new check-in without a reload, P1)
