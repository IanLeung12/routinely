# METRICS (last 6 h, generated 2026-10-18 02:07 UTC)

- **Throughput:** 54/55 claimed tasks merged · 11 active workers · first-try success 55%
- **Friction:** 8 PR CI failures · 48 releases (38 sessions ended early, 1 stale, 7 conflicts) · 4 blocked
- **Main:** 4/74 main CI runs red · 0 reverts
- **Quality signals:** avg task rating 4.5/5 · 79 bug/review tasks filed (all time)
- **Host worker idle (recent log):** w1 36m, w2 156m, w3 3m, w4 3m, w5 90m, w6 57m, w7 117m, w8 24m

## By class
| class | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| light | 31 | 31 | 55 | 5 | 28 | 30 | 45k |
| standard | 17 | 16 | 41 | 3 | 19 | 43 | 140k |
| heavy | 7 | 7 | 86 | 0 | 1 | 44 | 215k |

## By kind
| kind | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| feature | 20 | 20 | 65 | 2 | 17 | 40 | 135k |
| improvement | 20 | 20 | 55 | 5 | 7 | 36 | 60k |
| bug | 13 | 12 | 46 | 1 | 16 | 31 | 50k |
| docs | 1 | 1 | 0 | 0 | 2 | 27 | 55k |
| test | 1 | 1 | 0 | 0 | 6 | 30 | 80k |

## By worker
| worker | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| ian-claude-standard | 10 | 10 | 50 | 1 | 8 | 29 | 55k |
| ian-claude | 9 | 9 | 67 | 0 | 8 | 39 | 190k |
| ian-claude-heavy-3 | 8 | 8 | 75 | 0 | 3 | 36 | 148k |
| max_API_standard | 6 | 6 | 50 | 1 | 4 | 27 | 16k |
| Max_codex_light | 5 | 5 | 60 | 2 | 1 | 26 | 6k |
| ian-claude-standard-4 | 5 | 4 | 0 | 1 | 9 | 48 | 102k |
| ian-claude-standard-3 | 4 | 4 | 50 | 1 | 9 | 47 | 130k |
| max_API_light | 3 | 3 | 100 | 0 | 0 | 27 | 6k |
| max_API_standard-2 | 3 | 3 | 33 | 2 | 5 | 58 | 12k |
| ian-claude-heavy-2 | 2 | 2 | 50 | 0 | 1 | 43 | 215k |

## By area (top 8)
| area | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| pipeline/src/routine_watch | 7 | 7 | 86 | 1 | 1 | 42 | 210k |
| web/src/replays | 6 | 6 | 67 | 0 | 8 | 39 | 28k |
| web/src/people | 4 | 4 | 25 | 1 | 3 | 45 | 172k |
| web/src/routines | 4 | 4 | 25 | 0 | 7 | 30 | 85k |
| web/src/live | 3 | 3 | 33 | 0 | 2 | 78 | 290k |
| web/src/ui | 3 | 3 | 100 | 0 | 0 | 25 | 10k |
| web/src/resident | 3 | 3 | 33 | 1 | 1 | 40 | 45k |
| web/src/checkin | 3 | 2 | 0 | 1 | 4 | 60 | 151k |

## Problem tasks
- T408 (heavy/feature, ian-claude-heavy-2): released×1 — Roles: role chooser, role-aware shell, mock people/linking API
- T411 (light/improvement, ian-claude-heavy-3): released×2 — Wording pass: people, not just residents and nurses
- T422 (light/improvement, ian-claude-standard): released×1 — Restyle: HeatCalendar in the Fey palette
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
