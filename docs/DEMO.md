# Demo runbook

One page for whoever drives the ≈3-minute demo (SPEC.md §10). Everything here runs
offline, with no API keys and no camera.

## Before you start

```sh
scripts/dev.sh up
```

Starts the API and the dashboard in the background with `OFFLINE_MODE=true` and
`LIVE_API=0` (both default on — the pipeline runs on mock data, no real camera or
paid API calls), and prints:

```
DASHBOARD_URL=http://localhost:5173
API_URL=http://localhost:8000
```

Open `DASHBOARD_URL` in a real browser. Optionally confirm the stack answers before
the audience sits down:

```sh
scripts/smoke.sh
```

`scripts/dev.sh status` shows whether each is running; `scripts/dev.sh down` stops
both and frees the ports.

## Click path

The dashboard's home screen (`web/src/App.tsx`) shows the unit overview, the live
session, and the alert list all on one page — no screen to navigate to first.

- **Hook:** nothing to click — say the line about delirium, a medication problem, or
  a decline being easy for staff to miss (SPEC §10.1).
- **Baseline:** in **Unit overview**, click Mrs. K's row. Her detail screen shows her
  last two normal weeks — the baseline the alert will compare against.
- **Live:** go back (or stay on the home screen) and watch the **Live session**
  section, already running the `tea_skip_teabag_pour_twice` scenario. A teammate (or
  the scenario itself) skips the teabag and pours twice; the task map tiles flash
  amber/red in real time as each step and error lands.
- **Alert:** when the session ends, a "Flagged for review" banner appears under
  **Live session** with an **Open alert** button — click it. (It's also listed under
  **Alerts** on the home screen if you miss the banner.) This opens the alert's
  evidence view: the exact errors, a ghost replay against her normal session, and the
  top pattern it's consistent with.
- **Why / not just delirium:** from the alert view, click back to **Unit overview**
  and open Mr. D's row — he's on "watch" with a different pattern (slow drift) to
  show the same signal leading to a different, less urgent action.
- **Close:** nothing to click — say the lines on privacy (no video stored), that it
  only flags a change for review, the feedback loop, and prior art (SPEC §10.7, §11).

## If something fails

**No Wi-Fi, or the live session drops:** the dashboard already falls back to mock
data automatically (the "Mock data" badge appears in the Live session card), so the
demo keeps going without any action.

**Camera or live session broken, need a clean replay instead:** replay the same
scenario the demo uses, fully offline, and read the result as JSON:

```sh
cd pipeline && uv run python -m routine_watch.replay ../tests/scenarios/tea_skip_teabag_pour_twice
```

Or check every recorded scenario still passes in one shot:

```sh
scripts/e2e.sh
```

**Dashboard or API frozen, need to restart clean:**

```sh
scripts/dev.sh down
scripts/dev.sh up
```

## Reset between runs

The scenario replay and `/alerts` endpoint don't need any manual cleanup between
takes — `scripts/dev.sh down` followed by `scripts/dev.sh up` gives a fresh process
with no state carried over. If only the dashboard tab is stale, reload it; it refetches
alerts and residents on mount.

### Between rehearsals

To put the demo back to its seeded history without restarting the stack:

```sh
curl -X POST http://localhost:8000/demo/reset
```

Returns `{"ok": true}`. Only works with `OFFLINE_MODE=true` or `DEMO_RESET=1` — it
refuses to run against a real deployment.

## Medication routine

The live screen defaults to the tea scenario. To open it on the medication routine
instead, add `?task=meds` to the dashboard URL, e.g.
`http://localhost:5173/?task=meds`.
