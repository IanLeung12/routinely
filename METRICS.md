# METRICS (last 6 h, generated 2026-10-17 12:54 UTC)

- **Throughput:** 160/165 claimed tasks merged · 5 active workers · first-try success 90%
- **Friction:** 1 PR CI failures · 11 releases (9 sessions ended early, 1 stale, 1 conflicts) · 4 blocked
- **Main:** 2/150 main CI runs red · 0 reverts
- **Quality signals:** avg task rating 4.8/5 · 48 bug/review tasks filed (all time)
- **Host worker idle (recent log):** w1 0m, w2 63m, w3 3m, w4 3m

## By class
| class | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| light | 96 | 94 | 90 | 1 | 7 | 5 | 15k |
| standard | 61 | 59 | 92 | 0 | 4 | 10 | 65k |
| heavy | 8 | 7 | 88 | 0 | 0 | 19 | 140k |

## By kind
| kind | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| test | 43 | 42 | 91 | 0 | 4 | 5 | 25k |
| improvement | 41 | 40 | 85 | 0 | 5 | 7 | 35k |
| feature | 37 | 35 | 89 | 0 | 2 | 7 | 45k |
| bug | 34 | 33 | 94 | 1 | 0 | 11 | 80k |
| docs | 10 | 10 | 100 | 0 | 0 | 4 | 15k |

## By worker
| worker | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| ian-claude-light-2 | 60 | 58 | 87 | 1 | 5 | 4 | 15k |
| ian-claude-standard | 33 | 32 | 85 | 0 | 4 | 8 | 50k |
| ian-claude-standard-2 | 33 | 32 | 97 | 0 | 1 | 8 | 55k |
| ian-claude | 20 | 19 | 90 | 0 | 1 | 16 | 110k |
| max_API_light | 19 | 19 | 100 | 0 | 0 | 5 | 4k |

## By area (top 8)
| area | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| pipeline/src/routine_watch | 43 | 41 | 93 | 0 | 1 | 10 | 65k |
| web/src/live | 16 | 15 | 81 | 1 | 1 | 9 | 25k |
| web/src/alert | 15 | 14 | 80 | 0 | 2 | 7 | 45k |
| tests/scenarios | 13 | 13 | 100 | 0 | 0 | 8 | 30k |
| web/src/resident | 10 | 10 | 70 | 0 | 3 | 7 | 25k |
| web/src/ui | 7 | 7 | 100 | 0 | 0 | 5 | 35k |
| scripts/smoke.sh | 5 | 5 | 80 | 0 | 1 | 4 | 28k |
| web/src/overview | 4 | 4 | 100 | 0 | 0 | 5 | 9k |

## Problem tasks
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
- T227 (light/test, ian-claude-light-2): released×1 — Test: stand-in skeleton never changes what the recogniser reads
- T239 (standard/improvement, ian-claude-standard): released×1 — Resident detail: usable at phone width (375 px)
- T225 (light/improvement, ian-claude-light-2): released×1 — LiveSession: CSS file instead of inline <style>
- T229 (light/test, ian-claude-light-2): released×1 — Test: PatternList fixtures use unique pattern ids (no duplicate-key wa

## Low task ratings (≤3/5)
- T194 3/5: 3/5 ambiguous: a literal 'does the alert persist' check fails against real behavior since /demo/reset intentionally drop
