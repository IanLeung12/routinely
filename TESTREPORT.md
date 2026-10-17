# Test report
- main: 355d6b1 (T183: rank the overview's top pattern with this resident's nurse answers)
- run: 2026-10-17 09:50 UTC (OFFLINE_MODE=true, LIVE_API unset)

## Levels
- 1 Unit (scripts/ci.sh): PASS
- 2 Simulation (scripts/e2e.sh): PASS, 23/23 scenarios (adds meds_pill_twice, pattern_motor_slowing)
- Smoke (scripts/smoke.sh): PASS, all checks (T154 fixed: session replay + normal_replay return frames)
- 3 UI walkthrough: FAIL (only T155 left on the demo path)
  - unit overview: residents with status chips, top pattern per resident, demo banner + Reset demo
  - Mrs. K detail: baseline chart, slow drift, heat calendar with legend, sessions, care records render
  - live session: steps go green, teabag missed (red), pour repeated (amber), errors listed with times, "Flagged for review / Open alert"
  - after the live flag, overview updates to "1 flagged for review" and Alerts list fills without reload (T156 fixed); list labels resident by id "mrs-k" (covered by T196)
  - alert view from the live session still lists synthetic errors (fill kettle/boil), not the live teabag/pour → T155 (P0, claimed)
  - evidence: replay now plays (T154 fixed) but shows object boxes only, no skeleton/hands → T207 (P1); "Today" caption unreadable → T208 (P1)
  - patterns ("Consistent with ..." + rule-outs), suggested checks, care-record context render
  - "Confirmed": "Marked as confirmed", threshold 2.4 → 2.3
- 4 Robustness: not run (level 3 not passing)

## Open bug tasks
- T155 (P0): live-session alert lists synthetic errors, not the live ones
- T207 (P1): no skeleton in live view / ghost replay (synthetic frames have empty poses)
- T208 (P1): ghost replay "Today" caption unreadable
