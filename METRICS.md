# METRICS (last 6 h, generated 2026-10-17 17:59 UTC)

- **Throughput:** 104/111 claimed tasks merged · 6 active workers · first-try success 85%
- **Friction:** 2 PR CI failures · 14 releases (11 sessions ended early, 0 stale, 0 conflicts) · 6 blocked
- **Main:** 0/110 main CI runs red · 0 reverts
- **Quality signals:** avg task rating 4.8/5 · 58 bug/review tasks filed (all time)
- **Host worker idle (recent log):** w1 0m, w2 63m, w3 3m, w4 3m

## By class
| class | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| standard | 50 | 48 | 90 | 1 | 3 | 11 | 55k |
| light | 49 | 45 | 80 | 1 | 8 | 11 | 22k |
| heavy | 12 | 11 | 83 | 0 | 3 | 19 | 130k |

## By kind
| kind | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| test | 55 | 51 | 82 | 2 | 7 | 11 | 45k |
| improvement | 31 | 30 | 87 | 0 | 3 | 14 | 62k |
| feature | 17 | 16 | 88 | 0 | 4 | 13 | 45k |
| bug | 6 | 5 | 83 | 0 | 0 | 13 | 52k |
| docs | 2 | 2 | 100 | 0 | 0 | 7 | 15k |

## By worker
| worker | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| ian-claude-standard-2 | 28 | 27 | 89 | 1 | 2 | 11 | 55k |
| ian-claude-standard | 28 | 27 | 93 | 0 | 1 | 10 | 45k |
| ian-claude-light-2 | 27 | 26 | 85 | 0 | 4 | 9 | 18k |
| ian-claude | 17 | 16 | 82 | 1 | 4 | 19 | 125k |
| Max_codex_light | 6 | 4 | 67 | 0 | 1 | 16 | 4k |
| max_API_light | 5 | 4 | 40 | 0 | 2 | 30 | 6k |

## By area (top 8)
| area | tasks | merged | first-try % | CI fails | releases | median min | median tokens |
|---|---|---|---|---|---|---|---|
| pipeline/src/routine_watch | 18 | 16 | 83 | 0 | 3 | 14 | 75k |
| web/src/overview | 9 | 8 | 78 | 0 | 2 | 9 | 40k |
| web/src/resident | 9 | 9 | 89 | 0 | 1 | 10 | 40k |
| tests/scenarios | 8 | 7 | 75 | 1 | 1 | 13 | 50k |
| web/src/alert | 6 | 5 | 67 | 0 | 1 | 21 | 55k |
| web/src/handoff | 5 | 5 | 80 | 1 | 1 | 20 | 60k |
| web/src/live | 4 | 4 | 100 | 0 | 0 | 14 | 78k |
| scripts/smoke.sh | 4 | 4 | 100 | 0 | 0 | 9 | 55k |

## Problem tasks
- T229 (light/test, ian-claude-light-2): released×1 — Test: PatternList fixtures use unique pattern ids (no duplicate-key wa
- T260 (standard/test, ian-claude-standard-2): released×1 — Test: first-load JS bundle size budget for the dashboard
- T255 (light/feature, ian-claude-light-2): released×2 — Resident detail: show who consented to monitoring
- T275 (standard/improvement, ian-claude-standard): released×1 — Live screen: notice a pause/resume made while the panel is open
- T294 (light/test, ian-claude): CI×1 released×1 — Test: shift handoff works keyboard-only
- T187 (light/test, Max_codex_light): released×1 — Test: App shows the live routine picker with tea selected
- T307 (light/test, max_API_light): released×1 — Test: replay player works keyboard-only
- T301 (heavy/improvement, ian-claude): released×1 — Review: contract schema + smoke check for GET /residents/{id}/feedback
- T310 (light/test, ian-claude-light-2): blocked — Test: pattern library urgency filter (every option, reset, empty state
- T314 (standard/test, ian-claude-standard-2): CI×1 released×1 — Scenarios: tea_two_errors_one_session and tea_long_pause_not_error
- T328 (light/test, Max_codex_light): blocked — Test: /ws/live WebSocket routes in api_live.py
- T330 (light/improvement, ian-claude-light-2): released×1 blocked — Heat calendar: usable at phone width (375 px)
- T334 (light/test, max_API_light): released×1 — Test: pattern checks and summaries never use diagnosis wording
- T349 (light/improvement, Max_codex_light): blocked — worker.sh: always disallow Monitor/ScheduleWakeup for claude and re-re
- T341 (light/test, max_API_light): blocked — Test: pattern library urgency filter works keyboard-only

## Low task ratings (≤3/5)
- T266 3/5: 3/5 area was stale (LiveScreen.tsx has no paused UI; it lives in LiveSession.tsx, which the listed area didn't include)
