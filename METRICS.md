# METRICS (last 6 h, generated 2026-10-17 22:03 UTC)

- **Throughput:** 95/103 claimed tasks merged · 11 active workers · first-try success 83%
- **Friction:** 0 PR CI failures · 12 releases (7 sessions ended early, 0 stale, 3 conflicts) · 6 blocked
- **Main:** 1/115 main CI runs red · 0 reverts
- **Quality signals:** avg task rating 4.7/5 · 67 bug/review tasks filed (all time)
- **Host worker idle (recent log):** w1 0m, w2 78m, w3 3m, w4 3m, w5 0m, w6 0m, w7 33m, w8 0m

## By class
| class | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| light | 54 | 50 | 83 | 0 | 5 | 19 | 15k |
| standard | 37 | 34 | 84 | 0 | 3 | 17 | 55k |
| heavy | 12 | 11 | 75 | 0 | 4 | 28 | 212k |

## By kind
| kind | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| improvement | 36 | 33 | 81 | 0 | 4 | 23 | 40k |
| test | 34 | 34 | 91 | 0 | 3 | 16 | 25k |
| feature | 22 | 18 | 68 | 0 | 5 | 27 | 125k |
| bug | 9 | 8 | 89 | 0 | 0 | 18 | 55k |
| docs | 2 | 2 | 100 | 0 | 0 | 15 | 10k |

## By worker
| worker | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| ian-claude-light-2 | 17 | 17 | 94 | 0 | 1 | 12 | 25k |
| ian-claude-standard | 16 | 15 | 81 | 0 | 2 | 17 | 45k |
| ian-claude-standard-2 | 14 | 14 | 93 | 0 | 1 | 14 | 50k |
| ian-claude | 11 | 11 | 82 | 0 | 4 | 27 | 190k |
| max_API_light | 11 | 10 | 82 | 0 | 1 | 24 | 5k |
| Max_codex_light | 11 | 10 | 82 | 0 | 1 | 22 | 4k |
| ian-claude-heavy-2 | 8 | 7 | 75 | 0 | 1 | 20 | 90k |
| max_API_standard | 6 | 5 | 67 | 0 | 1 | 27 | 9k |
| ian-claude-heavy-3 | 5 | 4 | 80 | 0 | 0 | 24 | 105k |
| ian-claude-standard-3 | 3 | 2 | 67 | 0 | 0 | 38 | 192k |
| ian-claude-standard-4 | 1 | 0 | 0 | 0 | 0 | – | – |

## By area (top 8)
| area | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| pipeline/src/routine_watch | 13 | 12 | 85 | 0 | 3 | 26 | 120k |
| web/src/overview | 9 | 9 | 100 | 0 | 0 | 16 | 45k |
| web/src/resident | 9 | 8 | 67 | 0 | 2 | 15 | 22k |
| web/src/handoff | 6 | 6 | 83 | 0 | 1 | 22 | 30k |
| web/src/live | 6 | 5 | 67 | 0 | 1 | 20 | 35k |
| web/src/alert | 5 | 5 | 100 | 0 | 0 | 27 | 30k |
| tests/scenarios | 5 | 5 | 100 | 0 | 0 | 17 | 45k |
| web/src/ui | 4 | 4 | 100 | 0 | 0 | 25 | 8k |

## Problem tasks
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
- T392 (standard/test, max_API_standard): released×1 — Test: scripts/camera.sh argument handling (no camera needed)
- T394 (standard/improvement, ian-claude-standard): released×1 — Live: tell the nurse when the camera could not be opened (close code 4
- T408 (heavy/feature, ian-claude-heavy-2): released×1 — Roles: role chooser, role-aware shell, mock people/linking API
- T422 (light/improvement, ian-claude-standard): released×1 — Restyle: HeatCalendar in the Fey palette

## Low task ratings (≤3/5)
- T366 3/5: 3/5 task assumed ErrorState is wired into UnitOverview but it isn't; fetchResidents swallows errors and falls back to mo
