# METRICS (last 6 h, generated 2026-10-18 06:11 UTC)

- **Throughput:** 14/14 claimed tasks merged · 10 active workers · first-try success 86%
- **Friction:** 0 PR CI failures · 3 releases (3 sessions ended early, 0 stale, 0 conflicts) · 0 blocked
- **Main:** 0/27 main CI runs red · 0 reverts
- **Quality signals:** avg task rating 4.6/5 · 81 bug/review tasks filed (all time)
- **Host worker idle (recent log):** w1 138m, w2 243m, w3 3m, w4 3m, w5 126m, w6 231m, w7 192m, w8 87m

## By class
| class | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| light | 9 | 9 | 100 | 0 | 0 | 28 | 75k |
| standard | 4 | 4 | 50 | 0 | 3 | 38 | 215k |
| heavy | 1 | 1 | 100 | 0 | 0 | 51 | 345k |

## By kind
| kind | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| bug | 9 | 9 | 89 | 0 | 1 | 28 | 80k |
| feature | 3 | 3 | 67 | 0 | 2 | 39 | 230k |
| improvement | 2 | 2 | 100 | 0 | 0 | 29 | 138k |

## By worker
| worker | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| ian-claude-standard | 4 | 4 | 100 | 0 | 0 | 34 | 65k |
| ian-claude-heavy-3 | 3 | 3 | 100 | 0 | 0 | 18 | 95k |
| ian-claude-heavy-2 | 2 | 2 | 50 | 0 | 1 | 75 | 182k |
| max_API_standard | 1 | 1 | 0 | 0 | 2 | 39 | 22k |
| max_API_light | 1 | 1 | 100 | 0 | 0 | 27 | 6k |
| ian-claude | 1 | 1 | 100 | 0 | 0 | 39 | 200k |
| ian-claude-standard-4 | 1 | 1 | 100 | 0 | 0 | 41 | 95k |
| ian-claude-standard-3 | 1 | 1 | 100 | 0 | 0 | 28 | 35k |

## By area (top 8)
| area | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| web/src/checkin | 4 | 4 | 50 | 0 | 3 | 40 | 95k |
| pipeline/src/routine_watch | 3 | 3 | 100 | 0 | 0 | 38 | 230k |
| web/src/App.tsx | 1 | 1 | 100 | 0 | 0 | 18 | 75k |
| web/src/routines | 1 | 1 | 100 | 0 | 0 | 27 | 6k |
| web/src/replays | 1 | 1 | 100 | 0 | 0 | 31 | 55k |
| scripts/kaze_demo.py | 1 | 1 | 100 | 0 | 0 | 39 | 200k |
| web/src/testSetup.ts | 1 | 1 | 100 | 0 | 0 | 64 | 65k |
| scripts/dev.sh | 1 | 1 | 100 | 0 | 0 | 28 | 35k |

## Problem tasks
- T452 (standard/feature, max_API_standard): released×2 — Supervisor alarm UI: alarm banner + sound, acknowledge, escalation tim
- T457 (standard/bug, ian-claude-heavy-2): released×1 — Bug: supervisor alarm UI (T452) doesn't speak the real check-in API (T
