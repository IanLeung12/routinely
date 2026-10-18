# METRICS (last 6 h, generated 2026-10-18 00:05 UTC)

- **Throughput:** 74/81 claimed tasks merged · 13 active workers · first-try success 64%
- **Friction:** 7 PR CI failures · 41 releases (30 sessions ended early, 1 stale, 7 conflicts) · 4 blocked
- **Main:** 4/99 main CI runs red · 0 reverts
- **Quality signals:** avg task rating 4.6/5 · 73 bug/review tasks filed (all time)
- **Host worker idle (recent log):** w1 3m, w2 87m, w3 3m, w4 3m, w5 0m, w6 6m, w7 36m, w8 0m

## By class
| class | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| light | 44 | 42 | 64 | 5 | 27 | 25 | 32k |
| standard | 26 | 22 | 58 | 2 | 13 | 27 | 85k |
| heavy | 11 | 10 | 82 | 0 | 1 | 32 | 210k |

## By kind
| kind | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| improvement | 30 | 29 | 63 | 5 | 8 | 27 | 40k |
| feature | 24 | 20 | 67 | 1 | 11 | 28 | 130k |
| test | 12 | 11 | 75 | 0 | 8 | 21 | 35k |
| bug | 12 | 11 | 50 | 1 | 12 | 29 | 55k |
| docs | 3 | 3 | 67 | 0 | 2 | 19 | 15k |

## By worker
| worker | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| ian-claude-standard | 13 | 12 | 54 | 1 | 9 | 26 | 55k |
| ian-claude | 10 | 9 | 70 | 0 | 8 | 30 | 165k |
| ian-claude-heavy-3 | 9 | 8 | 67 | 0 | 3 | 33 | 105k |
| Max_codex_light | 8 | 8 | 62 | 2 | 2 | 30 | 6k |
| ian-claude-heavy-2 | 8 | 7 | 75 | 0 | 1 | 20 | 110k |
| max_API_light | 6 | 5 | 83 | 0 | 2 | 24 | 4k |
| max_API_standard | 6 | 6 | 67 | 0 | 2 | 27 | 10k |
| ian-claude-light-2 | 5 | 5 | 100 | 0 | 0 | 12 | 30k |
| ian-claude-standard-2 | 5 | 5 | 80 | 0 | 1 | 17 | 55k |
| ian-claude-standard-4 | 5 | 4 | 0 | 1 | 8 | 48 | 102k |
| ian-claude-standard-3 | 3 | 3 | 67 | 1 | 0 | 47 | 130k |
| max_API_standard-2 | 3 | 2 | 33 | 2 | 5 | 40 | 16k |

## By area (top 8)
| area | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| pipeline/src/routine_watch | 10 | 9 | 80 | 1 | 1 | 28 | 190k |
| web/src/overview | 5 | 5 | 80 | 2 | 0 | 18 | 55k |
| web/src/live | 5 | 4 | 40 | 0 | 2 | 23 | 80k |
| web/src/replays | 5 | 3 | 60 | 0 | 5 | 26 | 28k |
| web/src/handoff | 4 | 4 | 75 | 0 | 1 | 25 | 17k |
| web/src/alert | 4 | 4 | 75 | 0 | 2 | 29 | 110k |
| web/src/resident | 4 | 4 | 50 | 1 | 1 | 38 | 32k |
| web/src/ui | 4 | 4 | 100 | 0 | 0 | 25 | 8k |

## Problem tasks
- T203 (light/feature, ian-claude): released×1 — Shift handoff: print-friendly layout
- T368 (light/improvement, Max_codex_light): released×1 — Test infra: every web test gets a fake WebSocket by default
- T372 (standard/test, ian-claude-standard-2): released×1 — Test: every error type and pattern is covered by a recorded scenario
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

## Low task ratings (≤3/5)
- T366 3/5: 3/5 task assumed ErrorState is wired into UnitOverview but it isn't; fetchResidents swallows errors and falls back to mo
