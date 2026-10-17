# METRICS (last 6 h, generated 2026-10-17 21:02 UTC)

- **Throughput:** 95/103 claimed tasks merged · 10 active workers · first-try success 82%
- **Friction:** 1 PR CI failures · 14 releases (8 sessions ended early, 0 stale, 3 conflicts) · 7 blocked
- **Main:** 0/111 main CI runs red · 0 reverts
- **Quality signals:** avg task rating 4.7/5 · 65 bug/review tasks filed (all time)
- **Host worker idle (recent log):** w1 0m, w2 78m, w3 3m, w4 3m, w5 0m, w6 0m, w7 33m

## By class
| class | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| light | 51 | 49 | 86 | 0 | 5 | 17 | 15k |
| standard | 41 | 37 | 80 | 1 | 4 | 14 | 55k |
| heavy | 11 | 9 | 64 | 0 | 5 | 27 | 190k |

## By kind
| kind | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| test | 45 | 45 | 89 | 1 | 5 | 15 | 30k |
| improvement | 32 | 29 | 78 | 0 | 4 | 19 | 45k |
| feature | 16 | 12 | 62 | 0 | 5 | 18 | 125k |
| bug | 8 | 7 | 88 | 0 | 0 | 14 | 50k |
| docs | 2 | 2 | 100 | 0 | 0 | 15 | 10k |

## By worker
| worker | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| ian-claude-light-2 | 20 | 20 | 95 | 0 | 1 | 11 | 25k |
| ian-claude-standard | 19 | 18 | 89 | 0 | 1 | 13 | 45k |
| ian-claude-standard-2 | 19 | 19 | 89 | 1 | 2 | 14 | 55k |
| ian-claude | 11 | 10 | 64 | 0 | 5 | 27 | 120k |
| max_API_light | 10 | 9 | 70 | 0 | 2 | 24 | 5k |
| Max_codex_light | 9 | 8 | 78 | 0 | 1 | 18 | 4k |
| ian-claude-heavy-2 | 6 | 5 | 83 | 0 | 1 | 19 | 85k |
| ian-claude-heavy-3 | 4 | 3 | 75 | 0 | 0 | 22 | 95k |
| max_API_standard | 3 | 2 | 33 | 0 | 1 | 26 | 9k |
| ian-claude-standard-3 | 2 | 1 | 50 | 0 | 0 | 14 | 45k |

## By area (top 8)
| area | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| pipeline/src/routine_watch | 13 | 12 | 77 | 0 | 4 | 23 | 88k |
| web/src/resident | 10 | 10 | 90 | 0 | 1 | 10 | 35k |
| web/src/overview | 9 | 8 | 89 | 0 | 0 | 14 | 35k |
| web/src/live | 7 | 7 | 86 | 0 | 1 | 18 | 45k |
| tests/scenarios | 7 | 7 | 86 | 1 | 1 | 17 | 45k |
| web/src/alert | 6 | 5 | 83 | 0 | 0 | 23 | 30k |
| web/src/handoff | 5 | 5 | 80 | 0 | 1 | 20 | 30k |
| web/src/evidence | 4 | 4 | 75 | 0 | 1 | 31 | 52k |

## Problem tasks
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
- T368 (light/improvement, Max_codex_light): released×1 — Test infra: every web test gets a fake WebSocket by default
- T372 (standard/test, ian-claude-standard-2): released×1 — Test: every error type and pattern is covered by a recorded scenario

## Low task ratings (≤3/5)
- T366 3/5: 3/5 task assumed ErrorState is wired into UnitOverview but it isn't; fetchResidents swallows errors and falls back to mo
