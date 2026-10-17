# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: a825bee

## Tasks

### T149 — API: GET /monitoring and PUT /rooms/{room}/monitoring
- status: in-review
- class: standard
- priority: 3
- kind: feature
- deps: T148
- area: pipeline/src/routine_watch/api.py, pipeline/tests/test_api_monitoring.py (new)
- source: proposed
- owner: ian-claude-standard
- claimed: 2026-10-17T11:25Z
- pr: #226
- note: released by ian-claude-standard-2: run ended without progress; partial work on branch task/T149-wip-1051: start from it (git switch task/T149-wip-1051 && git merge origin/main)
- rating: 4/5 clear, except the WIP branch noted in the task had drifted far from main (unrelated demo.py/web diffs) and needed re-applying just the api.py/test slice onto fresh main

What: Expose the T148 store so the dashboard's pause switch is real. While a room is paused, `/ws/live` for a scenario whose resident is in that room sends one `{"type": "paused", "room": ...}` message and closes instead of streaming frames (no camera data processed).
Interface: `GET /monitoring` → `{"paused_rooms": [...]}`; `PUT /rooms/{room}/monitoring` body `{"on": bool}` → `{"room": str, "on": bool}`; uses `monitoring.get_monitoring_store()`. Room→resident comes from `demo.demo_residents()`; unknown room → 404.
Acceptance:
- tests: default empty, pause/resume round trip, 404 for unknown room, paused live session gets the `paused` message and no frames (TestClient websocket); store reset between tests.
- `scripts/ci.sh` passes.

### T179 — Docs: CODEMAP note that handoff reuses the alert's errors
- status: todo
- class: light
- priority: 3
- kind: docs
- deps: —
- area: docs/CODEMAP.md
- owner: —
- claimed: —
- pr: —

What: T166 (PR #159) made `alerts.session_id_for`, `task_errors`, `distinct_clauses` and `normal_error_rate` public so `handoff.py` writes its summary from the same evidence as the alert, against that resident's own baseline. CODEMAP notes don't say so.
Interface: Read only `docs/CODEMAP.md`, `git show e4f8fe1 --stat` and the module docstrings of `pipeline/src/routine_watch/alerts.py` and `handoff.py`. Edit notes only, not the generated file list.
Acceptance:
* 2-4 line note next to the existing handoff/alert notes naming the four shared functions and why (same steps, same times, same baseline).
* Also one line that handoff rows open the resident's alert by looking up the id in `GET /alerts` (T152, `web/src/handoff/Handoff.tsx` `alertByResident`).
* No other file changed.

### T187 — Test: App shows the live routine picker with tea selected
- status: todo
- class: light
- priority: 3
- kind: test
- deps: —
- area: web/src/App.test.tsx
- owner: —
- claimed: —
- pr: —

What: T161 swapped `LiveSession` for `LiveScreen` in `App.tsx`; nothing at app level checks the picker is there. Add one test.
Interface: Read only `web/src/App.tsx`, `web/src/App.test.tsx`, `web/src/live/LiveScreen.tsx`. Reuse App.test's existing fetch/websocket mocks.
Acceptance:
* Test: the "Routine to watch" group renders with "Making tea" pressed and "Medication with water" not pressed.
* `scripts/ci.sh` passes.

### T192 — /demo/reset also resumes paused room monitoring
- status: todo
- class: light
- priority: 2
- kind: improvement
- deps: T149
- area: pipeline/src/routine_watch/api.py (demo_reset only), pipeline/tests/test_api_demo_reset.py
- owner: —
- claimed: —
- pr: —

What: After T149 a rehearsal can pause a room, and `/demo/reset` leaves it paused. Make reset also call the monitoring store's `reset()`.
Interface: read `pipeline/src/routine_watch/api.py` (`demo_reset`), `pipeline/src/routine_watch/monitoring.py` (`get_monitoring_store`, `MonitoringStore.reset`), `pipeline/tests/test_api_demo_reset.py`.
Acceptance:
- Test: PUT a room to paused, POST /demo/reset, GET /monitoring shows no paused rooms.
- `cd pipeline && pytest tests/test_api_demo_reset.py` and `scripts/ci.sh` pass.

### T198 — Docs: DEMO.md mentions opening an alert from the shift handoff
- status: todo
- class: light
- priority: 3
- kind: docs
- deps: —
- area: docs/DEMO.md
- owner: —
- claimed: —
- pr: —

What: Since T152 (PR #177), each handoff row with an alert pending review has an "Open alert" button. The runbook's handoff step doesn't say so.
Interface: Read only `docs/DEMO.md` and `web/src/handoff/Handoff.tsx` (the `Open alert` button). Add 1-3 lines to the handoff step.
Acceptance:
* DEMO.md says the presenter can click "Open alert" on Mrs. K's handoff row to reach her alert.
* Wording says "flags a change for review"; no "diagnose". No other file changed.

### T203 — Shift handoff: print-friendly layout
- status: todo
- class: light
- priority: 3
- kind: feature
- source: proposed
- deps: —
- area: web/src/handoff/handoff.css, web/src/handoff/Handoff.tsx, web/src/handoff/Handoff.test.tsx
- owner: —
- claimed: —
- pr: —

What: nurses hand off on paper; a "Print" button plus `@media print` rules (hide nav/banner/buttons, black on white, no row breaks across pages) make the handoff usable as a printout.
Interface: read only the three area files. Button calls `window.print()`.
Acceptance:
- "Print handoff" button; test mocks window.print and asserts it's called on click
- handoff.css has an `@media print` block hiding `.no-print` elements and `break-inside: avoid` on rows
- `cd web && npm test -- Handoff` passes; `scripts/ci.sh` passes

### T212 — Docs: CODEMAP note that alerts read live session errors
- status: todo
- class: light
- priority: 3
- kind: docs
- deps: T179
- area: docs/CODEMAP.md
- owner: —
- claimed: —
- pr: —

What: T155 (#192) made `alerts.task_errors` return the real `error_events` of a session recorded live by `session_log.py` (keeping its own `session_id`), and only synthesise placeholder errors for the seeded history. Add 2–3 lines to the alerts/session_log notes in `docs/CODEMAP.md` saying so.
Interface: read `pipeline/src/routine_watch/alerts.py` (`session_id_for`, `task_errors` docstrings) and `pipeline/src/routine_watch/session_log.py`. Edit notes only, not the generated file list.
Acceptance:
- Note present and accurate; `scripts/ci.sh` passes.

### T222 — Review: Copy summary says "Change flagged" for slow-trend alerts
- status: done
- class: light
- priority: 1
- kind: bug
- deps: T221
- area: web/src/alert/alertText.ts, web/src/alert/alertText.test.ts
- owner: ian-claude
- claimed: 2026-10-17T10:48Z
- pr: #217
- source: reviewer
- rating: 5/5 clear - the task named the exact file, the exact conditional and the two test assertions

What: `alertText` (T199/T211, #189/#198) always writes the line `Change flagged for review`, but `Alert.kind` can be `'trend'`, which the overview labels `Slow trend for review` (`web/src/App.tsx` ~line 112). A nurse pasting a trend alert into the chart records the wrong kind of finding.
Interface: read `web/src/alert/alertText.ts`, `web/src/alert/alertText.test.ts`, and `AlertKind` in `web/src/contracts.ts`. Replace the fixed string with `alert.kind === 'trend' ? 'Slow trend for review' : 'Change flagged for review'`.
Acceptance:
* test: a `kind: 'trend'` alert's copied text contains `Slow trend for review` and not `Change flagged`; a change alert keeps `Change flagged for review`
* `cd web && npm test` passes

### T223 — SessionSummary: CSS file instead of inline <style>, reuse formatDuration
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/live/SessionSummary.tsx, web/src/live/sessionSummary.css, web/src/live/SessionSummary.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T10:27Z
- pr: #210
- rating: 5/5 clear

What: `SessionSummary.tsx` (from PR #204) injects a `<style>` block, against the CSS-class cleanup done in T214/T215 (see `web/src/resident/driftCard.css` for the pattern), and re-implements `formatDuration` that `web/src/resident/format.ts` already exports.
Interface: move the two rules into `web/src/live/sessionSummary.css` imported by the component; use `formatDuration` from `../resident/format.ts` only if its output matches the current strings in `SessionSummary.test.tsx`, otherwise keep the local one and add a one-line comment why.
Acceptance:
- no `<style>` element left in `SessionSummary.tsx`; rendered text unchanged
- existing SessionSummary tests pass unchanged (only add, don't loosen)
- `cd web && npx vitest run src/live/SessionSummary.test.tsx` and `scripts/ci.sh` pass

### T224 — LiveScreen: CSS file instead of inline <style>
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/live/LiveScreen.tsx, web/src/live/liveScreen.css
- owner: ian-claude-light-2
- claimed: 2026-10-17T10:40Z
- pr: #216
- rating: 5/5 clear

What: `web/src/live/LiveScreen.tsx` (line ~31) injects a `<style>` block; move it to a CSS file like `web/src/resident/driftCard.css` (T215).
Interface: new `web/src/live/liveScreen.css` imported by `LiveScreen.tsx`; same class names, same rules.
Acceptance:
- no `<style>` element left in `LiveScreen.tsx`; no visual or text change
- `cd web && npx vitest run src/live` and `scripts/ci.sh` pass

### T225 — LiveSession: CSS file instead of inline <style>
- status: todo
- class: light
- priority: 2
- kind: improvement
- deps: T220
- area: web/src/live/LiveSession.tsx, web/src/live/liveSession.css
- owner: —
- claimed: —
- pr: —

What: `web/src/live/LiveSession.tsx` (line ~140) injects a `<style>` block; move it to a CSS file like `web/src/resident/driftCard.css` (T215). Waits for T220, which edits the same file.
Interface: new `web/src/live/liveSession.css` imported by `LiveSession.tsx`; same class names, same rules.
Acceptance:
- no `<style>` element left in `LiveSession.tsx`; no visual or text change
- `cd web && npx vitest run src/live` and `scripts/ci.sh` pass

### T226 — Ghost replay: say the figure is a stand-in for demo recordings
- status: done
- class: light
- priority: 2
- kind: feature
- deps: —
- area: web/src/evidence/GhostReplay.tsx, web/src/evidence/GhostReplay.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T11:17Z
- pr: #221
- note: released by ian-claude-standard: run ended without progress; partial work on branch task/T226-wip-1052: start from it (git switch task/T226-wip-1052 && git merge origin/main)
- rating: 4/5 clear, but task was already mostly implemented on the WIP branch handed to me

What: Since T207 (PR #205) the demo's recordings get a made-up body (`pipeline/src/routine_watch/stick_figure.py`) so the ghost replay has something to draw. A judge or nurse should not mistake it for tracked motion, so add a small muted caption under the replay: "Demo recording: the body is drawn as a stand-in; the hand follows the tracked hand box."
Interface: read `web/src/evidence/GhostReplay.tsx` and its test only. Caption is plain text under the existing canvas/caption row, using existing muted text tokens (`var(--muted)`), readable on the dark card (see T208 for the contrast bug to avoid).
Acceptance:
- caption renders under the ghost replay; test asserts the text
- `cd web && npx vitest run src/evidence` and `scripts/ci.sh` pass

### T227 — Test: stand-in skeleton never changes what the recogniser reads
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_stick_figure.py
- owner: ian-claude-light-2
- claimed: 2026-10-17T11:22Z
- pr: #224
- note: released by ian-claude-light-2: run ended without progress; partial work on branch task/T227-wip-1053: start from it (git switch task/T227-wip-1053 && git merge origin/main)
- rating: 5/5 clear

What: `evidence._with_skeleton` adds poses/hands to box-only frames and promises "a frame read by the recogniser still says exactly what it did before". Pin that promise for every frame-level scenario.
Interface: read `pipeline/src/routine_watch/evidence.py` (`_with_skeleton`), `pipeline/src/routine_watch/stick_figure.py`, `pipeline/src/routine_watch/replay.py` (`load_scenario`, `SCENARIOS_DIR`). For each scenario dir under `tests/scenarios/` with a `frames.jsonl`, assert the recogniser's step/error output on the original frames equals the output on `_with_skeleton`-mapped frames (use whatever function `replay.py` already uses to turn frames into errors).
Acceptance:
- parametrized over all frame scenarios; fails if a stand-in landmark changes any error
- `cd pipeline && python -m pytest tests/test_stick_figure.py -q` and `scripts/ci.sh` pass

### T228 — Bug: flaky "moves focus to the h1" tests turn main CI red
- status: done
- class: light
- priority: 0
- kind: bug
- deps: —
- area: web/src/alert/AlertView.test.tsx, web/src/resident/ResidentDetail.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T10:39Z
- pr: #215
- rating: 5/5 clear

What: `main` CI failed on f679686 and 495a460 (and a rerun) in `AlertView.test.tsx > moves focus to the h1 once the alert loads` (T213, #202); the same race shows locally in `ResidentDetail.test.tsx > moves focus to the h1 once the resident loads` (T217, #208). The tests check `document.activeElement` right after `findByRole('heading')` resolves, but focus is set in an effect that can land a tick later under CI load. Also seen once: `shows a loading state for the evidence card…` timing out on `findByText('No replay available')` at the 1 s default.
Interface: read only the two test files. In both focus tests, replace the bare `expect(document.activeElement).toBe(heading)` with `await waitFor(() => expect(document.activeElement).toBe(heading))`. In AlertView's evidence loading-state test, wrap `releases.forEach(...)` in `await act(async () => { ... })` before the `findByText`. Do not change component code or loosen any other assertion.
Acceptance:
- `cd web && for i in 1 2 3 4 5; do npx vitest run || break; done` passes all 5 full runs
- `scripts/ci.sh` passes

### T229 — Test: PatternList fixtures use unique pattern ids (no duplicate-key warning)
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/alert/PatternList.test.tsx
- owner: —
- claimed: —
- pr: —

What: `PatternList.test.tsx > never uses diagnostic wording` renders two `pattern()` fixtures that both have `pattern_id: 'delirium'`, so React logs "Encountered two children with the same key" in every CI run, hiding real warnings.
Interface: read `web/src/alert/PatternList.test.tsx` only. Give the second fixture a different `pattern_id` (e.g. `pattern({ pattern_id: 'infection', urgency: 'urgent' })`); fix any other test in the file that renders duplicate ids the same way.
Acceptance:
- `cd web && npx vitest run src/alert/PatternList.test.tsx 2>&1 | grep -c "same key"` prints 0; all tests pass
- `scripts/ci.sh` passes

### T230 — Review: live summary's "usually ~" averages the resident's whole history, drift included
- status: done
- class: standard
- priority: 1
- kind: bug
- source: reviewer
- deps: T220
- area: pipeline/src/routine_watch/demo.py, pipeline/src/routine_watch/api.py, web/src/live/LiveSession.tsx, web/src/resident/types.ts
- owner: ian-claude
- claimed: 2026-10-17T11:02Z
- pr: #222
- rating: 5/5 clear - the interface named the exact fields and where to compute them; only thing not mentioned was alerts.py's Baseline(**resident['baseline']) splat, which breaks when the payload grows

What: `useResidentBaseline` in `web/src/live/LiveSession.tsx` averages `duration_s` and error totals over *every* non-assisted session of mrs-k, including the recent bad days that triggered her flag. So the end-of-session "usually ~Xs / ~N errors" is inflated by exactly the change we're flagging, and disagrees with the pipeline's baseline, which is anchored to the earliest `BASELINE_DAYS` (demo.py, SPEC §8 beat 6). It also re-implements baseline logic in the web.
Interface: in `demo.py`, where the resident baseline is built from the early window, also compute `usual_duration_s` and `usual_errors` (mean over the same early, non-assisted sessions) and serve them inside `baseline` from `GET /residents/{id}`. Add both as optional fields to `Baseline` in `web/src/resident/types.ts`; have `LiveSession.tsx` read them instead of averaging `sessions`, and delete `average`/`sessionErrorTotal`.
Acceptance:
- pytest: mrs-k's `baseline.usual_errors` equals the mean over her first `BASELINE_DAYS` own sessions, and is lower than the whole-history mean
- `LiveSession.test.tsx` shows the "usually" values from the mocked `baseline`, not from `sessions`
- `scripts/ci.sh` passes

### T231 — Test: integration.sh dashboard check retries instead of failing on a cold Vite start
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: scripts/integration.sh
- owner: —
- claimed: —
- pr: —
- source: integration

What: The integration run on main @ 60dce5a failed with "dashboard did not render (no 'Routine Watch' in DOM)", but the orchestrator reran `scripts/integration.sh` on the same sha at 10:52 UTC and it passed, so it is a flake (likely the headless-Chrome DOM dump racing Vite's first compile). Make the check robust, not looser.
Interface: in `scripts/integration.sh`, the "Rendered dashboard" block (around line 45): retry the `--dump-dom` up to 3 times with a 3 s sleep between attempts before calling `fail`; keep both existing grep checks unchanged.
Acceptance:
- a slow first render no longer fails the run; a dashboard that never renders still fails with the same message
- `scripts/integration.sh` prints OK and `scripts/ci.sh` passes

### T232 — Bug: alert feedback buttons (Confirmed / False alarm / cause) render unstyled
- status: done
- class: light
- priority: 1
- kind: bug
- deps: —
- area: web/src/alert/FeedbackButtons.tsx, web/src/alert/alert.css, web/src/alert/FeedbackButtons.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T11:06Z
- pr: #218
- source: tester
- rating: 5/5 clear

What: On the alert view (main 13032a4), the Feedback section's "Confirmed" / "False alarm" and the "What was it?" cause buttons show as tiny browser-default buttons (white border, small text), unlike every other button on the dashboard. "Confirmed" is the demo's closing click (SPEC §10) and is easy to miss. `.feedback-button` only has an `[aria-pressed='true']` rule in `alert.css`; there is no base style.
Repro: `OFFLINE_MODE=true scripts/dev.sh up`, open http://localhost:5173, let the live tea session finish, click "Open alert", scroll to Feedback.
Expected: buttons use the shared `Button` from `web/src/ui/Button.tsx` (or the `.btn` / `.btn--secondary` classes in `index.css`) at normal size, pressed state still visible. Actual: unstyled default buttons.
Interface: in `FeedbackButtons.tsx` render the buttons with `ui/Button` (or add `btn btn--secondary` classes); keep `aria-pressed` and the existing pressed-state rule.
Acceptance:
- Confirmed / False alarm / cause buttons share the dashboard button look; pressed one stays visibly distinct (not colour alone)
- existing FeedbackButtons tests pass; `scripts/ci.sh` passes

### T233 — Test: de-flake DemoBanner reset test under load
- status: done
- class: light
- priority: 1
- kind: test
- deps: —
- area: web/src/ui/DemoBanner.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T11:07Z
- pr: #219
- rating: 5/5 clear

What: PR #217 reported `DemoBanner.test.tsx` (reset cases from T218) failing intermittently in full `scripts/ci.sh` runs while passing alone. Make its async assertions wait instead of checking state right after a click/findBy.
Interface: read `web/src/ui/DemoBanner.tsx` and `web/src/ui/DemoBanner.test.tsx` only. Wrap post-click assertions (disabled state, error text appearing/disappearing) in `await waitFor(...)` or use `findBy*`/`waitForElementToBeRemoved`; resolve fake `onReset` promises inside `act`.
Acceptance:
- No behaviour change in DemoBanner.tsx.
- `cd web && for i in 1 2 3 4 5; do npm test -- --run DemoBanner || exit 1; done` passes, and `scripts/ci.sh` passes.

### T234 — Unit overview: usable at phone width (375 px)
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/index.css (overview rules only: .unit-filter*, .resident-list, .resident-row, .resident-open*, .resident-identity/name/room/status/pattern), web/src/overview/overview.css (new), web/src/overview/UnitOverview.tsx, web/src/overview/UnitOverview.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T11:12Z
- pr: #225
- rating: 5/5 clear

What: Nurses check the board on a phone on the floor, but there are no responsive rules anywhere in web/ (no `@media` except reduced-motion). Move the overview's rules out of index.css into `overview/overview.css` (imported by UnitOverview.tsx) and add a `@media (max-width: 480px)` block so each resident row stacks name/room, status chip + top pattern, and sparkline without horizontal scroll.
Interface: `web/src/overview/overview.css`; UnitOverview.tsx adds `import './overview.css'`. No markup or class name changes beyond what the stacking needs.
Acceptance:
- No horizontal scroll on the overview at 375 px wide; filter buttons wrap and stay ≥44 px tall tap targets.
- Desktop layout unchanged (same rules, just moved).
- Existing UnitOverview tests still pass; `scripts/ci.sh` passes.
- PR body notes the viewport widths checked.

### T236 — Review: live session_end flag/alert_id can disagree with the resident's real status (alert 404)
- status: claimed
- class: standard
- priority: 1
- kind: bug
- source: reviewer
- deps: —
- area: pipeline/src/routine_watch/live.py, pipeline/tests/test_live.py
- owner: ian-claude
- claimed: 2026-10-17T11:24Z
- pr: —

What: `session_messages` (live.py ~L282-305) sends `flag` from `score_session`, which judges against the *scenario's* `expected.history`, and sets `alert_id = f"alert-{resident_id}"` whenever that flag is true. But `/alerts` only has an alert when the resident (mrs-k) is flagged over her own history (`_resident_flagged`). Reproduced with `session_log.reset()` + one live run for mrs-k: `tea_kettle_twice` → `flag: True, alert_id: alert-mrs-k`, resident status `watch`, `GET /alerts/alert-mrs-k` → 404 ("View alert" dead-ends). `tea_no_kettle` → `flag: False` while she is `flagged` on the dashboard. The two demo picks (tea_skip_teabag_pour_twice, meds_skip_water) happen to agree, so this bites any other scenario or the camera path.
Interface: after `_record(...)`, compute `resident_name = _resident_flagged(resident_id)` once (reuse it for the push check) and send `flag = resident_name is not None` and `alert_id = f"alert-{resident_id}" if resident_name else None`, so the live screen says what the dashboard says. Keep the per-recording score as-is. Update the module docstring note about `flag` (~L75).
Acceptance:
- New test in `pipeline/tests/test_live.py`: for mrs-k after reset, `tea_kettle_twice` and `tea_no_kettle` each end with `alert_id` non-null iff `GET /alerts/{alert_id}` returns 200 (TestClient), and `flag` equals the resident's status == flagged.
- Existing live/notify tests still pass; `scripts/ci.sh` passes.

### T235 — Live screen and task map: usable at phone width (375 px)
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/live/liveScreen.css, web/src/live/taskMap.css
- owner: ian-claude-standard
- claimed: 2026-10-17T11:16Z
- pr: #223
- rating: 5/5 clear

What: The live session view (routine picker, task map of steps, skeleton panel) has no responsive rules. Add `@media (max-width: 480px)` blocks to the two CSS files so the routine picker wraps, the task-map steps stack in one column and the skeleton panel scales to the screen width, so a nurse can follow a live session on a phone.
Interface: CSS only, in the two listed files. Don't touch LiveSession.tsx / liveSession.css (T225, T230 work there).
Acceptance:
- No horizontal scroll on the live screen at 375 px; step labels and error times stay readable (no text below var(--text-sm)).
- Desktop layout unchanged.
- `scripts/ci.sh` passes; PR body notes the viewport widths checked.

### T237 — Test: de-flake AlertView "loading state for the evidence card" test under load
- status: in-review
- class: light
- priority: 1
- kind: test
- deps: —
- area: web/src/alert/AlertView.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T11:27Z
- pr: #227
- rating: 5/5 clear

What: `AlertView > shows a loading state for the evidence card before the replay resolves` fails intermittently under full-suite parallelism (PR #221 CI run 39028279950, and earlier per LESSONS): `findByText('No replay available')` times out at the default 1000 ms after the deferred replay fetch is released. Make it deterministic without changing app code.
Interface: read only `web/src/alert/AlertView.test.tsx` and `web/src/evidence/ReplayPlayer.tsx` (renders `No replay available` when frames are empty). Fix the test only, e.g. release inside `act` then `await waitFor(() => expect(screen.getByText('No replay available')).toBeTruthy(), { timeout: 3000 })`, and make sure any other `/sessions/` fetches the view makes also resolve (inspect `fetchMock.mock.calls`).
Acceptance:
- No app code changed; only AlertView.test.tsx.
- `cd web && for i in 1 2 3 4 5; do npx vitest run --pool=threads --maxWorkers=1 src/alert/AlertView.test.tsx || exit 1; done` passes, and `scripts/ci.sh` passes.

### T238 — Alert view: usable at phone width (375 px)
- status: claimed
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/alert/alert.css, web/src/alert/PatternList.css
- owner: ian-claude-standard-2
- claimed: 2026-10-17T11:32Z
- pr: —

What: Nurses open alerts from a phone (push alert, SPEC §5 nice-to-have 3), but the alert screen has no responsive rules. Add a `@media (max-width: 480px)` block to `alert.css` and `PatternList.css` (same breakpoint as T235's `live/liveScreen.css`) so the header, error list, pattern cards, suggested checks and feedback buttons stack without horizontal scroll.
Interface: CSS only in the two files listed; no markup or class name changes. If the ghost replay figure (styled in `web/src/index.css`) still overflows, note it in the PR instead of editing index.css.
Acceptance:
- No horizontal scroll on `/alerts/<id>` at 375 px; feedback buttons wrap and stay ≥44 px tall tap targets.
- Desktop layout unchanged.
- `scripts/ci.sh` passes; PR body notes the viewport widths checked (e.g. Playwright screenshot at 375 and 1280).

### T239 — Resident detail: usable at phone width (375 px)
- status: todo
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/driftCard.css, web/src/resident/heatCalendar.css, web/src/resident/resident.css (new), web/src/resident/ResidentDetail.tsx
- owner: —
- claimed: —
- pr: —

What: The resident detail screen (baseline chart, slow-drift card, heat calendar, sessions, care records) has no responsive rules. Add `@media (max-width: 480px)` rules so it reads on a phone: chart and calendar scale to the card width (or scroll inside their own card, never the page), lists stack.
Interface: CSS in the listed files; `resident.css` is new and imported by ResidentDetail.tsx for any rules not owned by DriftCard/HeatCalendar. Don't move rules out of `web/src/index.css` (T234 owns that pattern for the overview); add overrides instead.
Acceptance:
- No page-level horizontal scroll on `/residents/mrs-k` at 375 px; desktop layout unchanged.
- Existing resident tests still pass; `scripts/ci.sh` passes; PR body notes the widths checked.

### T240 — Pattern library: usable at phone width (375 px)
- status: todo
- class: light
- priority: 3
- kind: improvement
- deps: —
- area: web/src/patterns/PatternLibrary.css
- owner: —
- claimed: —
- pr: —

What: The pattern library page has no responsive rules. Add a `@media (max-width: 480px)` block to `PatternLibrary.css` so each pattern card's signals, rule-outs and sources stack in one column with no horizontal scroll.
Interface: read only `web/src/patterns/PatternLibrary.tsx` (for class names) and `web/src/patterns/PatternLibrary.css`; for the breakpoint style copy `web/src/live/taskMap.css`'s `@media (max-width: 480px)` block. CSS only, no markup changes.
Acceptance:
- No horizontal scroll on the pattern library at 375 px; desktop unchanged.
- `scripts/ci.sh` passes.

### T241 — Test: no user-facing web copy says "diagnose" or "has <condition>"
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/wording.test.ts (new)
- owner: —
- claimed: —
- pr: —

What: The wording rule (AGENTS.md: the product flags a change for review, lists patterns it is "consistent with", never "diagnoses") is only checked per component. Add one guard test that scans every non-test `web/src/**/*.ts(x)` file's string literals and JSX text for `diagnos` (case-insensitive) and fails with the file and line.
Interface: `web/src/wording.test.ts` using `import.meta.glob('./**/*.{ts,tsx}', { query: '?raw', import: 'default', eager: true })`, skipping `*.test.*` and `contracts.ts`. Strip `//` and `/* */` comments before matching (LiveSession.tsx and PatternList.tsx mention "never diagnoses" in comments, which is fine).
Acceptance:
- Test passes on current main; temporarily adding `'Diagnosed with X'` to any component makes it fail with that file named (say so in the PR body).
- `scripts/ci.sh` passes.
