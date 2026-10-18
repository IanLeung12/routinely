# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: b22bb32

## Tasks

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
- status: done
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
- status: done
- class: light
- priority: 0
- kind: bug
- deps: T457, T458
- area: pipeline/src/routine_watch/checkin.py, pipeline/tests/test_checkin.py, web/src/checkin/api.ts, web/src/checkin/api.test.ts
- source: tester
- owner: ian-claude-heavy-2
- claimed: 2026-10-18T03:23Z
- pr: #446
- rating: 4/5 the preferred interface (always return the open check-in) would have kept the repro broken: after the 20 s window the only open one is a stuck alarm, so the card stays at 0:00 - the task's acceptance needed start() to hand back only a still-pending question

What: on main @3a522b0 with the stack up (`OFFLINE_MODE=true scripts/dev.sh up`), run `curl -XPOST localhost:8000/checkins/demo -H 'content-type: application/json' -d '{"person":"sam"}'` twice ~20 s apart (or once after an earlier one expired), then open the dashboard as **Myself**. `GET /checkins/active?person=sam` returns several records: the old ones in `state: "alarm"` with `seconds_left: null`, the new one `pending`. `fetchMyCheckin` (web/src/checkin/api.ts ~98) takes `list[0]`, so the card shows the stale one: countdown stuck at **0:00** with "I'm okay", not the live 20 s question. Its comment assumes "at most one is ever open for a person at a time", but `POST /checkins/demo` without `alert_id` starts a new record every call. A presenter re-triggering the check-in during the demo hits this.
Expected: a person has at most one open check-in, or the person screen shows the newest pending one.
Interface: preferred: in the store's `start` (checkin.py), if the person already has an open check-in, return it instead of creating another (same idempotency the alert path has). Also make `fetchMyCheckin` prefer a `pending` record, newest first. Don't change `contracts/`. Waits for T457 and T458 (share web/src/checkin/).
Acceptance:
- pytest: two `start()` calls for one person leave one open check-in.
- api.test.ts: given `[alarm(old), pending(new)]`, `fetchMyCheckin` returns the pending one.
- Manual: the repro above shows a running countdown; I'm okay + PIN 1234 → "Thanks, you're checked in".
- `scripts/ci.sh` passes.

### T461 — "For myself" mode: show the live camera/skeleton session on My routine
- status: done
- class: standard
- priority: 0
- kind: bug
- source: ian
- deps: —
- area: web/src/people/MyRoutine.tsx, web/src/people/MyRoutine.test.tsx, web/src/people/people.css, web/src/App.tsx
- owner: ian-claude-standard
- claimed: 2026-10-18T03:45Z
- pr: #447
- rating: 5/5 clear

What: Ian, filming tonight: in "for myself" mode there is no way to see the live session (skeleton, task map, camera preview). `LiveScreen` is only rendered on the supervisor overview (App.tsx, "Live session" section). Add a **"Your session"** section to My routine that renders the same `<LiveScreen>` (same props: `onOpenAlert` opens the person's own alert view, `onSessionEnd` refreshes My routine), placed near the top under the summary, with person wording ("Start making tea when you're ready; only your skeleton is used"). The camera source and the "Show camera preview (this device only)" toggle must work exactly as on the supervisor page (LiveScreen already handles them). Don't change LiveScreen itself (another task owns web/src/live/).
Why: a person watching themselves is the point of SPEC §17; the demo needs the camera shot in that mode.
Acceptance: Vitest: My routine renders the live section (LiveScreen mocked); the supervisor page is unchanged; wording test passes; `cd web && npm test && npm run build`.

### T462 — Bug: `scripts/dev.sh up` dies with "unbound variable" on macOS bash 3.2 (empty VITE_HOST_ARGS)
- status: done
- class: light
- priority: 0
- kind: bug
- deps: —
- area: scripts/dev.sh
- owner: ian-claude-standard-3
- claimed: 2026-10-18T03:16Z
- pr: #445
- rating: 5/5 clear

What: commit 5c4a0e1 (LAN=1 support) expands `"${VITE_HOST_ARGS[@]}"` under `set -euo pipefail`. On bash < 4.4 (macOS default /bin/bash 3.2, which `#!/usr/bin/env bash` picks up on a stock Mac) an empty array expansion is an "unbound variable" error, so `scripts/dev.sh up` without `LAN=1` fails to start the dashboard on a laptop.
Interface: in both `vite` exec lines in `start_web()` of `scripts/dev.sh`, replace `"${VITE_HOST_ARGS[@]}"` with `${VITE_HOST_ARGS[@]+"${VITE_HOST_ARGS[@]}"}`. Nothing else.
Acceptance:
- `bash -n scripts/dev.sh` passes; `scripts/dev.sh up` then `scripts/dev.sh down` still works with and without `LAN=1`.
- `scripts/ci.sh` passes.

### T463 — Generic step building blocks: any routine recognised live, no new code
- status: done
- class: heavy
- priority: 0
- kind: feature
- source: ian
- deps: —
- area: pipeline/src/routine_watch/recogniser.py, pipeline/src/routine_watch/actions.py, pipeline/src/routine_watch/tasks/graph.py, pipeline/src/routine_watch/tasks/tea.yaml, pipeline/src/routine_watch/tasks/meds.yaml, pipeline/src/routine_watch/routine_builder.py, pipeline/tests/test_actions.py, pipeline/tests/test_recogniser.py, pipeline/tests/test_routine_builder.py, docs/CODEMAP.md
- owner: ian-claude-heavy-3
- claimed: 2026-10-18T03:20Z
- pr: #448
- rating: 4/5 clear on the primitive list and the acceptance; it did not say that unifying milk/sugar/pour into one primitive must change their 0.85 base confidence (POUR is 0.90), nor name 'stir'/'take_out', which tea needs but the listed primitives do not cover

What: Ian wants custom routines (first one: a protein shake) recognised live. Today the recogniser's `RULES` table is hand-written for tea, so any other task recognises nothing. Add **reusable action primitives** that a task YAML step names, and make the recogniser interpret them for any graph.
Interface:
- `actions.py`: pure functions over the existing per-frame scene and contact state (reuse recogniser's `_Scene` / `_Contact` / `_held` / `_inside` helpers, moved here if needed): `pick_up(x)`, `put_into(x, y)` (x released inside y's box), `pour(x, into=y)` (x held and tilted/raised over y, or a `pouring` box between them), `open(x)` (hand contact on x and x's box changes aspect/size, or a `<x>_open` class), `close(x)`, `hold(x, seconds)`, `shake(x)` (x held and the holding wrist landmark oscillates: ≥3 direction reversals in 2 s above an amplitude threshold), `bring_to_face(x)` (x box near the nose/mouth pose landmarks), `return(x)`. Each returns the same `(strength, objects)` firing the rules use today, so confidences and `unclear` handling are unchanged.
- YAML: a step may add `action: {type: put_into, object: teabag, target: cup}` (also `pour`/`shake`/...). `graph.py` validates the action types and that every object it names is in the step's allowed objects or aliases. Steps without `action` keep using the existing tea rules, so nothing changes by default. Then **rewrite `tea.yaml` and `meds.yaml` with `action:`** and prove that recognition on the existing tests and scenarios is identical (same events and timestamps on the e2e scenarios; adjust the confidence constants only if a test says so).
- `routine_builder.py` (T437): drafts emit `action:` per step, picking from the primitive list (fake drafts too), so builder-made routines are recognisable.
Acceptance: unit tests per primitive, including `shake` from synthetic wrist oscillation; tea and meds e2e scenarios unchanged; a builder draft round-trips through `parse_task`; `scripts/ci.sh` passes.

### T464 — Protein shake routine: task graph, detector classes, synthetic scenarios
- status: done
- class: standard
- priority: 0
- kind: feature
- source: ian
- deps: T463
- area: pipeline/src/routine_watch/tasks/protein_shake.yaml, pipeline/src/routine_watch/contracts.py, pipeline/src/routine_watch/detector.py, web/src/contracts.ts, pipeline/tests/test_protein_shake.py, tests/scenarios/protein_shake/, docs/DETECTOR.md
- owner: ian-claude-standard
- claimed: 2026-10-18T04:11Z
- pr: #450
- rating: 5/5 clear

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

### T465 — Bug: person's check-in card never shows a check-in that starts while My routine is open (fetches once on mount)
- status: done
- class: light
- priority: 1
- kind: bug
- deps: —
- area: web/src/checkin/CheckInCard.tsx, web/src/checkin/CheckInCard.test.tsx
- source: tester
- owner: ian-claude-heavy-3
- claimed: 2026-10-18T04:17Z
- pr: #449
- rating: 5/5 clear

What: on main @3976dad with the stack up (`OFFLINE_MODE=true scripts/dev.sh up`), open the dashboard, pick **Myself** (My routine), then `curl -XPOST localhost:8000/checkins/demo -H 'content-type: application/json' -d '{"person":"sam"}'`. `GET /checkins/active?person=sam` returns the pending check-in, but My routine shows no "Can you check in?" card; it appears only after a page reload. `CheckInCard` (web/src/checkin/CheckInCard.tsx ~45) calls `fetchMyCheckin` once in `useEffect([personId])` and never again, unlike the supporter `AlarmBanner`, which re-fetches every second. Since T461 the live session runs on My routine, so the SPEC §18 story (session flagged → person asked to check in) happens on this very screen and the person never sees the question; the 20 s window runs out and supporters are alarmed.
Expected: a check-in that starts while My routine is open appears within ~2 s with its countdown, no reload.
Interface: simplest: poll `fetchMyCheckin` every 1–2 s while no check-in is shown (stop during the PIN/thanks stages), same pattern as AlarmBanner. Subscribing to `/ws/live?checkin_person=` is also fine. Don't change `contracts/` or the API.
Acceptance:
- CheckInCard.test.tsx: first fetch returns null, a later one returns a pending check-in → the card appears (fake timers).
- Manual: the repro above shows the card with a running countdown without reloading; I'm okay + PIN 1234 → "Thanks, you're checked in".
- `scripts/ci.sh` passes.

### T466 — Bug: Live screen only offers tea + meds; protein shake and saved routines can't be watched
- status: done
- class: standard
- priority: 0
- kind: bug
- source: ian
- deps: —
- area: web/src/live/LiveScreen.tsx, web/src/live/LiveScreen.test.tsx, web/src/live/LiveScreen.keyboard.test.tsx, web/src/live/liveScreen.css, web/src/routines/api.ts, pipeline/src/routine_watch/live_camera.py, pipeline/src/routine_watch/api_live.py, pipeline/tests/test_live_camera.py, pipeline/tests/test_api_live.py
- owner: hermes
- claimed: 2026-10-18T06:57Z
- pr: —
- note: Pushed directly to main by Hermes (Ian asked for speed).

What: Ian, filming before 13:00 UTC: he saved a routine in the builder and it doesn't appear on the Live screen; the built-in protein shake doesn't either. `LiveScreen.tsx` hardcodes `TASKS` = tea + meds, and the camera path's `load_task(task)` only reads `tasks/<name>.yaml`.
Interface:
- Web: build the "Routine to watch" options from `GET /routines` (built-ins: tea, meds, protein_shake; then saved ones), falling back to the current tea/meds list if the API is unreachable (offline demo). Keep tea the default and keep `?task=` working for any routine id. A routine with a recorded scenario (`tea_skip_teabag_pour_twice`, `meds_skip_water`, `protein_shake_omit_powder` from tests/scenarios) plays it when there is no camera; one without a scenario shows "Watch this routine with the camera: run scripts/camera.sh" instead of an empty card when no camera is attached. With a camera (`?source=camera`), any routine is passed as `task=<id>`. A SegmentedControl won't fit many routines: switch to a select/listbox when there are more than 3.
- Pipeline: the camera session resolves `task` as a built-in `load_task(name)` first, then the saved routines store (`routine_builder.get_routine_store().get(id)` → `parse_task_data(routine.graph)`); unknown → the same error as today. Keep the import out of `tasks/graph.py` (no cycle); do it in `live_camera.py`/`api_live.py`. Built-in routine ids vs file names: accept both (e.g. `tea` and the graph id).
Acceptance: tests: options come from /routines incl. protein shake + a saved one; offline fallback; camera session starts for a saved routine id and for `protein_shake`; `cd web && npm test && npm run build`; `scripts/ci.sh --changed`.

### T467 — Bug: main red: App.test.tsx expects "Making tea" but the Live picker now shows routine titles ("Make tea")
- status: done
- class: light
- priority: 0
- kind: bug
- deps: —
- area: web/src/App.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-18T07:24Z
- pr: —
- note: Already fixed: 60fa686 (merged right after the cited CI run, b22bb32) corrected LiveScreen.tsx's label lookup. Verified on current origin/main (e38f907): npx vitest run src/App.test.tsx and full npm test both pass (137/137 files, 990 tests), 5x repeated with no flakiness. No code/test change needed; opened no PR.
- rating: 2/5 task was based on a stale CI run; a concurrent commit (60fa686) had already fixed the root cause by the time I claimed it

What: Since 6ea3d97 (T466, Live picker built from `GET /routines`), the `web/src/App.test.tsx` test "shows the live routine picker with making tea selected by default" fails on main: the picker renders "Make tea" / "Take medication with water", not "Making tea" / "Medication with water". It is the only failing test file (CI run 39107150618, 136/137 pass).
Interface: read `web/src/App.test.tsx` (lines ~35-42) and `web/src/live/LiveScreen.tsx` (how options/labels are built, offline fallback). Update the test only: assert the tea option is selected by default using the label LiveScreen actually renders in this test's setup (the picker may be a segmented control, or a select when there are more than 3 routines). Do not change LiveScreen.tsx.
Acceptance:
- `cd web && npx vitest run src/App.test.tsx` passes; `cd web && npm test` passes.
- `scripts/ci.sh --changed` passes.
