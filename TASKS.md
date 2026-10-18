# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: 42508fc

## Tasks

### T449 — Stability: lazy-load AlertView and ResidentDetail to restore first-load bundle headroom
- status: done
- class: light
- priority: 1
- kind: improvement
- source: orchestrator
- deps: —
- area: web/src/App.tsx, web/scripts/check-bundle.mjs, web/README.md
- owner: ian-claude-heavy-3
- claimed: 2026-10-18T00:57Z
- pr: #439
- note: orch: T432 (#431) raised BUDGET_BYTES to 99_000 (measured 98,102); after lazy-loading AlertView/ResidentDetail lower it to new measured + ~1,500
- rating: 5/5 clear — the note named the exact measurement and the budget formula, and the existing tests already used findBy so none needed changing

What: The first-load JS budget has been bumped three times today (92,200 → 96,000 → 96,500) and main sits ~250 B under it, so every remaining pre-freeze UI PR risks a red "first-load JS over budget" CI. Make `AlertView` and `ResidentDetail` lazy in `App.tsx` the same way `Handoff`/`RoutinesScreen` already are, then lower the budget to measured + ~1,500 B.
Why: stops bundle-budget CI failures from blocking demo-path PRs in the last 90 minutes before the 01:30 UTC freeze.
Interface: in `web/src/App.tsx` replace the eager `import { AlertView }` / `import { ResidentDetail }` with `lazy(() => import(...).then(m => ({ default: m.X })))` and render them inside the existing `<Suspense fallback={<Loading .../>}>` pattern used for `RoutinesScreen`. Read only `web/src/App.tsx`, `web/scripts/check-bundle.mjs` and the bundle section of `web/README.md`.
Acceptance:
- `cd web && npm run build && npm run check:bundle` passes; set `BUDGET_BYTES` to the new measured total + ~1,500 and record the measured number in the comment and in web/README.md.
- Existing App tests pass (if a test uses sync `getBy` on the alert/resident screen right after navigation, switch only that query to `findBy`).
- `scripts/ci.sh` passes.

### T450 — Safety check-in backend: alert → check-in countdown → supervisor alarm → escalation (Project KAZE)
- status: done
- class: heavy
- priority: 0
- kind: feature
- source: ian
- deps: —
- area: pipeline/src/routine_watch/checkin.py, pipeline/src/routine_watch/api_checkin.py, pipeline/src/routine_watch/api.py, pipeline/src/routine_watch/api_live.py, pipeline/tests/test_checkin.py, pipeline/tests/test_api_checkin.py, SPEC.md
- owner: ian-claude-heavy-3
- claimed: 2026-10-17T23:57Z
- pr: #436
- rating: 4/5 clear on the state machine, windows, permissions and the 7 scenarios; the 'api_alerts/alerts.py' hook point does not exist in this codebase (alerts are derived from flags on read, so the hook had to go on the flagged session_end in api_live.py), and the area left out contracts/ + the dashboard's live-message union, so the new checkin WS message is additive and undocumented in contracts/

What: Ian is entering the **Project KAZE** challenge ("help when someone can't ask for it themselves"). Whenever an **alert** is raised for a person, the system asks the **person** to check in. If they don't within a window, it **sounds an alarm for their supervisor**, then escalates to the next supporter if nobody acknowledges. All simulated; never a real call or SMS.
Why: KAZE prize ($1,500); also makes alerts actionable when the person can't respond.
Interface:
- `checkin.py`: a pure state machine with an injectable clock. States: `pending` (waiting for the person) → `ok` (cancelled with the safety PIN) | `duress` (duress PIN: **looks exactly like ok to the person**, but raises a silent `alarm` to supervisors marked duress) | `alarm` (window expired: supporter #1 alarmed) → `escalated` (supporter #1 didn't acknowledge within the ack window: supporter #2, and so on down the list) → `acknowledged` (a supporter tapped "I'm on it") → `resolved` (a supporter or the person resolves it, with a reason: `false_alarm` | `helped` | `other`). Every transition is appended to an event log with a timestamp and actor.
- **The server owns the countdown**: deadlines are stored server-side, and a background tick (asyncio, every 1 s) advances them, so an alarm still fires if the person's device disconnects after the check-in started (KAZE "connectivity failure").
- Settings per person (in-memory + JSON under `.data/`, mock defaults for the demo people): check-in window (default 120 s, demo 20 s), ack window (default 120 s, demo 15 s), ordered supporter list (from the T408 people links), safety PIN + duress PIN (hashed, never returned or logged), and **sharing permissions** per supporter: `location` (a simulated room/address string), `alert_details` (errors and evidence) and `replay`. Supervisor payloads include only what that supporter is allowed to see; the test proves it.
- Hook: when an alert is created (`api_alerts` / `alerts.py` path), start a check-in for that person (idempotent per alert). `POST /checkins/demo` starts one by hand, for the demo.
- API (`api_checkin.py`): `GET /checkins/active?person=` · `POST /checkins/{id}/respond {pin}` (same 200 response for the safety and duress PINs, wrong PIN → 401 and the countdown keeps running) · `POST /checkins/{id}/ack {supporter}` · `POST /checkins/{id}/resolve {by, reason}` · `GET/PUT /people/{id}/safety` (settings; PINs write-only) · `POST /checkins/{id}/simulate {event: "disconnect"|"reconnect"}` (marks the person's device offline; the countdown carries on). Push state changes on the existing live WebSocket (`checkin` messages) so the UIs update instantly.
- Wording (SPEC §12): "check in", "alarm", "is everyone okay?"; never diagnostic.
- SPEC: a short §18 "Safety check-ins (Project KAZE)": the flow, the 7 scenarios, and what is real vs simulated (no real calls/SMS, simulated location, demo timings).
Acceptance: tests with a fake clock for all 7 KAZE scenarios: safe; no response → alarm; duress (person sees "ok", supervisor gets a silent duress alarm); disconnect after start → alarm still fires; unacknowledged → escalates to #2; false alarm resolved by a supporter and by the person; permissions (a supporter without `location` never gets it). The duress and safety responses are byte-identical. PINs never appear in any response or log. `scripts/ci.sh` passes.

### T451 — Check-in UI (person side): countdown, "I'm okay" + PIN pad
- status: done
- class: standard
- priority: 0
- kind: feature
- source: ian
- deps: —
- area: web/src/checkin/CheckInCard.tsx, web/src/checkin/CheckInCard.test.tsx, web/src/checkin/PinPad.tsx, web/src/checkin/PinPad.test.tsx, web/src/checkin/checkin.css, web/src/checkin/api.ts, web/src/checkin/types.ts, web/src/mock/checkins.ts, web/src/people/MyRoutine.tsx
- owner: max_API_standard
- claimed: 2026-10-18T00:58Z
- pr: #437
- rating: 5/5 clear
- note: PR #437 merged with passing CI; concurrent worker completed the merge repair during local validation.

What: The person's half of T450, built in parallel against T450's API shape with a mock (`web/src/mock/checkins.ts`). Follow `docs/DESIGN.md`. In "for myself" mode (`MyRoutine`), when a check-in is active, a calm full-width card appears: "Quick check-in: are you okay?", a large countdown ring, one big **I'm okay** button that opens a large-key PIN pad (works with shaky hands: big targets, no time pressure shown beyond the ring). After any accepted PIN, safety or duress, it shows the **same** "Thanks, you're checked in" screen (duress must be indistinguishable). A wrong PIN says "Try again" and the countdown continues. Accessible: focus moves to the card, `aria-live` announcements, keyboard only.
Acceptance: Vitest: the card shows for an active check-in; a wrong PIN keeps it pending; the safety and duress paths render identical DOM; countdown text updates; `cd web && npm test && npm run build`.

### T452 — Supervisor alarm UI: alarm banner + sound, acknowledge, escalation timeline, resolve
- status: done
- class: standard
- priority: 0
- kind: feature
- source: ian
- deps: —
- area: web/src/checkin/AlarmBanner.tsx, web/src/checkin/AlarmBanner.test.tsx, web/src/checkin/EscalationTimeline.tsx, web/src/checkin/EscalationTimeline.test.tsx, web/src/checkin/alarmSound.ts, web/src/checkin/SafetySettings.tsx, web/src/checkin/SafetySettings.test.tsx, web/src/checkin/alarm.css, web/src/App.tsx
- owner: max_API_standard
- claimed: 2026-10-18T00:25Z
- pr: #435
- note: released by max_API_standard: run ended without progress
- rating: 4/5 Shared API field names were unspecified while T450 and T451 were still unlanded; otherwise clear.

What: The supervisor's half of T450, against the same mock as T451 (reuse `web/src/checkin/api.ts` / `types.ts` if T451 has landed; otherwise add them identically, since T451 owns them). In "supporting someone" mode, an `alarm` / `escalated` check-in shows a prominent, dismiss-proof **alarm banner** on every screen: "Mrs. K hasn't checked in (2 min)", plus "silent help request" for duress. It plays a repeating alarm tone made with Web Audio (no audio file), with a mute toggle and the browser's autoplay rule handled by an "Enable sound" control. Buttons: **I'm on it** (ack) and **Resolve** (false alarm / helped / other). An **escalation timeline** shows each step with times: alert → check-in sent → no answer → you were alarmed → escalated to {next} → acknowledged by → resolved. It shows only the fields the payload carries (respect T450's sharing permissions: no location line if it isn't shared). **SafetySettings**: an ordered supporter list, windows, and what each supporter may see; PINs are set but never displayed.
Acceptance: Vitest: the banner appears for an alarm and clears on resolve; duress shows "silent help request"; the timeline renders the events; no location when it's absent; sound starts/stops (mock AudioContext); `cd web && npm test && npm run build`.

### T453 — KAZE demo: scenario runner + docs (what's real vs simulated)
- status: done
- class: light
- priority: 1
- kind: improvement
- source: ian
- deps: T450
- area: scripts/kaze_demo.py, docs/KAZE.md, tests/scenarios/kaze/
- owner: ian-claude
- claimed: 2026-10-18T00:57Z
- pr: #440
- rating: 4/5 the area's tests/scenarios/kaze/ cannot exist: any directory there is read as a pipeline replay scenario (e2e.sh + scenario_dirs()), so the runner's tests went to tests/test_kaze_demo.py; everything else was clear

What: `scripts/kaze_demo.py <scenario>` drives a running local stack through each of the 7 KAZE scenarios using only T450's HTTP API (`safe`, `no-response`, `duress`, `disconnect`, `unacknowledged`, `false-alarm`, `privacy`), with demo timings, printing each state change. `docs/KAZE.md` covers: the challenge mapping (each scenario → what to click or run), and a "What the prototype demonstrates / What is simulated / Assumptions / What needs validation" section (real push/SMS providers, location, wearable signals, false-alarm rates).
Acceptance: each scenario exits 0 against `scripts/dev.sh up`; `python3 scripts/kaze_demo.py --help` works; read only T450's API, nothing else.

### T454 — Impact evaluation on synthetic data: catch rate, false alarms, hours earlier (docs/EVAL.md)
- status: done
- class: standard
- priority: 0
- kind: feature
- source: ian
- deps: —
- area: scripts/eval.py, pipeline/tests/test_eval.py, docs/EVAL.md, docs/eval/
- owner: ian-claude-standard-3
- claimed: 2026-10-18T00:15Z
- pr: #432
- note: released by max_API_standard-2: run ended without progress
- rating: 5/5 clear

What: Measurable impact for the "AI for Social Impact" track. `scripts/eval.py` runs the real pipeline (scoring, change detection, patterns; offline fakes, no paid calls) over a seeded synthetic cohort: about 50 people x 60 days generated with the existing generator (`pipeline/src/routine_watch/synth`), with labelled ground truth: a sudden change at a known onset (about 30%), a slow drift (about 15%), and normal with realistic noise (the rest). Report:
- **sudden changes caught** / missed (sensitivity), and **false alarms per person per month** on the normal group;
- **hours from onset to flag** (median, p90);
- versus a **weekly screening check** baseline (catches a change at the next weekly check if it is present then): median hours earlier;
- drift reported as a trend, not an alarm (count);
- a sensitivity sweep of the threshold (3 points) showing the false-alarm vs catch trade-off.
Write `docs/EVAL.md`: the numbers, one SVG/PNG chart in `docs/eval/` (hours earlier vs weekly check, or the trade-off curve; matplotlib only if it's already a dependency, otherwise a hand-made SVG), the method in 5 lines, and **limits stated plainly** (synthetic data, error rates from the literature, not clinical validation; what a real pilot would measure). Add a one-line "impact estimate" with its assumption shown (e.g. "if 1 in N caught changes avoids an ER visit...").
Why: the track asks for measurable societal impact; right now the pitch has no numbers.
Acceptance: deterministic (seeded, same numbers every run); finishes in < 60 s; a test runs a 5-person cohort and checks the metric keys and ranges; `scripts/ci.sh` passes.

### T455 — Bug: "Draft routine" blanks the whole dashboard (API task_graph steps use `deps`, UI reads `depends_on`)
- status: done
- class: light
- priority: 0
- kind: bug
- deps: —
- area: web/src/routines/api.ts, web/src/routines/api.test.ts, web/src/routines/RoutineBuilder.test.tsx
- source: tester
- owner: max_API_light
- claimed: 2026-10-18T00:25Z
- pr: #434
- rating: 4/5 saved graph alias behavior required confirmation; otherwise clear

What: on main @2e488ba with the dev stack up (`OFFLINE_MODE=true scripts/dev.sh up`), click **New routine** → **Brushing teeth** example (any example) → **Draft routine**: the React root unmounts and the page goes blank. Console: `TypeError: can't access property "includes", step.depends_on is undefined` (StepEditor.tsx:65/130). Cause: `POST /routines/draft` answers 200 with `task_graph.steps[*].deps` (routine_builder.py ~847), but `web/src/routines/types.ts` `RoutineStep` and `StepEditor` expect `depends_on`. Before T444 this was hidden by the mock fallback; now the real (fake-drafter) response reaches the UI. Repro API side: `curl -s -X POST -F "description=Get the toothbrush, then brush" localhost:8000/routines/draft` → steps have `deps`, no `depends_on`. This is on docs/DEMO.md's click path (routine builder step).
Expected: draft renders the task map + step editor; Save routine works.
Interface: normalize in `web/src/routines/api.ts` (map `deps` → `depends_on`, default missing `objects`/`depends_on` to `[]`, `needs_training`/`warnings` to `[]`) for `draftFromText`, `draftFromVideo` and any fetched `SavedRoutine.task_graph`. Check that `POST /routines` accepts what the UI sends (backend accepts `depends_on`/`deps` aliases on draft steps; confirm for the saved graph). Don't change `contracts/` or the API.
Acceptance:
- api.test.ts: a draft response whose steps use `deps` comes back with `depends_on`.
- RoutineBuilder test: drafting with a `deps`-shaped response renders the step editor without throwing.
- Manual: the click path above shows the draft and saves it to the Routines list.
- `scripts/ci.sh` passes.

### T456 — Review: Replays delete swallows a failed delete (unhandled rejection, no message)
- status: done
- class: light
- priority: 0
- kind: bug
- source: reviewer
- deps: —
- area: web/src/replays/Replays.tsx, web/src/replays/Replays.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-18T00:32Z
- pr: #438
- note: —
- rating: 5/5 clear

What: In `web/src/replays/Replays.tsx`, `confirmDelete` awaits `deleteReplay` with no try/catch and is called as `void confirmDelete(...)`. When the delete is refused (already possible for "Replay not found"; every non-ok once T441 lands), the promise rejection is unhandled, the confirm box stays open and the person gets no feedback, so they can't tell whether their replay (SPEC §17 privacy control) was removed.
Interface: wrap the call in try/catch; on failure keep the replay in the list and on screen, close the confirm, and show the error with `ErrorState` from `web/src/ui/` (e.g. "This replay could not be deleted. It is still stored."). Only filter the list and close the session on success.
Acceptance:
- Replays.test.tsx: person role, `deleteReplay` mocked to reject → error message shown, replay still listed after going back; resolve → removed.
- `scripts/ci.sh` passes.

### T457 — Bug: supervisor alarm UI (T452) doesn't speak the real check-in API (T450)
- status: done
- class: standard
- priority: 0
- kind: bug
- deps: T450, T452
- area: web/src/checkin/api.ts, web/src/checkin/types.ts, web/src/checkin/AlarmBanner.tsx, web/src/checkin/AlarmBanner.test.tsx, web/src/checkin/SafetySettings.tsx, web/src/checkin/SafetySettings.test.tsx, web/src/checkin/EscalationTimeline.tsx, web/src/checkin/EscalationTimeline.test.tsx
- owner: ian-claude-heavy-2
- claimed: 2026-10-18T02:40Z
- pr: #442
- note: released by ian-claude-standard-4: run ended without progress; partial work on branch task/T457-wip-0130: start from it (git switch task/T457-wip-0130 && git merge origin/main)
- rating: 4/5 the interface section listed every real mismatch (field names, wrappers, extra=forbid), which made this mostly mechanical; it didn't say the backend also renamed the event-log vocabulary (started/checked_in/alarmed/duress/escalation_exhausted vs T452's alert/no_answer/alarm), so EscalationTimeline needed rewriting too

What: T452 and T450 merged in parallel against different shapes, so with a live API the supervisor alarm banner and safety settings break (works only on the fake). Make `web/src/checkin/api.ts` + `types.ts` match `pipeline/src/routine_watch/api_checkin.py` / `checkin.py` (the backend is the source of truth; don't change it).
Interface (mismatches found):
- `GET /checkins/active` 422s when both `person` and `supporter` are sent; the supervisor banner must send only `?supporter=`. Response is `{"checkins": [...]}`, not a bare array.
- `/ack`, `/resolve` answer `{"checkin": {...}}`.
- Supporter view fields: `checkin_id` (not `id`), `state` (not `status`), `started_at` (not `created_at`), `person_name`, `seconds_left`, etc. (see `supporter_view` in checkin.py); map them in api.ts or change the types and consumers.
- Safety settings use `checkin_window_s` / `ack_window_s` (not `checkin_window`/`ack_window`), and `SafetyIn` is `extra="forbid"`, so the current PUT 422s.
Acceptance:
- api.ts tests stub `fetch` with payloads copied from the backend shapes (supporter_view, settings_payload) and pass; fake (offline) path still works.
- With `scripts/dev.sh up`, `POST /checkins/demo` then waiting past the window shows the alarm banner for a linked supporter; acknowledge and resolve work; safety settings save without 422.
- `scripts/ci.sh` passes.

### T458 — Review: person CheckInCard throws unhandled on 404/409 (late PIN after escalation hangs)
- status: done
- class: light
- priority: 0
- kind: bug
- source: reviewer
- deps: —
- area: web/src/checkin/CheckInCard.tsx, web/src/checkin/CheckInCard.test.tsx
- owner: ian-claude-standard-4
- claimed: 2026-10-18T02:40Z
- pr: #441
- rating: 5/5 clear

What: `CheckInCard.tsx` has no error handling on either API call. (1) `fetchMyCheckin(...).then(...)` has no `.catch`: `GET /checkins/active?person=` 404s (`UnknownPerson`) for anyone without safety settings, so every such person's home screen logs an unhandled rejection. (2) `handlePin` awaits `respondToCheckin`, which throws on any non-401 error; the backend answers 409 (`NotWaiting`) once the countdown has run out and the check-in escalated, so a late PIN leaves the pad stuck with no message. Fix in CheckInCard.tsx only (api.ts is in T457's area): catch on the fetch -> render nothing; wrap `handlePin` in try/catch -> on error replace the pad with a calm message like "This check-in has already gone to your supporters - they'll be in touch" (no hint about which PIN).
Acceptance: tests stub fetch with 404 on GET and 409 on respond; no unhandled rejection, the 409 message renders; `scripts/ci.sh` passes.

### T459 — Bug: web tests still flake under load: lazy screens vs findBy's 1 s default (MyRoutine again, AlertView.keyboard new)
- status: in-review
- class: light
- priority: 1
- kind: bug
- deps: —
- area: web/src/testSetup.ts, web/src/people/MyRoutine.test.tsx, web/src/alert/AlertView.keyboard.test.tsx
- source: tester
- owner: ian-claude-standard
- claimed: 2026-10-18T02:40Z
- pr: #444
- rating: 5/5 clear

What: `scripts/ci.sh` on main @3a522b0 (box load avg ~17) failed 2 web tests: `src/people/MyRoutine.test.tsx > says nobody else can see this when the person is watching themselves` (`findByRole('heading', {name: 'How this week looks'})` at line 45 timed out; same test T445 fixed) and `src/alert/AlertView.keyboard.test.tsx > tabs from the top of the alert to Confirmed and confirms it with Enter` (`Unable to find role="button" and name /play/i`, line 54/79). Both files pass in isolation (`cd web && npx vitest run src/alert/AlertView.keyboard.test.tsx src/people/MyRoutine.test.tsx`), and GitHub CI on main is green. Cause: T449 lazy-loads AlertView/ResidentDetail and T451 adds a lazy CheckInCard to MyRoutine; the first test to hit a lazy chunk pays the import cost, which exceeds testing-library's 1000 ms `findBy*` default on a busy box. Per-test fixes (T445) keep getting outrun by new lazy screens.
Expected: web tests pass on a loaded machine.
Interface: test-only. Raise the default once in `web/src/testSetup.ts` (`configure({ asyncUtilTimeout: 5000 })` from `@testing-library/react`), and/or preload the lazy modules in `beforeAll` of the two files. No product code changes.
Acceptance:
- `cd web && npx vitest run` passes while `stress`-style load runs (e.g. run it twice in parallel) with no findBy timeouts in these two files.
- `scripts/ci.sh` passes.

### T460 — Bug: person check-in card shows the oldest open check-in (0:00) when a person has several
- status: claimed
- class: light
- priority: 0
- kind: bug
- deps: T457, T458
- area: pipeline/src/routine_watch/checkin.py, pipeline/tests/test_checkin.py, web/src/checkin/api.ts, web/src/checkin/api.test.ts
- source: tester
- owner: ian-claude-heavy-2
- claimed: 2026-10-18T03:23Z

What: on main @3a522b0 with the stack up (`OFFLINE_MODE=true scripts/dev.sh up`), run `curl -XPOST localhost:8000/checkins/demo -H 'content-type: application/json' -d '{"person":"sam"}'` twice ~20 s apart (or once after an earlier one expired), then open the dashboard as **Myself**. `GET /checkins/active?person=sam` returns several records: the old ones in `state: "alarm"` with `seconds_left: null`, the new one `pending`. `fetchMyCheckin` (web/src/checkin/api.ts ~98) takes `list[0]`, so the card shows the stale one: countdown stuck at **0:00** with "I'm okay", not the live 20 s question. Its comment assumes "at most one is ever open for a person at a time", but `POST /checkins/demo` without `alert_id` starts a new record every call. A presenter re-triggering the check-in during the demo hits this.
Expected: a person has at most one open check-in, or the person screen shows the newest pending one.
Interface: preferred: in the store's `start` (checkin.py), if the person already has an open check-in, return it instead of creating another (same idempotency the alert path has). Also make `fetchMyCheckin` prefer a `pending` record, newest first. Don't change `contracts/`. Waits for T457 and T458 (share web/src/checkin/).
Acceptance:
- pytest: two `start()` calls for one person leave one open check-in.
- api.test.ts: given `[alarm(old), pending(new)]`, `fetchMyCheckin` returns the pending one.
- Manual: the repro above shows a running countdown; I'm okay + PIN 1234 → "Thanks, you're checked in".
- `scripts/ci.sh` passes.

### T461 — "For myself" mode: show the live camera/skeleton session on My routine
- status: todo
- class: standard
- priority: 0
- kind: bug
- source: ian
- deps: —
- area: web/src/people/MyRoutine.tsx, web/src/people/MyRoutine.test.tsx, web/src/people/people.css, web/src/App.tsx
- owner: —
- claimed: —
- pr: —

What: Ian, filming tonight: in "for myself" mode there is no way to see the live session (skeleton, task map, camera preview). `LiveScreen` is only rendered on the supervisor overview (App.tsx, "Live session" section). Add a **"Your session"** section to My routine that renders the same `<LiveScreen>` (same props: `onOpenAlert` opens the person's own alert view, `onSessionEnd` refreshes My routine), placed near the top under the summary, with person wording ("Start making tea when you're ready; only your skeleton is used"). The camera source and the "Show camera preview (this device only)" toggle must work exactly as on the supervisor page (LiveScreen already handles them). Don't change LiveScreen itself (another task owns web/src/live/).
Why: a person watching themselves is the point of SPEC §17; the demo needs the camera shot in that mode.
Acceptance: Vitest: My routine renders the live section (LiveScreen mocked); the supervisor page is unchanged; wording test passes; `cd web && npm test && npm run build`.

### T462 — Bug: `scripts/dev.sh up` dies with "unbound variable" on macOS bash 3.2 (empty VITE_HOST_ARGS)
- status: claimed
- class: light
- priority: 0
- kind: bug
- deps: —
- area: scripts/dev.sh
- owner: ian-claude-standard-3
- claimed: 2026-10-18T03:16Z
- pr: —

What: commit 5c4a0e1 (LAN=1 support) expands `"${VITE_HOST_ARGS[@]}"` under `set -euo pipefail`. On bash < 4.4 (macOS default /bin/bash 3.2, which `#!/usr/bin/env bash` picks up on a stock Mac) an empty array expansion is an "unbound variable" error, so `scripts/dev.sh up` without `LAN=1` fails to start the dashboard on a laptop.
Interface: in both `vite` exec lines in `start_web()` of `scripts/dev.sh`, replace `"${VITE_HOST_ARGS[@]}"` with `${VITE_HOST_ARGS[@]+"${VITE_HOST_ARGS[@]}"}`. Nothing else.
Acceptance:
- `bash -n scripts/dev.sh` passes; `scripts/dev.sh up` then `scripts/dev.sh down` still works with and without `LAN=1`.
- `scripts/ci.sh` passes.

### T463 — Generic step building blocks: any routine recognised live, no new code
- status: claimed
- class: heavy
- priority: 0
- kind: feature
- source: ian
- deps: —
- area: pipeline/src/routine_watch/recogniser.py, pipeline/src/routine_watch/actions.py, pipeline/src/routine_watch/tasks/graph.py, pipeline/src/routine_watch/tasks/tea.yaml, pipeline/src/routine_watch/tasks/meds.yaml, pipeline/src/routine_watch/routine_builder.py, pipeline/tests/test_actions.py, pipeline/tests/test_recogniser.py, pipeline/tests/test_routine_builder.py, docs/CODEMAP.md
- owner: ian-claude-heavy-3
- claimed: 2026-10-18T03:20Z
- pr: —

What: Ian wants custom routines (first one: a protein shake) recognised live. Today the recogniser's `RULES` table is hand-written for tea, so any other task recognises nothing. Add **reusable action primitives** that a task YAML step names, and make the recogniser interpret them for any graph.
Interface:
- `actions.py`: pure functions over the existing per-frame scene and contact state (reuse recogniser's `_Scene` / `_Contact` / `_held` / `_inside` helpers, moved here if needed): `pick_up(x)`, `put_into(x, y)` (x released inside y's box), `pour(x, into=y)` (x held and tilted/raised over y, or a `pouring` box between them), `open(x)` (hand contact on x and x's box changes aspect/size, or a `<x>_open` class), `close(x)`, `hold(x, seconds)`, `shake(x)` (x held and the holding wrist landmark oscillates: ≥3 direction reversals in 2 s above an amplitude threshold), `bring_to_face(x)` (x box near the nose/mouth pose landmarks), `return(x)`. Each returns the same `(strength, objects)` firing the rules use today, so confidences and `unclear` handling are unchanged.
- YAML: a step may add `action: {type: put_into, object: teabag, target: cup}` (also `pour`/`shake`/...). `graph.py` validates the action types and that every object it names is in the step's allowed objects or aliases. Steps without `action` keep using the existing tea rules, so nothing changes by default. Then **rewrite `tea.yaml` and `meds.yaml` with `action:`** and prove that recognition on the existing tests and scenarios is identical (same events and timestamps on the e2e scenarios; adjust the confidence constants only if a test says so).
- `routine_builder.py` (T437): drafts emit `action:` per step, picking from the primitive list (fake drafts too), so builder-made routines are recognisable.
Acceptance: unit tests per primitive, including `shake` from synthetic wrist oscillation; tea and meds e2e scenarios unchanged; a builder draft round-trips through `parse_task`; `scripts/ci.sh` passes.

### T464 — Protein shake routine: task graph, detector classes, synthetic scenarios
- status: todo
- class: standard
- priority: 0
- kind: feature
- source: ian
- deps: T463
- area: pipeline/src/routine_watch/tasks/protein_shake.yaml, pipeline/src/routine_watch/contracts.py, pipeline/src/routine_watch/detector.py, web/src/contracts.ts, pipeline/tests/test_protein_shake.py, tests/scenarios/protein_shake/, docs/DETECTOR.md
- owner: —
- claimed: —
- pr: —

What: Ian's custom routine, "Make a protein shake", as the second worked example of T463.
- New detector classes in `ObjectLabel` (and `web/src/contracts.ts`): `shaker`, `protein_tub`, `scoop`, plus `water_bottle` if there isn't already a water class (reuse meds' `water_jug`/`glass` if one fits). Aliases: `shaker_bottle`, `blender_bottle` → shaker; `protein`, `powder`, `tub` → protein_tub.
- `protein_shake.yaml`, steps with `action:`:
  1. get shaker: `pick_up(shaker)`
  2. open tub: `open(protein_tub)`
  3. scoop powder: `put_into(scoop, shaker)`, deps [get shaker, open tub], `once_only: false` (1–2 scoops is normal)
  4. add liquid: `pour(milk|water_bottle, into=shaker)`, deps [get shaker]; powder-first and liquid-first are both valid
  5. close lid: `close(shaker)`, deps [scoop powder, add liquid]
  6. shake: `shake(shaker)`, deps [close lid]
  7. close tub: `close(protein_tub)`, optional
  8. drink: `bring_to_face(shaker)`, optional
  Errors that fall out: shaking with the lid open (sequence), forgetting the powder (omission), scooping again after shaking (perseveration).
- `tests/scenarios/protein_shake/`: synthetic capture records (normal; omission of powder; lid-open shake; double pour) passed through the real pipeline, with expected errors.
- `docs/DETECTOR.md`: the labelling list for Ian's Roboflow project with these classes added to the tea ones, and how to train on his own GPU (yolo11n, cu128 PyTorch, export ONNX to `models/detector.onnx`).
Acceptance: the scenarios give the expected errors; the dashboard task map renders the graph (parallel powder/liquid branches); `scripts/ci.sh` passes.
