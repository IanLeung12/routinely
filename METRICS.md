# METRICS (last 6 h, generated 2026-10-17 11:53 UTC)

- **Throughput:** 169/173 claimed tasks merged · 7 active workers · first-try success 91%
- **Friction:** 1 PR CI failures · 15 releases (8 sessions ended early, 3 stale, 3 conflicts) · 5 blocked
- **Main:** 2/151 main CI runs red · 0 reverts
- **Quality signals:** avg task rating 4.8/5 · 43 bug/review tasks filed (all time)
- **Host worker idle (recent log):** w1 0m, w2 63m, w3 3m, w4 3m

## By class
| class | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| light | 105 | 103 | 90 | 1 | 9 | 5 | 15k |
| standard | 61 | 59 | 92 | 0 | 4 | 11 | 65k |
| heavy | 7 | 7 | 86 | 0 | 2 | 18 | 150k |

## By kind
| kind | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| test | 45 | 45 | 91 | 0 | 5 | 5 | 25k |
| feature | 42 | 42 | 93 | 0 | 4 | 7 | 50k |
| improvement | 41 | 38 | 83 | 0 | 6 | 6 | 32k |
| bug | 34 | 33 | 94 | 1 | 0 | 11 | 80k |
| docs | 11 | 11 | 100 | 0 | 0 | 4 | 15k |

## By worker
| worker | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| ian-claude-light-2 | 56 | 54 | 88 | 1 | 6 | 4 | 15k |
| ian-claude-standard | 37 | 36 | 89 | 0 | 4 | 8 | 55k |
| ian-claude-standard-2 | 36 | 35 | 94 | 0 | 1 | 8 | 55k |
| ian-claude | 21 | 21 | 90 | 0 | 3 | 16 | 105k |
| max_API_light | 20 | 20 | 95 | 0 | 1 | 5 | 4k |
| max-codex-light-2 | 2 | 2 | 100 | 0 | 0 | 28 | 4k |
| max-codex-light-1 | 1 | 1 | 100 | 0 | 0 | 41 | 4k |

## By area (top 8)
| area | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| pipeline/src/routine_watch | 47 | 46 | 94 | 0 | 3 | 12 | 70k |
| web/src/alert | 19 | 18 | 89 | 0 | 1 | 7 | 45k |
| web/src/live | 17 | 16 | 82 | 1 | 3 | 9 | 42k |
| tests/scenarios | 14 | 14 | 100 | 0 | 0 | 8 | 30k |
| web/src/resident | 11 | 10 | 64 | 0 | 4 | 6 | 20k |
| web/src/ui | 7 | 7 | 100 | 0 | 0 | 5 | 35k |
| web/src/overview | 6 | 6 | 100 | 0 | 0 | 5 | 10k |
| scripts/smoke.sh | 6 | 6 | 83 | 0 | 1 | 4 | 30k |

## Problem tasks
- T072 (heavy/feature, ian-claude): released×2 — Live camera session messages (capture → recogniser → live messages)
- T071 (light/test, ian-claude-light-2): released×2 blocked — Tests for useLiveSession and mockLiveStream
- T076 (light/test, max_API_light): released×1 — Tests for ContextTimeline and BaselineChart
- T101 (standard/improvement, ian-claude-standard-2): released×1 — Evidence players: keyboard and screen-reader pass
- T109 (standard/improvement, ian-claude-standard): released×1 — Resident detail: not-found, API-down and no-sessions states
- T096 (light/test, ian-claude-light-2): blocked — Scenario: teabag added three times is perseveration, stirring twice is
- T123 (light/bug, max_API_light): blocked — Bug: smoke.sh always fails the evidence replay check (alert body is ov
- T132 (light/improvement, ian-claude-light-2): blocked — Web tests: AlertView and PatternList time out under default parallelis
- T143 (standard/test, ian-claude-standard-2): blocked — Pattern scenario: motor slowing after a sedating medication
- T194 (light/test, ian-claude-light-2): released×1 — smoke.sh: seeded alert survives /demo/reset
- T197 (light/improvement, ian-claude-standard): released×1 — Heat calendar legend: CSS classes instead of inline styles
- T221 (light/improvement, ian-claude): released×1 — Copy summary uses the resident's real name, not one guessed from the i
- T220 (light/bug, ian-claude-light-2): CI×1 — Live screen: settle on session_end's final error list
- T149 (standard/feature, ian-claude-standard): released×1 — API: GET /monitoring and PUT /rooms/{room}/monitoring
- T226 (light/feature, ian-claude-light-2): released×1 — Ghost replay: say the figure is a stand-in for demo recordings

## Low task ratings (≤3/5)
- T194 3/5: 3/5 ambiguous: a literal 'does the alert persist' check fails against real behavior since /demo/reset intentionally drop
