# METRICS (last 6 h, generated 2026-10-17 14:56 UTC)

- **Throughput:** 122/127 claimed tasks merged · 5 active workers · first-try success 86%
- **Friction:** 2 PR CI failures · 13 releases (11 sessions ended early, 1 stale, 1 conflicts) · 0 blocked
- **Main:** 2/129 main CI runs red · 0 reverts
- **Quality signals:** avg task rating 4.8/5 · 51 bug/review tasks filed (all time)
- **Host worker idle (recent log):** w1 0m, w2 63m, w3 3m, w4 3m

## By class
| class | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| light | 64 | 61 | 81 | 2 | 9 | 6 | 25k |
| standard | 54 | 53 | 91 | 0 | 4 | 9 | 65k |
| heavy | 9 | 8 | 89 | 0 | 0 | 19 | 140k |

## By kind
| kind | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| test | 39 | 35 | 79 | 1 | 4 | 8 | 45k |
| improvement | 39 | 39 | 87 | 0 | 5 | 9 | 50k |
| feature | 26 | 25 | 85 | 0 | 4 | 9 | 58k |
| bug | 19 | 19 | 95 | 1 | 0 | 12 | 70k |
| docs | 4 | 4 | 100 | 0 | 0 | 5 | 15k |

## By worker
| worker | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| ian-claude-light-2 | 41 | 39 | 78 | 2 | 7 | 6 | 15k |
| ian-claude-standard | 32 | 31 | 84 | 0 | 4 | 9 | 55k |
| ian-claude-standard-2 | 28 | 27 | 93 | 0 | 1 | 10 | 55k |
| ian-claude | 20 | 19 | 90 | 0 | 1 | 17 | 130k |
| max_API_light | 6 | 6 | 100 | 0 | 0 | 5 | 4k |

## By area (top 8)
| area | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| pipeline/src/routine_watch | 24 | 23 | 92 | 0 | 1 | 11 | 75k |
| web/src/live | 13 | 13 | 85 | 1 | 1 | 9 | 20k |
| web/src/alert | 13 | 13 | 85 | 0 | 2 | 10 | 45k |
| web/src/overview | 7 | 6 | 71 | 0 | 2 | 7 | 35k |
| web/src/resident | 7 | 7 | 71 | 0 | 2 | 8 | 30k |
| tests/scenarios | 6 | 5 | 83 | 0 | 0 | 8 | 55k |
| scripts/smoke.sh | 6 | 6 | 83 | 0 | 1 | 9 | 50k |
| web/src/handoff | 5 | 4 | 80 | 1 | 0 | 13 | 68k |

## Problem tasks
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
- T294 (light/test, ian-claude-light-2): CI×1 — Test: shift handoff works keyboard-only

## Low task ratings (≤3/5)
- T194 3/5: 3/5 ambiguous: a literal 'does the alert persist' check fails against real behavior since /demo/reset intentionally drop
- T266 3/5: 3/5 area was stale (LiveScreen.tsx has no paused UI; it lives in LiveSession.tsx, which the listed area didn't include)
