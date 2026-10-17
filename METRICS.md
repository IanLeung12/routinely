# METRICS (last 6 h, generated 2026-10-17 09:51 UTC)

- **Throughput:** 180/185 claimed tasks merged · 8 active workers · first-try success 94%
- **Friction:** 2 PR CI failures · 9 releases (3 sessions ended early, 2 stale, 3 conflicts) · 6 blocked
- **Main:** 0/147 main CI runs red · 0 reverts
- **Quality signals:** avg task rating 4.9/5 · 34 bug/review tasks filed (all time)
- **Host worker idle (recent log):** w1 0m, w2 63m, w3 3m, w4 3m

## By class
| class | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| light | 115 | 111 | 95 | 0 | 4 | 4 | 5k |
| standard | 58 | 58 | 97 | 0 | 2 | 9 | 55k |
| heavy | 12 | 11 | 75 | 2 | 3 | 23 | 150k |

## By kind
| kind | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| feature | 51 | 51 | 96 | 2 | 3 | 7 | 45k |
| test | 41 | 40 | 93 | 0 | 3 | 5 | 15k |
| ? | 31 | 31 | 100 | 0 | 0 | 3 | 12k |
| improvement | 27 | 25 | 85 | 0 | 3 | 5 | 18k |
| bug | 23 | 21 | 91 | 0 | 0 | 8 | 75k |
| docs | 12 | 12 | 100 | 0 | 0 | 4 | 15k |

## By worker
| worker | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| ian-claude-standard | 45 | 44 | 96 | 0 | 2 | 7 | 55k |
| ian-claude-light-2 | 38 | 36 | 92 | 0 | 2 | 4 | 15k |
| ian-claude-standard-2 | 28 | 28 | 96 | 0 | 1 | 8 | 45k |
| max_API_light | 21 | 20 | 90 | 0 | 1 | 5 | 4k |
| ian-claude | 20 | 19 | 85 | 2 | 3 | 16 | 140k |
| max-codex-light-2 | 16 | 16 | 100 | 0 | 0 | 4 | 4k |
| max-codex-light-1 | 14 | 14 | 100 | 0 | 0 | 3 | 4k |
| ian-claude-light | 3 | 3 | 100 | 0 | 0 | 2 | 12k |

## By area (top 8)
| area | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| pipeline/src/routine_watch | 57 | 56 | 96 | 2 | 2 | 9 | 55k |
| web/src/alert | 17 | 16 | 94 | 0 | 0 | 4 | 35k |
| tests/scenarios | 17 | 17 | 100 | 0 | 0 | 8 | 10k |
| web/src/live | 15 | 15 | 93 | 0 | 2 | 6 | 30k |
| web/src/resident | 13 | 12 | 77 | 0 | 3 | 4 | 4k |
| web/src/overview | 6 | 6 | 100 | 0 | 0 | 5 | 10k |
| scripts/smoke.sh | 6 | 5 | 83 | 0 | 0 | 4 | 35k |
| web/src/evidence | 5 | 4 | 60 | 0 | 1 | 6 | 4k |

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
