# METRICS (last 6 h, generated 2026-10-17 15:57 UTC)

- **Throughput:** 101/107 claimed tasks merged · 5 active workers · first-try success 83%
- **Friction:** 2 PR CI failures · 15 releases (13 sessions ended early, 0 stale, 1 conflicts) · 1 blocked
- **Main:** 2/108 main CI runs red · 0 reverts
- **Quality signals:** avg task rating 4.8/5 · 53 bug/review tasks filed (all time)
- **Host worker idle (recent log):** w1 0m, w2 63m, w3 3m, w4 3m

## By class
| class | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| light | 49 | 46 | 78 | 2 | 10 | 9 | 30k |
| standard | 48 | 46 | 88 | 0 | 4 | 11 | 65k |
| heavy | 10 | 9 | 90 | 0 | 1 | 19 | 140k |

## By kind
| kind | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| test | 39 | 34 | 77 | 1 | 6 | 10 | 45k |
| improvement | 36 | 35 | 86 | 0 | 5 | 10 | 65k |
| feature | 18 | 18 | 83 | 0 | 4 | 12 | 45k |
| bug | 12 | 12 | 92 | 1 | 0 | 13 | 48k |
| docs | 2 | 2 | 100 | 0 | 0 | 7 | 15k |

## By worker
| worker | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| ian-claude-light-2 | 31 | 30 | 77 | 1 | 7 | 7 | 18k |
| ian-claude-standard | 30 | 29 | 87 | 0 | 3 | 9 | 55k |
| ian-claude-standard-2 | 26 | 24 | 88 | 0 | 1 | 11 | 60k |
| ian-claude | 19 | 18 | 84 | 1 | 3 | 19 | 118k |
| max_API_light | 1 | 0 | 0 | 0 | 1 | – | – |

## By area (top 8)
| area | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| pipeline/src/routine_watch | 21 | 20 | 90 | 0 | 2 | 13 | 85k |
| web/src/alert | 12 | 12 | 83 | 0 | 2 | 10 | 48k |
| web/src/live | 10 | 10 | 80 | 1 | 1 | 12 | 30k |
| web/src/resident | 8 | 8 | 88 | 0 | 1 | 8 | 45k |
| web/src/about | 4 | 4 | 75 | 0 | 1 | 10 | 22k |
| scripts/smoke.sh | 4 | 4 | 100 | 0 | 0 | 9 | 55k |
| web/src/overview | 4 | 4 | 75 | 0 | 2 | 8 | 42k |
| tests/scenarios | 4 | 2 | 50 | 0 | 0 | 10 | 55k |

## Problem tasks
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
- T294 (light/test, ian-claude): CI×1 released×1 — Test: shift handoff works keyboard-only
- T187 (light/test, ian-claude-light-2): released×1 — Test: App shows the live routine picker with tea selected
- T307 (light/test, max_API_light): released×1 — Test: replay player works keyboard-only
- T301 (heavy/improvement, ian-claude): released×1 — Review: contract schema + smoke check for GET /residents/{id}/feedback

## Low task ratings (≤3/5)
- T266 3/5: 3/5 area was stale (LiveScreen.tsx has no paused UI; it lives in LiveSession.tsx, which the listed area didn't include)
