# Test report
- main: a4a94a1 (T068: show demo banner in App); also checked cdc1798
- run: 2026-10-17 08:45 UTC (OFFLINE_MODE=true, LIVE_API unset)

## Levels
- 1 Unit (scripts/ci.sh): PASS
- 2 Simulation (scripts/e2e.sh): PASS, 21/21 scenarios (adds meds_pill_before_water, pattern_* x5, tea_bad_sessions_far_apart, tea_teabag_three_times)
- Smoke (scripts/smoke.sh): FAIL, 2 checks: session replay and normal_replay return no frames → T154
- 3 UI walkthrough: FAIL (now on real API data; T119–T123 fixed)
  - unit overview: renders real residents with status chips + demo banner
  - Mrs. K detail: baseline chart, slow drift, heat calendar, sessions, care records render
  - live session: task map steps go green, missed/repeated steps marked, errors listed, "Open alert" appears; skeleton view shows objects
  - after the live flag, overview chip/status line and Alerts list don't refresh until reload → T156 (P1)
  - alert view opened from the live session shows synthetic errors (fill kettle/boil), not the live session's (teabag/pour); summary says "4 errors this session" across 2 sessions → T155 (P0)
  - evidence: "No replay available / No skeleton data" for every error → T154 (P0)
  - patterns ("Consistent with ..." + rule-outs), suggested checks, care-record context render
  - "Confirmed": "Marked as confirmed", threshold visibly 2.4 → 2.3 (real API)
- 4 Robustness: not run (level 3 not passing)

## Open bug tasks
- T154 (P0): evidence replay empty (stand-in recordings shorter than error windows)
- T155 (P0): live-session alert lists synthetic errors, not the live ones
- T156 (P1): overview/Alerts list don't refresh after live flag
