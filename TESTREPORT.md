# Test report
- main: 7c48d9c (T036: Add skeleton evidence replay player)
- run: 2026-10-17 05:20 UTC (OFFLINE_MODE=true, LIVE_API unset)

## Levels
- 1 Unit (scripts/ci.sh): PASS
- 2 Simulation (scripts/e2e.sh): PASS, 7/7 scenarios (tea_no_kettle, tea_normal, tea_sequence_error, tea_single_bad_no_flag, tea_skip_teabag_pour_twice, tea_substitution, tea_unclear_not_error)
- 3 UI walkthrough: PARTIAL
  - unit overview (status chips, sparklines): PASS
  - Mrs. K detail (baseline chart, heat calendar, sessions, care records): PASS with cosmetic bug T048 (calendar light background / unreadable high-score cell)
  - live session / demo replay / task map: not built (T043, T029 open)
  - alert + evidence view + "confirmed" threshold change: not built (T028 open)
  - api/web logs: no errors
- 4 Robustness: not run (level 3 not fully passing yet; waiting on live/evidence screens)

## Open bug tasks
- T048 (priority 1): heat calendar ignores dark theme
