# METRICS (last 6 h, generated 2026-10-18 03:08 UTC)

- **Throughput:** 38/41 claimed tasks merged · 11 active workers · first-try success 39%
- **Friction:** 8 PR CI failures · 46 releases (37 sessions ended early, 1 stale, 6 conflicts) · 4 blocked
- **Main:** 4/52 main CI runs red · 0 reverts
- **Quality signals:** avg task rating 4.5/5 · 79 bug/review tasks filed (all time)
- **Host worker idle (recent log):** w1 93m, w2 186m, w3 3m, w4 3m, w5 120m, w6 117m, w7 177m, w8 54m

## By class
| class | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| light | 26 | 24 | 42 | 5 | 27 | 31 | 45k |
| standard | 12 | 11 | 17 | 3 | 19 | 47 | 145k |
| heavy | 3 | 3 | 100 | 0 | 0 | 44 | 250k |

## By kind
| kind | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| feature | 14 | 14 | 57 | 2 | 16 | 43 | 135k |
| improvement | 13 | 13 | 38 | 5 | 6 | 39 | 75k |
| bug | 12 | 9 | 25 | 1 | 16 | 38 | 45k |
| docs | 1 | 1 | 0 | 0 | 2 | 27 | 55k |
| test | 1 | 1 | 0 | 0 | 6 | 30 | 80k |

## By worker
| worker | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| ian-claude | 7 | 7 | 57 | 0 | 8 | 39 | 190k |
| ian-claude-standard | 7 | 6 | 29 | 1 | 7 | 33 | 55k |
| ian-claude-heavy-3 | 6 | 6 | 67 | 0 | 3 | 40 | 148k |
| ian-claude-standard-4 | 5 | 4 | 0 | 1 | 8 | 48 | 102k |
| Max_codex_light | 4 | 4 | 50 | 2 | 1 | 33 | 7k |
| max_API_standard | 4 | 4 | 25 | 1 | 4 | 33 | 18k |
| max_API_standard-2 | 3 | 3 | 33 | 2 | 5 | 58 | 12k |
| max_API_light | 2 | 2 | 100 | 0 | 0 | 37 | 6k |
| ian-claude-standard-3 | 2 | 2 | 0 | 1 | 9 | 47 | 130k |
| ian-claude-heavy-2 | 1 | 0 | 0 | 0 | 1 | – | – |

## By area (top 8)
| area | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| web/src/replays | 6 | 6 | 67 | 0 | 8 | 39 | 28k |
| web/src/routines | 4 | 4 | 25 | 0 | 7 | 30 | 85k |
| web/src/checkin | 4 | 2 | 0 | 1 | 4 | 60 | 151k |
| web/src/people | 3 | 3 | 33 | 1 | 2 | 44 | 130k |
| pipeline/src/routine_watch | 3 | 3 | 67 | 1 | 1 | 54 | 210k |
| web/src/live | 2 | 2 | 0 | 0 | 2 | 87 | 295k |
| web/src/resident | 2 | 2 | 50 | 1 | 0 | 41 | 80k |
| web/src/alert | 1 | 1 | 0 | 0 | 2 | 37 | 190k |

## Problem tasks
- T411 (light/improvement, ian-claude-heavy-3): released×2 — Wording pass: people, not just residents and nurses
- T410 (standard/feature, ian-claude-standard-3): CI×1 — Supervisor side: "People I support" + add a person
- T406 (standard/improvement, ian-claude-standard-4): released×1 — Redesign 6/6: live session + handoff
- T421 (standard/improvement, ian-claude-standard-4): CI×1 — Restyle: BaselineChart + drift card on LineChart
- T436 (light/bug, Max_codex_light): CI×1 released×1 blocked — Review: camera preview MJPEG readable by any website open on the captu
- T433 (light/improvement, ian-claude-standard): CI×1 released×1 blocked — Redesign follow-up: pattern library onto the Fey system
- T438 (standard/feature, ian-claude-standard): released×1 — Routine builder UI: describe it or upload a setup clip → editable task
- T420 (light/improvement, max_API_standard-2): CI×2 blocked — Restyle: overview Sparkline → MicroBars
- T434 (light/improvement, Max_codex_light): CI×1 blocked — Redesign follow-up: guided tour card on the Fey system
- T442 (light/bug, ian-claude): released×1 — Bug: main CI red — first-load JS 336 bytes over bundle budget
- T441 (light/bug, max_API_standard-2): released×5 — Review: deleteReplay reports success when the API refuses the delete
- T435 (light/improvement, max_API_standard): released×1 — Redesign follow-up: privacy panel + monitoring toggle on the Fey syste
- T413 (standard/feature, ian-claude-standard): released×3 — Replays library for supervisors and the person
- T443 (light/bug, ian-claude-heavy-3): released×1 — Review: Routines screen crashes on the live API (GET /routines has no 
- T445 (light/bug, ian-claude-standard-4): released×2 — Bug: flaky unit test MyRoutine "says nobody else can see this…" (lazy 
