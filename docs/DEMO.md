# Demo runbook

One page for whoever drives the ≈3-minute demo (SPEC.md §10). Everything here runs
offline, with no API keys and no camera — the one exception is the optional
["Live camera on your laptop"](#live-camera-on-your-laptop) section at the end.

## Before you start

Run this first; it brings the stack up (if it isn't already), smoke-tests every
route, replays every recorded scenario, and resets the demo so the dashboard shows
the demo resident on watch — one ✓/✗ checklist, offline, no API keys:

```sh
scripts/preflight.sh
```

It stops at the first ✗ with a one-line fix hint. Then:

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

The dashboard's home screen for a supervisor who supports several people
(`web/src/App.tsx`) shows the unit overview, the live session, and the alert list all
on one page — no screen to navigate to first.

- **Who it's for:** a browser that hasn't answered yet opens on "Who is this for?" —
  pick **I'm supporting someone** for the care-home demo (SPEC §17). The choice is
  remembered, and the **Viewing as** switch in the header flips between *Myself* (the
  person watching their own routine) and *Someone I support*. "Reset demo" puts the
  question back.
- **Hook:** nothing to click — say the line about delirium, a medication problem, or
  a decline being easy for staff to miss (SPEC §10.1).
- **Baseline:** in **Unit overview**, click Mrs. K's row. Her detail screen shows her
  last two normal weeks — the baseline the alert will compare against.
- **Privacy switch:** still on Mrs. K's row, point at the "Consent: ..." line, then
  flip the monitoring switch to **Paused** — "No camera data is processed while
  paused" appears, and **Recent changes** logs "Paused by ...". Back on **Unit
  overview** her row now shows a **Monitoring paused** chip, and the shift handoff
  names the paused room. Flip the switch back to **On** (or run `/demo/reset`).
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
- **Shift handoff:** click **Shift handoff**. Mrs. K's row shows her pending alert;
  click **Open alert** on that row to reach the same alert from a different screen.
- **Optional — people, My routine, routine builder:** if there's time, these three
  screens aren't on the main beat but round out the story (skip straight to Close
  otherwise):
  - **Myself / My routine:** flip **Viewing as** to **Myself**. The person's own
    screen shows **My routine**, the **How this week looks** card against their
    usual, and the **Your privacy** card — click **Pause watching** (then **Resume
    watching**) to show the off switch. Under **Invite someone**, click **Invite
    someone** to show the code a new supervisor would type in.
  - **People I support:** flip **Viewing as** back to **Someone I support**, paste
    that code into the invite-code box under **People I support**, and click **Add
    person** — the new row appears immediately with **Open** and **Stop supporting**
    on it.
  - **Routines / routine builder:** click **New routine** in the top bar (either
    role). On the **Describe it** tab, click the **Making toast** example, then
    **Draft routine** — offline (the default) this returns a canned fake draft; set
    `LIVE_API=1` to draft with the real model instead. Review the task map, use
    **Edit the steps**, then click **Save routine** to add it to the **Routines**
    list.
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

## Live camera on your laptop

Everything above plays recordings. To point the **Live session** card at your own
webcam instead — one command, laptop camera → `/ws/live?source=camera`:

```sh
scripts/camera.sh
```

It installs the capture extra (MediaPipe + OpenCV), downloads the two MediaPipe task
bundles into `models/` if they aren't there yet (free, no key, not in git), opens the
camera once to check it answers, restarts the local stack and prints:

```
DASHBOARD_URL=http://localhost:5173
API_URL=http://localhost:8000
LIVE_URL=http://localhost:5173/?source=camera&camera=0
```

Open `LIVE_URL`. The **Live session** card is now your camera, with a **Live camera**
badge where the **Mock data** one goes: the skeleton view on the left, the task map
filling in on the right, errors as they are classified. The **Routine to watch**
buttons above it pick which task graph the camera is read against (tea or medication),
and the session ends when you stop the stack:

```sh
scripts/dev.sh down
```

Three options:

```sh
scripts/camera.sh --camera 1           # a second or external device
scripts/camera.sh --record out.jsonl   # keep the capture records as well
scripts/camera.sh --preview            # see the camera picture, on this device only
```

Windows and Linux: index `0` is the built-in camera, and nothing asks for permission.
**macOS** asks the program that opens the camera — your *terminal*, not the browser —
so the first `scripts/camera.sh` pops a permission prompt; if it was denied earlier,
tick the terminal under System Settings → Privacy & Security → Camera and run it again.

`--record` writes the same JSONL a scenario holds — landmarks, boxes and timestamps,
never video (SPEC §8) — so a session you filmed can be replayed offline afterwards:

```sh
mkdir -p .dev/my_session && cp out.jsonl .dev/my_session/frames.jsonl
printf 'task: tea\nsteps: []\nerrors: []\nflag: false\n' > .dev/my_session/expected.yaml
cd pipeline && uv run python -m routine_watch.replay ../.dev/my_session
```

(Keep it out of `tests/scenarios/`, which is CI's own set.)

### Seeing the camera picture (this device only)

The dashboard draws skeletons, because that is all a capture record holds. While you
are framing the camera — is the kettle in shot? is the counter lit enough for MediaPipe
to find a hand? — you want the real picture too, so `--preview` adds it *under* the
skeleton on the machine with the camera:

```sh
scripts/camera.sh --preview
```

It prints one more line:

```
PREVIEW_URL=http://127.0.0.1:8765/preview.mjpg
```

Open `LIVE_URL` as usual and press **Show camera preview (this device only)** on the
skeleton view. The picture appears behind the skeleton and boxes, aligned to the same
coordinates, with a **Preview · not recorded · this device only** badge on it. Press it
again to go back to skeleton-only.

**What the promise is.** The capture process serves the current frame itself, on
`127.0.0.1` and nothing else: a client that is not this machine is refused, and so is a
request whose `Host:` is not loopback, so no page anywhere can read it through somebody
else's browser. One frame is held in memory at a time and dropped when the session ends.
Nothing is written to disk, nothing goes to the API, and nothing reaches a supervisor —
with the preview on, `--record` writes the same landmarks-and-boxes JSONL it always did
(SPEC §8, §12). It is for the person standing at the camera, and nobody else.

The toggle is only offered when the dashboard is open on the capture machine itself
(`localhost`) *and* that machine's preview answers. On any other machine, on a recorded
session, or without `--preview`, the Live screen is the skeleton view it has always
been — no toggle, no message, nothing to explain.

Two things worth knowing:

- `PREVIEW_PORT` moves it off 8765 if something else is there; `scripts/camera.sh`
  exports it to the dashboard as well, so use the script rather than setting it by hand.
- The preview exists only while the camera is open, so the toggle appears a moment
  after the first frame arrives, and goes when you stop the stack.

### What you'll see without detector weights

Without `DETECTOR_WEIGHTS` the local object detector doesn't run, and that is the
normal first run: the skeleton and hands stream live, the task map stays pending, and
it says **Waiting for object detector** under the map. Steps are hands on objects, so
they need the detector's boxes. To get steps too, export weights exported from
Roboflow — run locally, never hosted inference — before starting:

```sh
export DETECTOR_WEIGHTS=models/detector.onnx
scripts/camera.sh
```

### If the camera doesn't come up

`scripts/camera.sh` says why before it starts anything (`capture: no camera at index
0`). If it fails later, the Live session card falls back to the recorded demo and
shows the **Mock data** badge, and `.dev/api.log` has the reason:

```
no camera session on camera 0: no camera at index 0
```

Pausing the room from the resident's page stops the camera the same way it stops a
replay (SPEC §12): the card says monitoring is paused, and nothing is filmed until
it's back on — and with it the preview, which lives exactly as long as the camera does.

If `--preview` printed `PREVIEW_URL` but the toggle never appears, the capture process
has no camera to preview: `.dev/api.log` says so (`no camera session on camera 0`), and
the toggle waits for the first frame on purpose. A port already in use is in the same
log (`no camera preview on port 8765`) and costs you the preview, never the session.
