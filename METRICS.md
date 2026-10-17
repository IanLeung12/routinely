# METRICS (last 6 h, generated 2026-10-17 07:49 UTC)

- **Throughput:** 108/115 claimed tasks merged · 8 active workers · first-try success 89%
- **Friction:** 5 PR CI failures · 7 releases (2 sessions ended early, 2 stale, 3 conflicts) · 4 blocked
- **Main:** 1/143 main CI runs red · 0 reverts
- **Quality signals:** avg task rating None/5 · 21 bug/review tasks filed (all time)
- **Host worker idle (recent log):** w1 0m, w2 63m, w3 3m, w4 0m

## By class
| class | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| light | 69 | 66 | 93 | 2 | 2 | 4 | 5k |
| standard | 34 | 31 | 85 | 1 | 2 | 9 | 55k |
| heavy | 12 | 11 | 75 | 2 | 3 | 20 | 150k |

## By kind
| kind | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| ? | 39 | 39 | 97 | 1 | 0 | 4 | 15k |
| feature | 32 | 30 | 81 | 4 | 3 | 8 | 45k |
| test | 18 | 15 | 83 | 0 | 2 | 5 | 10k |
| improvement | 12 | 11 | 83 | 0 | 2 | 6 | 55k |
| bug | 11 | 10 | 91 | 0 | 0 | 9 | 40k |
| docs | 3 | 3 | 100 | 0 | 0 | 3 | 25k |

## By worker
| worker | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| ian-claude-standard | 31 | 29 | 87 | 2 | 1 | 6 | 55k |
| ian-claude | 17 | 16 | 82 | 2 | 3 | 17 | 150k |
| max-codex-light-2 | 16 | 16 | 100 | 0 | 0 | 4 | 4k |
| ian-claude-standard-2 | 15 | 14 | 87 | 0 | 1 | 5 | 45k |
| max-codex-light-1 | 14 | 14 | 100 | 0 | 0 | 3 | 4k |
| ian-claude-light-2 | 12 | 11 | 92 | 0 | 0 | 4 | 15k |
| ian-claude-light | 7 | 7 | 86 | 1 | 0 | 2 | 15k |
| max_API_light | 3 | 1 | 33 | 0 | 2 | 4 | 4k |

## By area (top 8)
| area | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| pipeline/src/routine_watch | 44 | 42 | 93 | 2 | 2 | 6 | 50k |
| web/src/alert | 13 | 12 | 92 | 0 | 0 | 4 | 35k |
| web/src/live | 10 | 9 | 80 | 1 | 1 | 6 | 45k |
| tests/scenarios | 10 | 9 | 90 | 0 | 0 | 7 | 4k |
| web/src/resident | 9 | 7 | 78 | 0 | 2 | 3 | 4k |
| web/src/evidence | 3 | 3 | 67 | 0 | 1 | 4 | 4k |
| web/src/overview | 3 | 3 | 100 | 0 | 0 | 6 | 24k |
| scripts/smoke.sh | 3 | 3 | 100 | 0 | 0 | 4 | 25k |

## Problem tasks
- T004 (light/?, ian-claude-light): CI×1 — Synthetic care-record generator
- T043 (standard/feature, ian-claude-standard): CI×1 — Live session screen (WebSocket client + mock stream)
- T052 (light/feature, ian-claude-standard): CI×1 blocked — Demo-data banner component
- T041 (heavy/feature, ian-claude): released×1 — Second task: taking medication with water
- T072 (heavy/feature, ian-claude): CI×2 released×2 — Live camera session messages (capture → recogniser → live messages)
- T071 (light/test, max_API_light): released×1 blocked — Tests for useLiveSession and mockLiveStream
- T076 (light/test, max_API_light): released×1 — Tests for ContextTimeline and BaselineChart
- T101 (standard/improvement, ian-claude-standard-2): released×1 — Evidence players: keyboard and screen-reader pass
- T109 (standard/improvement, ian-claude-standard): released×1 — Resident detail: not-found, API-down and no-sessions states
- T096 (light/test, ian-claude-light-2): blocked — Scenario: teabag added three times is perseveration, stirring twice is
- T123 (light/bug, max_API_light): blocked — Bug: smoke.sh always fails the evidence replay check (alert body is ov
