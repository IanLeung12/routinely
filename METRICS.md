# METRICS (last 6 h, generated 2026-10-17 20:01 UTC)

- **Throughput:** 102/108 claimed tasks merged · 9 active workers · first-try success 83%
- **Friction:** 2 PR CI failures · 15 releases (9 sessions ended early, 0 stale, 2 conflicts) · 7 blocked
- **Main:** 0/109 main CI runs red · 0 reverts
- **Quality signals:** avg task rating 4.8/5 · 62 bug/review tasks filed (all time)
- **Host worker idle (recent log):** w1 0m, w2 63m, w3 3m, w4 3m, w5 0m, w6 0m

## By class
| class | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| light | 56 | 53 | 82 | 1 | 7 | 16 | 15k |
| standard | 42 | 40 | 88 | 1 | 4 | 13 | 55k |
| heavy | 10 | 9 | 70 | 0 | 4 | 21 | 130k |

## By kind
| kind | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| test | 54 | 52 | 83 | 2 | 7 | 14 | 35k |
| improvement | 33 | 31 | 85 | 0 | 4 | 17 | 55k |
| feature | 12 | 11 | 75 | 0 | 4 | 20 | 125k |
| bug | 5 | 4 | 80 | 0 | 0 | 18 | 45k |
| docs | 4 | 4 | 100 | 0 | 0 | 9 | 15k |

## By worker
| worker | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| ian-claude-light-2 | 25 | 25 | 96 | 0 | 1 | 11 | 25k |
| ian-claude-standard-2 | 23 | 23 | 91 | 1 | 2 | 14 | 55k |
| ian-claude-standard | 20 | 19 | 95 | 0 | 1 | 11 | 45k |
| ian-claude | 14 | 13 | 64 | 1 | 6 | 24 | 105k |
| Max_codex_light | 9 | 8 | 67 | 0 | 2 | 18 | 4k |
| max_API_light | 9 | 8 | 67 | 0 | 2 | 24 | 5k |
| ian-claude-heavy-2 | 5 | 4 | 80 | 0 | 0 | 19 | 85k |
| ian-claude-heavy-3 | 2 | 1 | 50 | 0 | 0 | 21 | 105k |
| max_API_standard | 1 | 1 | 0 | 0 | 1 | 30 | 9k |

## By area (top 8)
| area | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| pipeline/src/routine_watch | 13 | 12 | 77 | 0 | 4 | 21 | 95k |
| web/src/resident | 10 | 9 | 80 | 0 | 1 | 10 | 40k |
| tests/scenarios | 9 | 9 | 89 | 1 | 1 | 13 | 45k |
| web/src/overview | 9 | 9 | 100 | 0 | 0 | 12 | 40k |
| web/src/alert | 7 | 7 | 100 | 0 | 0 | 21 | 45k |
| web/src/handoff | 6 | 6 | 67 | 1 | 2 | 22 | 38k |
| web/src/live | 6 | 5 | 83 | 0 | 1 | 18 | 58k |
| web/src/about | 4 | 4 | 100 | 0 | 0 | 14 | 20k |

## Problem tasks
- T294 (light/test, ian-claude): CI×1 released×1 — Test: shift handoff works keyboard-only
- T187 (light/test, Max_codex_light): released×1 — Test: App shows the live routine picker with tea selected
- T307 (light/test, max_API_light): released×1 — Test: replay player works keyboard-only
- T301 (heavy/improvement, ian-claude): released×1 — Review: contract schema + smoke check for GET /residents/{id}/feedback
- T310 (light/test, ian-claude-light-2): blocked — Test: pattern library urgency filter (every option, reset, empty state
- T314 (standard/test, ian-claude-standard-2): CI×1 released×1 — Scenarios: tea_two_errors_one_session and tea_long_pause_not_error
- T328 (light/test, Max_codex_light): blocked — Test: /ws/live WebSocket routes in api_live.py
- T330 (light/improvement, ian-claude-light-2): released×1 blocked — Heat calendar: usable at phone width (375 px)
- T334 (light/test, max_API_light): released×1 — Test: pattern checks and summaries never use diagnosis wording
- T349 (light/improvement, Max_codex_light): blocked — worker.sh: always disallow Monitor/ScheduleWakeup for claude and re-re
- T341 (light/test, max_API_light): blocked — Test: pattern library urgency filter works keyboard-only
- T356 (heavy/feature, ian-claude): released×3 — Live camera on the dashboard: one command, laptop webcam → /ws/live
- T346 (light/test, ian-claude-light-2): blocked — Test: alert time-of-day strip has accessible names
- T351 (light/bug, ian-claude-light-2): blocked — Review: time-of-day strip and evening pattern use different "evening" 
- T203 (light/feature, ian-claude): released×1 — Shift handoff: print-friendly layout

## Low task ratings (≤3/5)
- T366 3/5: 3/5 task assumed ErrorState is wired into UnitOverview but it isn't; fetchResidents swallows errors and falls back to mo
