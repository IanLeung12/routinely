# METRICS (last 6 h, generated 2026-10-18 01:06 UTC)

- **Throughput:** 67/70 claimed tasks merged · 13 active workers · first-try success 60%
- **Friction:** 8 PR CI failures · 49 releases (38 sessions ended early, 1 stale, 7 conflicts) · 4 blocked
- **Main:** 4/89 main CI runs red · 0 reverts
- **Quality signals:** avg task rating 4.6/5 · 76 bug/review tasks filed (all time)
- **Host worker idle (recent log):** w1 3m, w2 96m, w3 3m, w4 3m, w5 30m, w6 6m, w7 57m, w8 0m

## By class
| class | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| light | 39 | 37 | 59 | 5 | 28 | 27 | 38k |
| standard | 21 | 20 | 48 | 3 | 20 | 34 | 130k |
| heavy | 10 | 10 | 90 | 0 | 1 | 39 | 212k |

## By kind
| kind | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| improvement | 24 | 22 | 50 | 5 | 8 | 34 | 40k |
| feature | 22 | 21 | 68 | 2 | 17 | 36 | 145k |
| bug | 14 | 14 | 57 | 1 | 15 | 30 | 50k |
| test | 8 | 8 | 75 | 0 | 7 | 22 | 9k |
| docs | 2 | 2 | 50 | 0 | 2 | 19 | 35k |

## By worker
| worker | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| ian-claude-standard | 12 | 12 | 50 | 1 | 9 | 28 | 52k |
| ian-claude | 11 | 10 | 64 | 0 | 8 | 32 | 190k |
| ian-claude-heavy-3 | 10 | 9 | 70 | 0 | 3 | 35 | 105k |
| max_API_standard | 8 | 7 | 50 | 1 | 5 | 27 | 12k |
| Max_codex_light | 6 | 6 | 67 | 2 | 1 | 30 | 6k |
| ian-claude-heavy-2 | 5 | 5 | 80 | 0 | 1 | 20 | 90k |
| max_API_light | 5 | 5 | 100 | 0 | 0 | 25 | 4k |
| ian-claude-standard-3 | 4 | 4 | 50 | 1 | 9 | 47 | 130k |
| ian-claude-standard-4 | 4 | 4 | 0 | 1 | 8 | 48 | 102k |
| max_API_standard-2 | 3 | 3 | 33 | 2 | 5 | 58 | 12k |
| ian-claude-standard-2 | 1 | 1 | 100 | 0 | 0 | 14 | 45k |
| ian-claude-light-2 | 1 | 1 | 100 | 0 | 0 | 11 | 15k |

## By area (top 8)
| area | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| pipeline/src/routine_watch | 9 | 9 | 89 | 1 | 1 | 36 | 210k |
| web/src/replays | 6 | 6 | 67 | 0 | 8 | 39 | 28k |
| web/src/live | 4 | 4 | 25 | 0 | 3 | 53 | 168k |
| web/src/resident | 4 | 4 | 50 | 1 | 1 | 38 | 32k |
| web/src/ui | 4 | 4 | 100 | 0 | 0 | 25 | 8k |
| web/src/people | 4 | 4 | 25 | 1 | 3 | 45 | 172k |
| web/src/routines | 4 | 4 | 25 | 0 | 7 | 30 | 85k |
| scripts/integration.sh | 3 | 3 | 100 | 0 | 0 | 22 | 95k |

## Problem tasks
- T392 (standard/test, max_API_standard): released×1 — Test: scripts/camera.sh argument handling (no camera needed)
- T394 (standard/improvement, ian-claude-standard): released×1 — Live: tell the nurse when the camera could not be opened (close code 4
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
