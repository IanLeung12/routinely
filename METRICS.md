# METRICS (last 6 h, generated 2026-10-17 08:50 UTC)

- **Throughput:** 151/156 claimed tasks merged · 8 active workers · first-try success 92%
- **Friction:** 4 PR CI failures · 8 releases (2 sessions ended early, 2 stale, 3 conflicts) · 6 blocked
- **Main:** 1/150 main CI runs red · 0 reverts
- **Quality signals:** avg task rating 4.9/5 · 29 bug/review tasks filed (all time)
- **Host worker idle (recent log):** w1 0m, w2 63m, w3 3m, w4 3m

## By class
| class | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| light | 97 | 96 | 96 | 1 | 3 | 4 | 5k |
| standard | 45 | 41 | 84 | 1 | 2 | 10 | 55k |
| heavy | 14 | 14 | 86 | 2 | 3 | 19 | 150k |

## By kind
| kind | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| feature | 42 | 42 | 90 | 4 | 3 | 6 | 45k |
| ? | 39 | 39 | 100 | 0 | 0 | 4 | 15k |
| test | 28 | 26 | 86 | 0 | 3 | 5 | 15k |
| improvement | 21 | 20 | 86 | 0 | 2 | 6 | 35k |
| bug | 17 | 15 | 88 | 0 | 0 | 8 | 45k |
| docs | 9 | 9 | 100 | 0 | 0 | 4 | 15k |

## By worker
| worker | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| ian-claude-standard | 38 | 36 | 87 | 2 | 1 | 6 | 45k |
| ian-claude-light-2 | 27 | 26 | 93 | 0 | 2 | 4 | 15k |
| ian-claude-standard-2 | 21 | 20 | 90 | 0 | 1 | 8 | 45k |
| ian-claude | 20 | 19 | 85 | 2 | 3 | 17 | 150k |
| max-codex-light-2 | 16 | 16 | 100 | 0 | 0 | 4 | 4k |
| max-codex-light-1 | 14 | 14 | 100 | 0 | 0 | 3 | 4k |
| max_API_light | 13 | 13 | 92 | 0 | 1 | 5 | 4k |
| ian-claude-light | 7 | 7 | 100 | 0 | 0 | 2 | 15k |

## By area (top 8)
| area | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| pipeline/src/routine_watch | 55 | 53 | 95 | 2 | 2 | 6 | 45k |
| web/src/alert | 15 | 14 | 93 | 0 | 0 | 4 | 35k |
| tests/scenarios | 15 | 14 | 93 | 0 | 0 | 8 | 10k |
| web/src/resident | 11 | 11 | 82 | 0 | 2 | 4 | 4k |
| web/src/live | 11 | 11 | 82 | 1 | 2 | 6 | 45k |
| web/src/evidence | 4 | 4 | 75 | 0 | 1 | 6 | 4k |
| web/src/ui | 4 | 4 | 75 | 1 | 0 | 6 | 15k |
| docs/CODEMAP.md | 4 | 4 | 100 | 0 | 0 | 4 | 15k |

## Problem tasks
- T043 (standard/feature, ian-claude-standard): CI×1 — Live session screen (WebSocket client + mock stream)
- T052 (light/feature, ian-claude-standard): CI×1 blocked — Demo-data banner component
- T041 (heavy/feature, ian-claude): released×1 — Second task: taking medication with water
- T072 (heavy/feature, ian-claude): CI×2 released×2 — Live camera session messages (capture → recogniser → live messages)
- T071 (light/test, ian-claude-light-2): released×2 blocked — Tests for useLiveSession and mockLiveStream
- T076 (light/test, max_API_light): released×1 — Tests for ContextTimeline and BaselineChart
- T101 (standard/improvement, ian-claude-standard-2): released×1 — Evidence players: keyboard and screen-reader pass
- T109 (standard/improvement, ian-claude-standard): released×1 — Resident detail: not-found, API-down and no-sessions states
- T096 (light/test, ian-claude-light-2): blocked — Scenario: teabag added three times is perseveration, stirring twice is
- T123 (light/bug, max_API_light): blocked — Bug: smoke.sh always fails the evidence replay check (alert body is ov
- T132 (light/improvement, ian-claude-light-2): blocked — Web tests: AlertView and PatternList time out under default parallelis
- T143 (standard/test, ian-claude-standard): blocked — Pattern scenario: motor slowing after a sedating medication
