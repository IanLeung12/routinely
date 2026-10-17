# Test report
- main: 5c8db0c (T095: Add hesitation edge case tests)
- run: 2026-10-17 07:25 UTC (OFFLINE_MODE=true, LIVE_API unset)

## Levels
- 1 Unit (scripts/ci.sh): PASS
- 2 Simulation (scripts/e2e.sh): PASS, 13/13 scenarios (meds_normal, meds_skip_water, tea_abandoned, tea_kettle_twice, tea_milk_sugar, tea_no_kettle, tea_normal, tea_self_corrected, tea_sequence_error, tea_single_bad_no_flag, tea_skip_teabag_pour_twice, tea_substitution, tea_unclear_not_error)
- Smoke (scripts/smoke.sh): FAIL, 1 check (script bug; the routes work) → T123
- 3 UI walkthrough: FAIL
  - API sends no CORS headers: every dashboard fetch fails and silently falls back to web mocks (overview, Mrs. K, alert, feedback all mock) → T119 (P0)
  - unit overview: renders (mock data)
  - Mrs. K detail (baseline chart, heat calendar with weekday headers, sessions, care records): renders (mock data); T048 fixed
  - live session over /ws/live: works (real data); task map overflows and hides the error steps → T120 (P0); skeleton panel never gets frames → T122
  - alert/evidence view: summary, timestamped errors, skeleton replay + ghost overlay, suggested checks render (mock alert)
  - "Confirmed": shows "Marked as confirmed" but threshold stays 1.2 (mock path; the API itself lowers 4.09 → 3.88) → T119
  - API alert content (visible once T119 lands): placeholder errors, repeated summary clauses, grows per page load → T121
- 4 Robustness: not run (level 3 not passing)

## Open bug tasks
- T119 (P0): API missing CORS → dashboard on mock data
- T120 (P0): live task map overflow hides error steps
- T121 (P1): demo alert placeholder errors / garbled summary / grows per load
- T122 (P1): live skeleton view empty for the demo scenario
- T123 (P1): smoke.sh replay check always fails
