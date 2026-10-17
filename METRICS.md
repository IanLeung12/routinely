# METRICS (last 6 h, generated 2026-10-17 19:00 UTC)

- **Throughput:** 97/105 claimed tasks merged · 7 active workers · first-try success 83%
- **Friction:** 2 PR CI failures · 16 releases (11 sessions ended early, 0 stale, 2 conflicts) · 7 blocked
- **Main:** 0/105 main CI runs red · 0 reverts
- **Quality signals:** avg task rating 4.8/5 · 60 bug/review tasks filed (all time)
- **Host worker idle (recent log):** w1 0m, w2 63m, w3 3m, w4 3m, w5 0m

## By class
| class | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| light | 53 | 48 | 77 | 1 | 9 | 15 | 18k |
| standard | 43 | 41 | 91 | 1 | 3 | 12 | 55k |
| heavy | 9 | 8 | 78 | 0 | 4 | 18 | 130k |

## By kind
| kind | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| test | 53 | 51 | 87 | 2 | 6 | 13 | 42k |
| improvement | 32 | 28 | 78 | 0 | 4 | 17 | 58k |
| feature | 13 | 12 | 77 | 0 | 6 | 16 | 60k |
| bug | 4 | 3 | 75 | 0 | 0 | 14 | 105k |
| docs | 3 | 3 | 100 | 0 | 0 | 7 | 10k |

## By worker
| worker | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| ian-claude-light-2 | 25 | 24 | 88 | 0 | 3 | 11 | 25k |
| ian-claude-standard | 24 | 23 | 92 | 0 | 1 | 10 | 50k |
| ian-claude-standard-2 | 24 | 23 | 92 | 1 | 2 | 13 | 55k |
| ian-claude | 15 | 14 | 73 | 1 | 6 | 19 | 110k |
| Max_codex_light | 9 | 7 | 67 | 0 | 2 | 17 | 4k |
| max_API_light | 7 | 6 | 57 | 0 | 2 | 30 | 5k |
| ian-claude-heavy-2 | 1 | 0 | 0 | 0 | 0 | – | 80k |

## By area (top 8)
| area | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| web/src/overview | 11 | 10 | 82 | 0 | 2 | 11 | 40k |
| pipeline/src/routine_watch | 11 | 9 | 73 | 0 | 4 | 17 | 95k |
| tests/scenarios | 9 | 9 | 89 | 1 | 1 | 13 | 45k |
| web/src/resident | 9 | 9 | 89 | 0 | 1 | 10 | 40k |
| web/src/handoff | 7 | 7 | 71 | 1 | 2 | 20 | 60k |
| web/src/alert | 7 | 5 | 71 | 0 | 0 | 21 | 55k |
| web/src/about | 5 | 5 | 80 | 0 | 1 | 16 | 25k |
| web/src/live | 5 | 4 | 80 | 0 | 0 | 18 | 80k |

## Problem tasks
- T255 (light/feature, ian-claude-light-2): released×2 — Resident detail: show who consented to monitoring
- T275 (standard/improvement, ian-claude-standard): released×1 — Live screen: notice a pause/resume made while the panel is open
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

## Low task ratings (≤3/5)
- T366 3/5: 3/5 task assumed ErrorState is wired into UnitOverview but it isn't; fetchResidents swallows errors and falls back to mo
