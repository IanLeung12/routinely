# METRICS (last 6 h, generated 2026-10-18 04:09 UTC)

- **Throughput:** 27/28 claimed tasks merged · 11 active workers · first-try success 43%
- **Friction:** 1 PR CI failures · 42 releases (37 sessions ended early, 1 stale, 4 conflicts) · 0 blocked
- **Main:** 2/48 main CI runs red · 0 reverts
- **Quality signals:** avg task rating 4.5/5 · 80 bug/review tasks filed (all time)
- **Host worker idle (recent log):** w1 138m, w2 195m, w3 3m, w4 3m, w5 126m, w6 126m, w7 192m, w8 87m

## By class
| class | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| light | 18 | 18 | 50 | 0 | 25 | 30 | 65k |
| standard | 8 | 8 | 25 | 1 | 17 | 63 | 172k |
| heavy | 2 | 1 | 50 | 0 | 0 | 60 | 302k |

## By kind
| kind | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| bug | 13 | 13 | 54 | 0 | 15 | 32 | 60k |
| feature | 7 | 6 | 29 | 1 | 15 | 53 | 200k |
| improvement | 6 | 6 | 50 | 0 | 4 | 32 | 132k |
| docs | 1 | 1 | 0 | 0 | 2 | 27 | 55k |
| test | 1 | 1 | 0 | 0 | 6 | 30 | 80k |

## By worker
| worker | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| ian-claude-heavy-3 | 5 | 4 | 40 | 0 | 3 | 34 | 190k |
| ian-claude | 5 | 5 | 40 | 0 | 8 | 39 | 140k |
| ian-claude-standard | 5 | 5 | 60 | 0 | 5 | 31 | 55k |
| max_API_standard | 3 | 3 | 0 | 1 | 4 | 39 | 22k |
| ian-claude-standard-4 | 3 | 3 | 33 | 0 | 7 | 38 | 65k |
| max_API_standard-2 | 2 | 2 | 50 | 0 | 5 | 82 | 14k |
| ian-claude-standard-3 | 2 | 2 | 50 | 0 | 9 | 38 | 82k |
| ian-claude-heavy-2 | 2 | 2 | 50 | 0 | 1 | 75 | 182k |
| max_API_light | 1 | 1 | 100 | 0 | 0 | 27 | 6k |

## By area (top 8)
| area | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| web/src/checkin | 4 | 4 | 25 | 1 | 4 | 61 | 155k |
| web/src/replays | 3 | 3 | 33 | 0 | 8 | 103 | 31k |
| web/src/routines | 3 | 3 | 33 | 0 | 6 | 29 | 65k |
| pipeline/src/routine_watch | 3 | 2 | 67 | 0 | 0 | 43 | 260k |
| web/src/people | 2 | 2 | 50 | 0 | 2 | 26 | 40k |
| web/src/alert | 1 | 1 | 0 | 0 | 2 | 37 | 190k |
| web/scripts/check-bundle.mjs | 1 | 1 | 0 | 0 | 1 | 55 | 45k |
| web/src/about | 1 | 1 | 0 | 0 | 1 | 28 | 14k |

## Problem tasks
- T411 (light/improvement, ian-claude-heavy-3): released×2 — Wording pass: people, not just residents and nurses
- T442 (light/bug, ian-claude): released×1 — Bug: main CI red — first-load JS 336 bytes over bundle budget
- T441 (light/bug, max_API_standard-2): released×5 — Review: deleteReplay reports success when the API refuses the delete
- T435 (light/improvement, max_API_standard): released×1 — Redesign follow-up: privacy panel + monitoring toggle on the Fey syste
- T413 (standard/feature, ian-claude-standard): released×3 — Replays library for supervisors and the person
- T443 (light/bug, ian-claude-heavy-3): released×1 — Review: Routines screen crashes on the live API (GET /routines has no 
- T445 (light/bug, ian-claude-standard-4): released×2 — Bug: flaky unit test MyRoutine "says nobody else can see this…" (lazy 
- T432 (standard/improvement, ian-claude): released×1 — Task map as a Postman Flows–style node graph
- T447 (light/docs, ian-claude-standard): released×2 — DEMO.md: click path for the new screens (people, My routine, routine b
- T444 (light/bug, ian-claude-standard-4): released×5 — Review: routine builder shows a canned draft / fake save when the API 
- T448 (light/test, ian-claude): released×6 — Smoke: check the routines and replays endpoints
- T451 (standard/feature, max_API_standard): CI×1 released×1 — Check-in UI (person side): countdown, "I'm okay" + PIN pad
- T454 (standard/feature, ian-claude-standard-3): released×9 — Impact evaluation on synthetic data: catch rate, false alarms, hours e
- T452 (standard/feature, max_API_standard): released×2 — Supervisor alarm UI: alarm banner + sound, acknowledge, escalation tim
- T457 (standard/bug, ian-claude-heavy-2): released×1 — Bug: supervisor alarm UI (T452) doesn't speak the real check-in API (T
