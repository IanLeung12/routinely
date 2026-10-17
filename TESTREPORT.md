# Test report
- main: 99dcc12 (T302: test alert view works keyboard-only)
- run: 2026-10-17 15:30 UTC (OFFLINE_MODE=true, LIVE_API unset)

## Levels
- 1 Unit (scripts/ci.sh): PASS
- 2 Simulation (scripts/e2e.sh): PASS, 29/29 scenarios (4 new meds_* scenarios)
- Smoke (scripts/smoke.sh, stack up): PASS, all checks
- Integration (scripts/integration.sh): PASS ("OK integration (api + dashboard + live ws)"). Run it before dev.sh up from the same clone (pid-file clash otherwise; tester ordering, not a product bug)
- 3 UI walkthrough: PASS, full demo path re-walked (api_state refactor, ResidentDetail/AlertView changes)
  - Reset demo → overview 4 watch · 2 normal → Mrs. K detail (baseline chart, heat calendar, consent line, "What nurses said: No nurse answers yet")
  - live session → "Flagged for review" banner + Open alert; Mrs. K chip flips to Flagged
  - alert view: summary, 4 timestamped errors, skeleton replay, patterns with rule-outs, Copy summary / Print
  - Confirmed → threshold 2.4 → 2.3; Mrs. K "What nurses said" shows "Confirmed · 17 Oct, 15:28"
  - document.title "Mrs. K — Routine Watch"; Pattern library urgency filter "Check this shift" shows only the delirium pattern
  - no captured console errors
- 4 Robustness: PASS (not re-run; e2e corrupted-frames cases still pass)

## Open bug tasks
- none
