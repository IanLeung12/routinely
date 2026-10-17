# REVIEW

- last-reviewed: 56f927e
- next-area: pipeline

## Known issues filed
- T047 flaky web CI (App.test.tsx async)
- T048 heat calendar dark-theme contrast
- T053 postFeedback swallows non-ok API responses into mock
- T054 TaskMap/SkeletonView hard-coded light colours
- T055 scoring duplicated replay.py/live.py; empty-scenario IndexError
- T073 live screen uses MOCK_STEPS; no session_start with task graph
- T074 assisted = any single 2-pose frame
- T075 ErrorType label/colour maps x3 in web
- T105 Claude guard misses spelled-out numbers
- (noted) cause picker not wired to API/contract yet (T100 is store half); verifier.resolve unused until live capture
- T107 evidence ghost == today frames (both tea_no_kettle)
- T108 smoke.sh missing replay routes; not bash -n in ci
- (noted) notify.py + store.py built but not wired into api yet
- T124 mrs-k flagged before live session (beat 4)
- T125 drift/evening/motor residents never watch (baseline absorbs drift)
- T126 session_log leaks across tests; need conftest reset
- T138 AlertContext unused/unstyled, dup of ContextTimeline
