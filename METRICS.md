# METRICS (last 6 h, generated 2026-10-17 13:55 UTC)

- **Throughput:** 146/151 claimed tasks merged · 5 active workers · first-try success 88%
- **Friction:** 1 PR CI failures · 13 releases (11 sessions ended early, 1 stale, 1 conflicts) · 2 blocked
- **Main:** 2/149 main CI runs red · 0 reverts
- **Quality signals:** avg task rating 4.8/5 · 50 bug/review tasks filed (all time)
- **Host worker idle (recent log):** w1 0m, w2 63m, w3 3m, w4 3m

## By class
| class | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| light | 83 | 81 | 87 | 1 | 9 | 5 | 15k |
| standard | 58 | 56 | 90 | 0 | 4 | 9 | 65k |
| heavy | 10 | 9 | 90 | 0 | 0 | 17 | 130k |

## By kind
| kind | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| improvement | 43 | 41 | 84 | 0 | 5 | 8 | 45k |
| test | 40 | 38 | 85 | 0 | 4 | 5 | 30k |
| feature | 35 | 34 | 89 | 0 | 4 | 8 | 45k |
| bug | 24 | 24 | 96 | 1 | 0 | 11 | 90k |
| docs | 9 | 9 | 100 | 0 | 0 | 4 | 15k |

## By worker
| worker | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| ian-claude-light-2 | 50 | 48 | 82 | 1 | 7 | 4 | 15k |
| ian-claude-standard | 35 | 34 | 86 | 0 | 4 | 8 | 45k |
| ian-claude-standard-2 | 29 | 28 | 93 | 0 | 1 | 9 | 55k |
| ian-claude | 21 | 20 | 90 | 0 | 1 | 16 | 125k |
| max_API_light | 16 | 16 | 100 | 0 | 0 | 5 | 4k |

## By area (top 8)
| area | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| pipeline/src/routine_watch | 33 | 33 | 97 | 0 | 1 | 10 | 55k |
| web/src/live | 14 | 14 | 86 | 1 | 1 | 9 | 20k |
| web/src/alert | 13 | 12 | 77 | 0 | 2 | 8 | 48k |
| tests/scenarios | 9 | 9 | 100 | 0 | 0 | 8 | 55k |
| web/src/resident | 9 | 9 | 78 | 0 | 2 | 6 | 20k |
| web/src/ui | 6 | 6 | 100 | 0 | 0 | 5 | 32k |
| web/src/overview | 6 | 6 | 83 | 0 | 2 | 7 | 30k |
| web/src/handoff | 5 | 4 | 80 | 0 | 0 | 11 | 75k |

## Problem tasks
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
- T260 (standard/test, ian-claude-standard-2): released×1 — Test: first-load JS bundle size budget for the dashboard
- T255 (light/feature, ian-claude-light-2): released×2 — Resident detail: show who consented to monitoring
- T275 (standard/improvement, ian-claude-standard): released×1 — Live screen: notice a pause/resume made while the panel is open

## Low task ratings (≤3/5)
- T194 3/5: 3/5 ambiguous: a literal 'does the alert persist' check fails against real behavior since /demo/reset intentionally drop
- T266 3/5: 3/5 area was stale (LiveScreen.tsx has no paused UI; it lives in LiveSession.tsx, which the listed area didn't include)
