# METRICS (last 6 h, generated 2026-10-17 16:58 UTC)

- **Throughput:** 100/107 claimed tasks merged · 6 active workers · first-try success 84%
- **Friction:** 2 PR CI failures · 12 releases (9 sessions ended early, 0 stale, 1 conflicts) · 2 blocked
- **Main:** 0/108 main CI runs red · 0 reverts
- **Quality signals:** avg task rating 4.8/5 · 54 bug/review tasks filed (all time)
- **Host worker idle (recent log):** w1 0m, w2 63m, w3 3m, w4 3m

## By class
| class | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| standard | 50 | 48 | 88 | 1 | 4 | 11 | 58k |
| light | 45 | 41 | 80 | 1 | 7 | 10 | 25k |
| heavy | 12 | 11 | 83 | 0 | 1 | 20 | 135k |

## By kind
| kind | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| test | 46 | 42 | 80 | 2 | 6 | 11 | 45k |
| improvement | 33 | 31 | 82 | 0 | 4 | 17 | 75k |
| feature | 17 | 16 | 88 | 0 | 2 | 10 | 52k |
| bug | 9 | 9 | 100 | 0 | 0 | 13 | 70k |
| docs | 2 | 2 | 100 | 0 | 0 | 7 | 15k |

## By worker
| worker | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| ian-claude-standard-2 | 28 | 27 | 89 | 1 | 2 | 11 | 55k |
| ian-claude-standard | 28 | 27 | 89 | 0 | 2 | 9 | 55k |
| ian-claude-light-2 | 27 | 25 | 81 | 0 | 5 | 8 | 20k |
| ian-claude | 18 | 17 | 83 | 1 | 2 | 20 | 130k |
| max_API_light | 3 | 2 | 33 | 0 | 1 | 37 | 7k |
| Max_codex_light | 3 | 2 | 67 | 0 | 0 | 16 | 4k |

## By area (top 8)
| area | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| pipeline/src/routine_watch | 19 | 18 | 89 | 0 | 1 | 13 | 75k |
| web/src/resident | 9 | 6 | 56 | 0 | 1 | 9 | 52k |
| web/src/alert | 8 | 8 | 88 | 0 | 1 | 15 | 50k |
| web/src/live | 7 | 7 | 86 | 0 | 1 | 13 | 75k |
| web/src/overview | 7 | 7 | 86 | 0 | 2 | 9 | 42k |
| web/src/about | 5 | 5 | 80 | 0 | 1 | 11 | 20k |
| scripts/smoke.sh | 4 | 4 | 100 | 0 | 0 | 9 | 55k |
| web/src/handoff | 4 | 4 | 75 | 1 | 1 | 21 | 52k |

## Problem tasks
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
- T310 (light/test, ian-claude-light-2): blocked — Test: pattern library urgency filter (every option, reset, empty state
- T314 (standard/test, ian-claude-standard-2): CI×1 released×1 — Scenarios: tea_two_errors_one_session and tea_long_pause_not_error
- T328 (light/test, Max_codex_light): blocked — Test: /ws/live WebSocket routes in api_live.py

## Low task ratings (≤3/5)
- T266 3/5: 3/5 area was stale (LiveScreen.tsx has no paused UI; it lives in LiveSession.tsx, which the listed area didn't include)
