# Test report
- main: 2bc3e75 (T281: shift handoff shows who paused a room and when)
- run: 2026-10-17 14:22 UTC (OFFLINE_MODE=true, LIVE_API unset)

## Levels
- 1 Unit (scripts/ci.sh): PASS
- 2 Simulation (scripts/e2e.sh): PASS, 25/25 scenarios
- Smoke (scripts/smoke.sh, stack up): PASS, all checks
- Integration (scripts/integration.sh): PASS ("OK integration (api + dashboard + live ws)"). Note: run it with no dev.sh stack up from the same clone, else its dev.sh up sees the pid files, skips starting on 8100 and times out (tester ordering, not a product bug)
- 3 UI walkthrough: PASS (only the changed screen re-checked; demo path code unchanged since 1d6ee98 where it passed end to end)
  - shift handoff with room 204 paused (T281): "Monitoring paused: Mrs. K (room 204), paused by nurse at 14:19"; Mrs. K row keeps "Monitoring paused" chip; no console errors
  - demo path (overview → Mrs. K → live session → alert → Confirmed, threshold 2.4 → 2.3) passed at 1d6ee98
- 4 Robustness: PASS (not re-run; e2e corrupted-frames cases still pass)

## Open bug tasks
- none (T270, T277 done)
