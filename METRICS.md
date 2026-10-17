# METRICS (last 6 h, generated 2026-10-17 10:52 UTC)

- **Throughput:** 189/196 claimed tasks merged · 7 active workers · first-try success 92%
- **Friction:** 3 PR CI failures · 11 releases (5 sessions ended early, 2 stale, 3 conflicts) · 6 blocked
- **Main:** 2/158 main CI runs red · 0 reverts
- **Quality signals:** avg task rating 4.9/5 · 39 bug/review tasks filed (all time)
- **Host worker idle (recent log):** w1 0m, w2 63m, w3 3m, w4 3m

## By class
| class | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| light | 126 | 120 | 92 | 1 | 5 | 4 | 15k |
| standard | 60 | 59 | 95 | 0 | 3 | 10 | 65k |
| heavy | 10 | 10 | 80 | 2 | 3 | 20 | 150k |

## By kind
| kind | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| feature | 55 | 53 | 93 | 2 | 4 | 7 | 45k |
| test | 47 | 45 | 91 | 0 | 3 | 5 | 15k |
| improvement | 38 | 37 | 87 | 0 | 4 | 6 | 15k |
| bug | 29 | 27 | 93 | 1 | 0 | 10 | 75k |
| ? | 15 | 15 | 100 | 0 | 0 | 3 | 4k |
| docs | 12 | 12 | 100 | 0 | 0 | 4 | 15k |

## By worker
| worker | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| ian-claude-light-2 | 50 | 47 | 92 | 1 | 2 | 4 | 15k |
| ian-claude-standard | 43 | 42 | 93 | 0 | 2 | 8 | 55k |
| ian-claude-standard-2 | 33 | 32 | 94 | 0 | 2 | 8 | 55k |
| ian-claude | 21 | 20 | 81 | 2 | 4 | 17 | 120k |
| max_API_light | 21 | 20 | 90 | 0 | 1 | 5 | 4k |
| max-codex-light-2 | 15 | 15 | 100 | 0 | 0 | 4 | 3k |
| max-codex-light-1 | 13 | 13 | 100 | 0 | 0 | 3 | 4k |

## By area (top 8)
| area | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| pipeline/src/routine_watch | 52 | 51 | 96 | 2 | 3 | 11 | 65k |
| web/src/alert | 21 | 19 | 86 | 0 | 1 | 6 | 45k |
| web/src/live | 19 | 18 | 89 | 1 | 2 | 7 | 15k |
| tests/scenarios | 19 | 19 | 100 | 0 | 0 | 8 | 15k |
| web/src/resident | 14 | 14 | 79 | 0 | 3 | 5 | 5k |
| web/src/ui | 7 | 7 | 100 | 0 | 0 | 5 | 30k |
| web/src/evidence | 6 | 5 | 67 | 0 | 1 | 5 | 4k |
| web/src/overview | 6 | 6 | 100 | 0 | 0 | 5 | 10k |

## Problem tasks
- T052 (light/feature, ian-claude-standard): blocked — Demo-data banner component
- T041 (heavy/feature, ian-claude): released×1 — Second task: taking medication with water
- T072 (heavy/feature, ian-claude): CI×2 released×2 — Live camera session messages (capture → recogniser → live messages)
- T071 (light/test, ian-claude-light-2): released×2 blocked — Tests for useLiveSession and mockLiveStream
- T076 (light/test, max_API_light): released×1 — Tests for ContextTimeline and BaselineChart
- T101 (standard/improvement, ian-claude-standard-2): released×1 — Evidence players: keyboard and screen-reader pass
- T109 (standard/improvement, ian-claude-standard): released×1 — Resident detail: not-found, API-down and no-sessions states
- T096 (light/test, ian-claude-light-2): blocked — Scenario: teabag added three times is perseveration, stirring twice is
- T123 (light/bug, max_API_light): blocked — Bug: smoke.sh always fails the evidence replay check (alert body is ov
- T132 (light/improvement, ian-claude-light-2): blocked — Web tests: AlertView and PatternList time out under default parallelis
- T143 (standard/test, ian-claude-standard-2): blocked — Pattern scenario: motor slowing after a sedating medication
- T197 (light/improvement, ian-claude-standard): released×1 — Heat calendar legend: CSS classes instead of inline styles
- T221 (light/improvement, ian-claude): released×1 — Copy summary uses the resident's real name, not one guessed from the i
- T220 (light/bug, ian-claude-light-2): CI×1 — Live screen: settle on session_end's final error list
- T149 (standard/feature, ian-claude-standard-2): released×1 — API: GET /monitoring and PUT /rooms/{room}/monitoring
