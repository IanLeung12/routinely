# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: f563195

## Tasks

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
- note: released by ian-claude-light-2: run ended without progress; partial work on branch task/T225-wip-1147: start from it (git switch task/T225-wip-1147 && git merge origin/main)

What: `web/src/live/LiveSession.tsx` (line ~140) injects a `<style>` block; move it to a CSS file like `web/src/resident/driftCard.css` (T215). Waits for T220, which edits the same file.
Interface: new `web/src/live/liveSession.css` imported by `LiveSession.tsx`; same class names, same rules.
Acceptance:
- no `<style>` element left in `LiveSession.tsx`; no visual or text change
- `cd web && npx vitest run src/live` and `scripts/ci.sh` pass

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
- status: done
- class: standard
- priority: 1
- kind: bug
- source: reviewer
- deps: —
- area: pipeline/src/routine_watch/live.py, pipeline/tests/test_live.py
- owner: ian-claude
- claimed: 2026-10-17T11:24Z
- pr: #228
- rating: 5/5 clear - exact repro, the fix was the interface note verbatim; only unstated bit was that two sibling test files (test_live_matches_replay.py, test_live_camera.py) assert the old per-recording flag and had to be updated too

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
- status: done
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
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/alert/alert.css, web/src/alert/PatternList.css
- owner: ian-claude-standard-2
- claimed: 2026-10-17T11:32Z
- pr: #232
- rating: 4/5 clear, but the /alerts/<id> URL in the acceptance criteria doesn't exist (no router — alerts open via in-page state), so verifying required scripting a headless-Chrome click-through instead of a direct navigate

What: Nurses open alerts from a phone (push alert, SPEC §5 nice-to-have 3), but the alert screen has no responsive rules. Add a `@media (max-width: 480px)` block to `alert.css` and `PatternList.css` (same breakpoint as T235's `live/liveScreen.css`) so the header, error list, pattern cards, suggested checks and feedback buttons stack without horizontal scroll.
Interface: CSS only in the two files listed; no markup or class name changes. If the ghost replay figure (styled in `web/src/index.css`) still overflows, note it in the PR instead of editing index.css.
Acceptance:
- No horizontal scroll on `/alerts/<id>` at 375 px; feedback buttons wrap and stay ≥44 px tall tap targets.
- Desktop layout unchanged.
- `scripts/ci.sh` passes; PR body notes the viewport widths checked (e.g. Playwright screenshot at 375 and 1280).

### T239 — Resident detail: usable at phone width (375 px)
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/driftCard.css, web/src/resident/heatCalendar.css, web/src/resident/resident.css (new), web/src/resident/ResidentDetail.tsx
- owner: —
- claimed: —
- pr: #231
- rating: 5/5 clear
- note: merged as #231

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

### T242 — Web: monitoring API client (GET /monitoring, PUT /rooms/{room}/monitoring)
- status: done
- class: light
- priority: 1
- kind: feature
- deps: —
- area: web/src/about/monitoringApi.ts, web/src/about/monitoringApi.test.ts
- owner: ian-claude-light-2
- claimed: 2026-10-17T11:39Z
- pr: #230
- rating: 5/5 clear

What: T149 (#226) added the pipeline endpoints behind the room pause switch, but the web has no client for them. Add a small typed client; no UI changes.
Interface: read `pipeline/src/routine_watch/api.py` (search `monitoring`) and `web/src/config.ts` (`apiUrl`), copy the fetch style of `web/src/resident/api.ts`. Export `fetchPausedRooms(): Promise<string[]>` (GET `${apiUrl}/monitoring`, returns `paused_rooms`) and `setRoomMonitoring(room: string, on: boolean): Promise<void>` (PUT `${apiUrl}/rooms/${encodeURIComponent(room)}/monitoring` with the JSON body the endpoint expects). Both throw on network error or non-ok response.
Acceptance:
- tests with a stubbed `fetch` cover: URL + method + body, parsed result, throws on `ok: false`, throws on network error
- `cd web && npm test` and `scripts/ci.sh` pass

### T243 — Resident detail: monitoring switch reads and writes the real pause state
- status: claimed
- class: standard
- priority: 1
- kind: feature
- deps: T242
- area: web/src/resident/ResidentDetail.tsx, web/src/resident/ResidentDetail.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T11:57Z
- pr: —

What: `ResidentDetail` keeps the monitoring switch in local `useState(true)`, so pausing a room does nothing on the server (SPEC §12). Load the initial state from `fetchPausedRooms()` and call `setRoomMonitoring()` on toggle (T242).
Interface: consume `web/src/about/monitoringApi.ts`; `MonitoringToggle` props unchanged. Optimistic toggle; if the PUT fails, revert the switch and show a short inline message ("Couldn't change monitoring. Try again."). If the GET fails (API down / mock mode), keep today's local-only behaviour, no error shown.
Acceptance:
- tests: initial state reflects a paused room; toggle sends PUT; failed PUT reverts + shows message; GET failure falls back to "on"
- `cd web && npm test` and `scripts/ci.sh` pass

### T244 — Live screen: show "Monitoring paused" when /ws/live sends {"type":"paused"}
- status: done
- class: standard
- priority: 1
- kind: bug
- deps: —
- area: web/src/live/useLiveSession.ts, web/src/live/useLiveSession.test.ts, web/src/live/LiveScreen.tsx, web/src/live/LiveScreen.test.tsx
- owner: ian-claude
- claimed: 2026-10-17T11:39Z
- pr: #233
- rating: 4/5 clear on the interface and acceptance, but the area named LiveScreen.tsx/LiveScreen.test.tsx while the hook is consumed by LiveSession.tsx, which owns the skeleton/task map the acceptance asks about

What: since T149 (#226), `/ws/live` sends one `{"type": "paused", "room": "<room>"}` and closes if the demo resident's room is paused. `useLiveSession` counts that as data received, ignores the unknown type, and the live screen sits empty with no explanation. Handle it explicitly.
Interface: add a `paused` message to the hook's `LiveMessage` union (web-side type only; don't touch `contracts/`) and a `paused: { room: string } | null` field to its state; do not fall back to mock data when paused. `LiveScreen` renders the `EmptyState` from `web/src/ui/` with "Monitoring is paused for room <room>" and a hint that it can be turned back on from the resident's page.
Acceptance:
- hook test: a fake socket sending `paused` then closing yields `paused.room`, no mock fallback
- LiveScreen test: paused state shows the message, no skeleton/task map
- `cd web && npm test` and `scripts/ci.sh` pass

### T245 — Smoke: check GET /monitoring and a PUT round-trip
- status: todo
- class: light
- priority: 2
- kind: test
- deps: T192
- area: scripts/smoke.sh
- owner: —
- claimed: —
- pr: —

What: `scripts/smoke.sh` doesn't exercise the monitoring endpoints added in T149 (#226). Add checks so the tester catches a broken pause switch.
Interface: read `scripts/smoke.sh` (copy the `curl "${CURL_OPTS[@]}"` + `pass`/`fail` pattern) and `pipeline/src/routine_watch/api.py` (search `monitoring`). Before the final `/demo/reset` block: GET `/monitoring` returns JSON with `paused_rooms`; PUT pause on the demo resident's room, GET shows it paused, PUT resume, GET shows it gone; PUT on an unknown room returns 404. Always resume the room even if a check fails.
Acceptance:
- `scripts/dev.sh up && scripts/smoke.sh` passes with the new checks; `scripts/dev.sh down`
- `bash -n scripts/smoke.sh` and `scripts/ci.sh` pass

### T246 — Unit overview: "Monitoring paused" chip on residents whose room is paused
- status: todo
- class: light
- priority: 2
- kind: feature
- deps: T242
- area: web/src/overview/UnitOverview.tsx, web/src/overview/UnitOverview.test.tsx, web/src/overview/overview.css
- owner: —
- claimed: —
- pr: —

What: A nurse scanning the unit can't tell which rooms are paused (SPEC §12 privacy pause). On load, call `fetchPausedRooms()` and show a small grey "Monitoring paused" chip on each resident card whose `resident.room` is in the list.
Interface: read `web/src/about/monitoringApi.ts` (`fetchPausedRooms(): Promise<string[]>`) and `web/src/overview/UnitOverview.tsx` (card markup around the `resident-room` span). If the fetch fails (API down / mock mode), show no chips and no error. Add the chip text to the card's `aria-label`.
Acceptance:
- tests (mock `fetchPausedRooms`): paused room shows the chip; others don't; fetch rejection shows no chip and the overview still renders
- `cd web && npm test` and `scripts/ci.sh` pass

### T247 — Shift handoff: usable at phone width (375 px)
- status: todo
- class: light
- priority: 2
- kind: improvement
- deps: T203
- area: web/src/handoff/handoff.css, web/src/handoff/Handoff.tsx, web/src/handoff/Handoff.test.tsx
- owner: —
- claimed: —
- pr: —

What: Same treatment T234/T235 gave the overview and live screen: at 375 px the handoff page has no horizontal scroll, rows stack, and buttons are at least 44 px tall.
Interface: read `web/src/handoff/Handoff.tsx`, `web/src/handoff/handoff.css`, and `web/src/overview/overview.css` (copy its `@media (max-width: 480px)` approach). CSS plus at most class-name changes in `Handoff.tsx`; no behaviour change.
Acceptance:
- a `@media (max-width: 480px)` block in `handoff.css`; no fixed widths over 375 px
- existing Handoff tests still pass; `cd web && npm test` and `scripts/ci.sh` pass

### T248 — Test: live session_end flag matches /residents for every scenario
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_live_flag_consistency.py
- owner: —
- claimed: —
- pr: —

What: Guard T236 across all recordings: after a live replay of each scenario in `tests/scenarios/`, `session_end.flag` must equal that resident's flagged state from `/residents`, and `alert_id` must be `None` or an id that `/alerts/{id}` returns 200 for.
Interface: read `pipeline/tests/test_live.py` (how it drives `session_messages` / `/ws/live` with the FastAPI `TestClient`) and `pipeline/tests/test_api_demo_reset.py` (calling `/demo/reset` between cases). New file only; parametrize over scenario dirs; reset state between cases.
Acceptance:
- one parametrized test per scenario; fakes only, no real API calls
- `cd pipeline && python -m pytest tests/test_live_flag_consistency.py` and `scripts/ci.sh` pass

### T249 — Review: pausing a room mid-session doesn't stop the live session
- status: in-review
- class: standard
- priority: 1
- kind: bug
- source: reviewer
- deps: —
- area: pipeline/src/routine_watch/api.py, pipeline/tests/test_api_monitoring.py
- owner: ian-claude-standard-2
- claimed: 2026-10-17T11:52Z
- pr: #234
- rating: 5/5 clear

What: `/ws/live` checks `get_monitoring_store().is_on(room)` only once before the session starts. If a nurse pauses the room while a session is streaming, frames keep going out and the finished session is still recorded into the resident's history (and can flag them), although the UI says "No camera data is processed while paused" (SPEC §12).
Interface: in the `async for message in session_messages(...)` loop in `api.py`, re-check the resident's room each message; if paused, send `{"type": "paused", "room": room}`, close normally and stop iterating (closing the generator early means `session_messages` never records the session, same as a dashboard disconnect). Factor the check into one helper used at start and in the loop.
Acceptance:
- test: start `/ws/live`, `PUT /rooms/{room}/monitoring {"on": false}` after the first message, assert a `paused` message arrives, no `session_end`, and `/residents/{id}` session count is unchanged
- `scripts/ci.sh` passes

### T250 — Review: /ws/live message protocol has no contract
- status: claimed
- class: heavy
- priority: 2
- kind: improvement
- source: reviewer
- deps: T244
- area: contracts/live_message.schema.json, contracts/README.md, pipeline/tests/test_live_contract.py
- owner: ian-claude
- claimed: 2026-10-17T11:53Z
- pr: —

What: The live socket's messages (`session_start`, `frame`, `step`, `step_state`, `error`, `session_end`, and now `paused`) cross the pipeline/web boundary but are defined only in `live.py`'s docstring and hand-mirrored in `web/src/live/useLiveSession.ts`; `paused` was just added on one side only. Add a JSON Schema (`oneOf` on `type`) to `contracts/`.
Interface: read `pipeline/src/routine_watch/live.py` (module docstring + `as_json`), `api.py` `live_session`, and `web/src/live/useLiveSession.ts`. Schema only plus a test; don't change message shapes.
Acceptance:
- pytest replays one scenario through `/ws/live` (fakes only) and validates every message, plus a `paused` message, against the schema
- `contracts/README.md` lists it; `scripts/ci.sh` passes

### T251 — Shift handoff payload lists rooms whose monitoring is paused
- status: todo
- class: standard
- priority: 2
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/handoff.py, pipeline/tests/test_handoff.py
- owner: —
- claimed: —
- pr: —

What: A nurse taking over a shift must know which rooms aren't being watched; a paused room silently produces no flags, so today the handoff can read "all quiet" for a resident nobody was monitoring (SPEC §12).
Interface: `build_handoff(...)` adds `"paused": [{"room": str, "resident_id": str, "name": str}]` to its result, read from `get_monitoring_store().paused_rooms()` (`monitoring.py`) and the room→resident config the API already uses for `/ws/live`; empty list when nothing is paused. Each resident row whose room is paused gets `"monitoring_paused": true` (else false). Don't change `api.py` (the endpoint returns `build_handoff` as-is) or anything in `web/`.
Acceptance:
- Tests in `pipeline/tests/test_handoff.py`: nothing paused → `paused == []`, all rows false; pause one room → that resident listed once, its row true; resume → back to empty. Reset the monitoring store between tests.
- Summary/flag counts unchanged by pausing.
- `scripts/ci.sh` passes.

### T252 — Web: lazy-load the secondary screens to shrink the first-load bundle
- status: todo
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/App.tsx, web/src/App.test.tsx
- owner: —
- claimed: —
- pr: —

What: The demo opens on the unit overview, but `App.tsx` statically imports every screen (pattern library, shift handoff, tour, live screen, alert view). Load the screens not shown on first paint with `React.lazy` + `Suspense` so the overview appears faster on a phone.
Interface: In `App.tsx` only, `lazy(() => import(...))` for `PatternLibrary`, `Handoff` and `Tour` (named exports: map to `{ default: m.X }`); wrap each in `<Suspense fallback={...}>` using an existing `web/src/ui/` loading/empty component. Keep the overview, resident detail, live and alert screens static (demo path). No behaviour or copy changes.
Acceptance:
- Existing `App.test.tsx` tests pass (use `findBy*` where a lazy screen now resolves async); add one test that opening "Shift handoff" still renders it.
- PR body gives the main JS chunk size from `cd web && npm run build` before and after.
- `scripts/ci.sh` passes.

### T253 — Shift handoff screen: show the rooms whose monitoring is paused
- status: todo
- class: light
- priority: 2
- kind: feature
- deps: T251
- area: web/src/handoff/types.ts, web/src/handoff/mockHandoff.ts, web/src/handoff/Handoff.tsx, web/src/handoff/Handoff.test.tsx
- owner: —
- claimed: —
- pr: —

What: Show T251's new `paused` list on the handoff screen so the incoming nurse sees which rooms weren't watched.
Interface: Read `web/src/handoff/types.ts`, `Handoff.tsx`, `mockHandoff.ts` and T251's docstring in `pipeline/src/routine_watch/handoff.py`. Add `paused: { room: string; resident_id: string; name: string }[]` to the `Handoff` type (treat missing as `[]` for older APIs) and `monitoring_paused?: boolean` to `HandoffResident`. When non-empty, render one line above the rows: "Monitoring paused: <name> (room <room>), ..." and a "Monitoring paused" chip on those residents' rows. Include the line in `handoffText`. Mock gets `paused: []`.
Acceptance:
- Tests: no line when `paused` is empty or missing; line + chip when one room is paused; `handoffText` includes it.
- `scripts/ci.sh` passes.
