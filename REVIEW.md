# REVIEW

- last-reviewed: 602d205
- next-area: contracts+api

## Known issues filed
- T055 scoring duplicated replay.py/live.py; empty-scenario IndexError
- T073 live screen uses MOCK_STEPS; no session_start with task graph
- T075 ErrorType label/colour maps x3 in web
- T105 Claude guard misses spelled-out numbers
- T107 evidence ghost == today frames (both tea_no_kettle)
- T108 smoke.sh missing replay routes; not bash -n in ci
- (noted) notify.py + store.py built but not wired into api yet
- T124 mrs-k flagged before live session (beat 4)
- T125 drift/evening/motor residents never watch (baseline absorbs drift)
- T126 session_log leaks across tests; need conftest reset
- T138 AlertContext unused/unstyled, dup of ContextTimeline
- T166/T167/T168 handoff baseline, tuned threshold, push name (merged)
- T204 tour copy: "two in a row" vs 2-in-48h flag rule
- T182 false alarm un-flags -> alert 404, cause re-post fails
- T183 overview/handoff top_pattern unweighted vs alert patterns[0]
- (noted) API resident/handoff payloads have no contracts/ schema; web types hand-mirrored
- T222 alertText says "Change flagged" for trend alerts
- T230 live summary "usually" averages whole history (drift), not early baseline
- T236 live session_end flag/alert_id from scenario verdict, not resident status (alert 404)
- T249 pause mid-session not enforced on /ws/live
- T250 /ws/live messages have no contracts/ schema
- T261 ci.sh/pytest don't force LIVE_API=0
- T271 handoff quiet count includes paused residents
- T272 duplicate scenario README test (tests/ + pipeline/tests/)
- T284 api_* routers do `from . import api` (cycle); move shared state to api_state.py
- (noted) LiveSession room ownership hard-coded to mrs-k; Paused(n) counts rooms not residents
