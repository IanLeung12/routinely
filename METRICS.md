# METRICS (last 6 h, generated 2026-10-18 05:10 UTC)

- **Throughput:** 23/23 claimed tasks merged · 10 active workers · first-try success 61%
- **Friction:** 1 PR CI failures · 29 releases (27 sessions ended early, 0 stale, 2 conflicts) · 0 blocked
- **Main:** 0/36 main CI runs red · 0 reverts
- **Quality signals:** avg task rating 4.6/5 · 81 bug/review tasks filed (all time)
- **Host worker idle (recent log):** w1 138m, w2 201m, w3 3m, w4 3m, w5 126m, w6 171m, w7 192m, w8 87m

## By class
| class | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| light | 14 | 14 | 71 | 0 | 15 | 29 | 78k |
| standard | 7 | 7 | 29 | 1 | 14 | 47 | 222k |
| heavy | 2 | 2 | 100 | 0 | 0 | 55 | 302k |

## By kind
| kind | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| bug | 10 | 10 | 80 | 0 | 6 | 29 | 65k |
| feature | 7 | 7 | 57 | 1 | 12 | 47 | 230k |
| improvement | 4 | 4 | 50 | 0 | 3 | 38 | 195k |
| docs | 1 | 1 | 0 | 0 | 2 | 27 | 55k |
| test | 1 | 1 | 0 | 0 | 6 | 30 | 80k |

## By worker
| worker | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| ian-claude-heavy-3 | 5 | 5 | 80 | 0 | 2 | 37 | 190k |
| ian-claude-standard | 5 | 5 | 80 | 0 | 2 | 31 | 60k |
| ian-claude | 4 | 4 | 50 | 0 | 7 | 35 | 170k |
| ian-claude-standard-4 | 2 | 2 | 50 | 0 | 5 | 35 | 80k |
| max_API_standard | 2 | 2 | 0 | 1 | 3 | 60 | 151k |
| ian-claude-standard-3 | 2 | 2 | 50 | 0 | 9 | 38 | 82k |
| ian-claude-heavy-2 | 2 | 2 | 50 | 0 | 1 | 75 | 182k |
| max_API_light | 1 | 1 | 100 | 0 | 0 | 27 | 6k |

## By area (top 8)
| area | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| web/src/checkin | 5 | 5 | 40 | 1 | 4 | 41 | 95k |
| pipeline/src/routine_watch | 4 | 4 | 100 | 0 | 0 | 44 | 245k |
| web/src/routines | 2 | 2 | 50 | 0 | 5 | 28 | 36k |
| web/src/alert | 1 | 1 | 0 | 0 | 2 | 37 | 190k |
| web/src/live | 1 | 1 | 0 | 0 | 1 | 78 | 290k |
| web/src/evidence | 1 | 1 | 100 | 0 | 0 | 30 | 140k |
| docs/DEMO.md | 1 | 1 | 0 | 0 | 2 | 27 | 55k |
| scripts/smoke.sh | 1 | 1 | 0 | 0 | 6 | 30 | 80k |

## Problem tasks
- T411 (light/improvement, ian-claude-heavy-3): released×2 — Wording pass: people, not just residents and nurses
- T432 (standard/improvement, ian-claude): released×1 — Task map as a Postman Flows–style node graph
- T447 (light/docs, ian-claude-standard): released×2 — DEMO.md: click path for the new screens (people, My routine, routine b
- T444 (light/bug, ian-claude-standard-4): released×5 — Review: routine builder shows a canned draft / fake save when the API 
- T448 (light/test, ian-claude): released×6 — Smoke: check the routines and replays endpoints
- T451 (standard/feature, max_API_standard): CI×1 released×1 — Check-in UI (person side): countdown, "I'm okay" + PIN pad
- T454 (standard/feature, ian-claude-standard-3): released×9 — Impact evaluation on synthetic data: catch rate, false alarms, hours e
- T452 (standard/feature, max_API_standard): released×2 — Supervisor alarm UI: alarm banner + sound, acknowledge, escalation tim
- T457 (standard/bug, ian-claude-heavy-2): released×1 — Bug: supervisor alarm UI (T452) doesn't speak the real check-in API (T
