# METRICS (last 6 h, generated 2026-10-17 23:04 UTC)

- **Throughput:** 88/93 claimed tasks merged · 13 active workers · first-try success 76%
- **Friction:** 7 PR CI failures · 18 releases (9 sessions ended early, 0 stale, 6 conflicts) · 8 blocked
- **Main:** 4/111 main CI runs red · 0 reverts
- **Quality signals:** avg task rating 4.7/5 · 73 bug/review tasks filed (all time)
- **Host worker idle (recent log):** w1 3m, w2 84m, w3 3m, w4 3m, w5 0m, w6 6m, w7 36m, w8 0m

## By class
| class | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| light | 51 | 48 | 76 | 5 | 8 | 24 | 14k |
| standard | 31 | 29 | 74 | 2 | 6 | 23 | 55k |
| heavy | 11 | 11 | 82 | 0 | 4 | 36 | 210k |

## By kind
| kind | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| improvement | 34 | 33 | 74 | 5 | 6 | 25 | 32k |
| test | 23 | 23 | 91 | 0 | 2 | 18 | 28k |
| feature | 22 | 21 | 73 | 1 | 7 | 28 | 130k |
| bug | 12 | 9 | 58 | 1 | 3 | 27 | 45k |
| docs | 2 | 2 | 100 | 0 | 0 | 15 | 10k |

## By worker
| worker | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| ian-claude-standard | 16 | 15 | 69 | 1 | 4 | 18 | 48k |
| ian-claude-light-2 | 11 | 11 | 100 | 0 | 0 | 12 | 25k |
| Max_codex_light | 10 | 10 | 70 | 2 | 2 | 29 | 6k |
| ian-claude | 10 | 10 | 70 | 0 | 5 | 28 | 190k |
| ian-claude-standard-2 | 9 | 9 | 89 | 0 | 1 | 17 | 55k |
| max_API_light | 8 | 8 | 100 | 0 | 0 | 24 | 4k |
| ian-claude-heavy-2 | 7 | 7 | 86 | 0 | 1 | 20 | 90k |
| ian-claude-heavy-3 | 7 | 6 | 86 | 0 | 1 | 31 | 100k |
| max_API_standard | 6 | 6 | 67 | 0 | 2 | 27 | 10k |
| ian-claude-standard-3 | 4 | 3 | 50 | 1 | 1 | 47 | 130k |
| ian-claude-standard-4 | 2 | 1 | 0 | 1 | 1 | 58 | 220k |
| max_API_standard-2 | 2 | 2 | 50 | 2 | 0 | 40 | 16k |
| ian-laptop-standard | 1 | 0 | 0 | 0 | 0 | – | – |

## By area (top 8)
| area | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| pipeline/src/routine_watch | 11 | 11 | 82 | 1 | 4 | 36 | 190k |
| web/src/overview | 7 | 7 | 86 | 2 | 0 | 18 | 35k |
| web/src/resident | 6 | 6 | 67 | 1 | 1 | 29 | 38k |
| tests/scenarios | 5 | 5 | 100 | 0 | 0 | 17 | 45k |
| web/src/handoff | 5 | 5 | 80 | 0 | 1 | 24 | 30k |
| web/src/live | 5 | 4 | 60 | 0 | 2 | 23 | 45k |
| web/src/replays | 5 | 3 | 60 | 0 | 1 | 26 | 28k |
| web/src/alert | 4 | 4 | 100 | 0 | 0 | 28 | 28k |

## Problem tasks
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
- T410 (standard/feature, ian-claude-standard-3): CI×1 — Supervisor side: "People I support" + add a person
- T406 (standard/improvement, ian-claude-standard-4): released×1 — Redesign 6/6: live session + handoff
- T421 (standard/improvement, ian-claude-standard-4): CI×1 — Restyle: BaselineChart + drift card on LineChart

## Low task ratings (≤3/5)
- T366 3/5: 3/5 task assumed ErrorState is wired into UnitOverview but it isn't; fetchResidents swallows errors and falls back to mo
