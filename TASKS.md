# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: 13032a4

## Tasks

### T149 — API: GET /monitoring and PUT /rooms/{room}/monitoring
- status: claimed
- class: standard
- priority: 3
- kind: feature
- deps: T148
- area: pipeline/src/routine_watch/api.py, pipeline/tests/test_api_monitoring.py (new)
- source: proposed
- owner: ian-claude-standard-2
- claimed: 2026-10-17T10:46Z
- pr: —

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

### T194 — smoke.sh: seeded alert survives /demo/reset
- status: claimed
- class: light
- priority: 2
- kind: test
- deps: T178
- area: scripts/smoke.sh
- owner: max_API_light
- claimed: 2026-10-17T09:28Z
- pr: —

What: Reset must only drop live sessions and feedback, not the seeded demo history. After smoke.sh's POST /demo/reset, check GET /alerts still returns at least one alert.
Interface: read `scripts/smoke.sh` (the `/demo/reset` block at the end and the existing `/alerts` check).
Acceptance:
- New PASS/FAIL line "GET /alerts after reset" right after the reset check.
- `bash -n scripts/smoke.sh` and `scripts/ci.sh` pass; against `scripts/dev.sh up` all checks pass.

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

### T210 — Live screen: end-of-session summary against the resident's normal
- status: done
- class: standard
- priority: 2
- kind: feature
- source: proposed
- deps: —
- area: web/src/live/SessionSummary.tsx (new), web/src/live/SessionSummary.test.tsx (new), web/src/live/LiveSession.tsx, web/src/live/LiveSession.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T10:03Z
- pr: #204
- rating: 5/5 clear

What: Rationale: on demo day the live session just stops; a one-glance close ("Finished in 3m 40s, usually ~2m 50s · 2 errors, usually 0–1") makes the per-resident-baseline idea land for judges (Clarity). Shown when the `session_end` message arrives, above the existing flag/Open alert block.
Interface: `SessionSummary({durationS, errorCount, usualDurationS?, usualErrors?})`. Duration from the session_end payload if present, else first→last step event timestamps; the resident's normal from data the web already loads (`web/src/resident/api.ts`); omit the "usually" parts when unavailable. No pipeline or contract change.
Acceptance:
- Tests: renders with and without the baseline; plain wording, no "diagnos"; uses existing `web/src/ui` components/CSS classes, no inline styles.
- `cd web && npm test` and `scripts/ci.sh` pass.

### T211 — Test: alert "Copy summary" text keeps the safe wording
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/alert/alertText.test.ts
- owner: ian-claude-light-2
- claimed: 2026-10-17T10:00Z
- pr: #198
- rating: 4/5 clear, but acceptance criterion about display name required a small fix to alertText.ts beyond pure test-writing

What: T199 (#189) added `web/src/alert/alertText.ts`, the text a nurse pastes into the chart. Pin its wording rules with tests.
Interface: read only `web/src/alert/alertText.ts` and `web/src/alert/alertText.test.ts`; use the alert fixture the existing test uses.
Acceptance:
- New tests: the summary says "consistent with" for patterns, contains no "diagnos" and no "has <pattern>"; includes each error's time; names the resident by display name, not the raw id (e.g. not "mrs-k"); works with zero patterns.
- `cd web && npx vitest run src/alert/alertText.test.ts` passes.

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

### T213 — Alert view: heading order, focus on open, landmark
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/alert/AlertView.tsx, web/src/alert/AlertView.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T10:08Z
- pr: #202
- rating: 5/5 clear

What: The alert is the screen judges and nurses read most. Make it navigable by screen reader and keyboard: one `h1` (resident + "Flagged for review"), section `h2`s in reading order (What changed, Errors, Evidence, Patterns, Suggested checks, Feedback), the view wrapped in a labelled `main`/`section`, and focus moved to the `h1` when an alert opens.
Interface: markup-only changes in `AlertView.tsx`; keep existing class names and copy.
Acceptance:
- Tests: heading levels via `getAllByRole('heading')`, `h1` has focus after render, existing tests still pass unchanged in meaning.
- `cd web && npm test` and `scripts/ci.sh` pass.

### T214 — TaskMapLegend: CSS classes instead of inline styles
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/live/TaskMapLegend.tsx, web/src/live/taskMap.css, web/src/live/TaskMapLegend.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T10:08Z
- pr: #201
- rating: 5/5 clear

What: `TaskMapLegend.tsx` has three inline `style={{...}}` objects (list, item, swatch padding). Move them to classes in the existing `web/src/live/taskMap.css`, same pattern as T197/T200 (#193, #195). No visual change.
Interface: read only the area files plus `web/src/index.css` for the `--space-*` tokens. Class names `task-map-legend`, `task-map-legend__item`, `task-map-legend__swatch`.
Acceptance:
- `grep -c "style={{" web/src/live/TaskMapLegend.tsx` is 0
- existing TaskMapLegend tests still pass unchanged
- `cd web && npm test -- TaskMapLegend` and `scripts/ci.sh` pass

### T215 — DriftCard: CSS classes instead of inline styles
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/DriftCard.tsx, web/src/resident/driftCard.css, web/src/resident/DriftCard.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T10:13Z
- pr: #203
- rating: 5/5 clear

What: `DriftCard.tsx` sets text colour inline, including a `state === 'trending'` ternary. Move it to a new `web/src/resident/driftCard.css` keyed off the existing `data-state` attribute (`.drift-card[data-state="trending"] .drift-card__summary { color: var(--error-amber-text) }`). No visual change.
Interface: read only the area files and `web/src/resident/heatCalendar.css` as the example.
Acceptance:
- `grep -c "style={{" web/src/resident/DriftCard.tsx` is 0
- test asserts the trending summary has the `drift-card__summary` class and the card keeps `data-state="trending"`
- `cd web && npm test -- DriftCard` and `scripts/ci.sh` pass

### T216 — HeatCalendar grid and cells: CSS classes instead of inline styles
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/HeatCalendar.tsx, web/src/resident/heatCalendar.css, web/src/resident/HeatCalendar.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T10:17Z
- pr: #206
- rating: 5/5 clear

What: after T197 moved the legend to `heatCalendar.css`, the grid (line ~24) and day cells (~30, ~52) still use inline styles. Move static layout to classes (`heat-grid`, `heat-cell`). A per-cell colour that depends on the score may stay inline only as a single CSS custom property (e.g. `style={{ '--heat': ... }}`). No visual change.
Interface: read only the area files.
Acceptance:
- HeatCalendar.tsx has at most one inline style, and it only sets a CSS custom property
- existing HeatCalendar tests pass; one new test asserts cells have the `heat-cell` class
- `cd web && npm test -- HeatCalendar` and `scripts/ci.sh` pass

### T217 — Resident detail: heading order, landmark, focus on open
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/ResidentDetail.tsx, web/src/resident/ResidentDetail.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T10:17Z
- pr: #208
- rating: 5/5 clear

What: same accessibility pass as T213 does for the alert view, on the resident detail screen: one `h1` (the resident's display name), section headings as `h2` in visual order, the screen wrapped in `<main>` or a labelled region, and focus moved to the `h1` when the screen opens so a screen-reader user hears whose page it is.
Interface: ResidentDetail only; don't touch child components (BaselineChart, HeatCalendar, DriftCard, SessionList, ContextTimeline) beyond what ResidentDetail renders around them.
Acceptance:
- test: exactly one `heading` of level 1 with the resident's name; it has focus after render
- test: no heading level is skipped (h1 → h2)
- `cd web && npm test -- ResidentDetail` and `scripts/ci.sh` pass

### T218 — Test: DemoBanner disables Reset while resetting and clears the error on retry
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/ui/DemoBanner.tsx, web/src/ui/DemoBanner.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T10:18Z
- pr: #207
- rating: 5/5 clear

What: the Reset demo button (T189, T200) is the presenter's recovery path, so pin its behaviour: the button is disabled while the reset promise is pending, and a "Couldn't reset the demo" error from a failed attempt disappears after a later successful reset. If the second case fails today, fix it in DemoBanner.tsx.
Interface: `DemoBanner({ onReset })` with an injected fake `onReset`; read only the area files.
Acceptance:
- test: pending reset → button disabled; resolved → enabled
- test: reject then resolve → `role="alert"` error gone
- `cd web && npm test -- DemoBanner` and `scripts/ci.sh` pass

### T219 — Bug: live session's final error list differs from replay for sequence scenarios
- status: done
- class: standard
- priority: 1
- kind: bug
- deps: —
- area: pipeline/src/routine_watch/live.py, pipeline/tests/test_live_matches_replay.py, pipeline/tests/test_live.py
- owner: ian-claude
- claimed: 2026-10-17T10:20Z
- pr: #211
- rating: 4/5 the interface was clear, but it does not mention that test_live_camera.py pins the camera path's session_end to live's message for message, so live_camera.py needs the same field in the same PR

What: Played live, `tea_sequence_error`, `tea_self_corrected`, `meds_pill_before_water` and `meds_self_corrected` stream a transient `omission` for a dependency that happens later, so the errors the demo ends on are not the ones `expected.yaml` checks (xfailed in `test_live_matches_replay.py`, noted again in T202/#197). Keep streaming errors as now, but make `session_end` carry the healed final list so the screen can settle on the right answer.
Interface: the `session_end` message gains `errors` = the `final` `classify_errors(..., ended=True)` result `live.py` already computes, serialised like the `error` message's `error`. The `live.py` docstring says streamed errors are provisional and `session_end.errors` is authoritative. No change to `contracts.py`.
Acceptance:
* `test_live_matches_replay.py` compares `session_end["errors"]` against `expected.yaml` for every scenario; the `_SEQUENCE_HEALS_FROM_A_TRANSIENT_OMISSION` xfail set is removed and all scenarios pass.
* Existing live tests still pass; `scripts/ci.sh` passes.

### T220 — Live screen: settle on session_end's final error list
- status: in-review
- class: light
- priority: 1
- kind: bug
- deps: T219
- area: web/src/live/useLiveSession.ts, web/src/live/mockLiveStream.ts, web/src/live/useLiveSession.test.ts
- owner: ian-claude-light-2
- claimed: 2026-10-17T10:35Z
- pr: #213
- rating: 5/5 clear

What: After T219 the `session_end` WebSocket message carries `errors`, the session's final (healed) error list. The live screen should replace its streamed error list with it, so a step reported missed mid-session but done later no longer shows as missed once the session ends.
Interface: read `web/src/live/useLiveSession.ts` (message union and reducer, `case 'session_end'`), `web/src/live/mockLiveStream.ts`, and the `session_end` part of the module docstring in `pipeline/src/routine_watch/live.py`. Add optional `errors` to the `session_end` message type (same shape as the `error` message's `error`); on `session_end` with `errors`, set the state's errors to it; without `errors` (older server), keep the streamed list. Add `errors` to the mock's `session_end`.
Acceptance:
* test: a streamed omission followed by a `session_end` whose `errors` lack it leaves only the final errors
* test: a `session_end` without `errors` keeps the streamed list
* `cd web && npm test` and `scripts/ci.sh` pass

### T221 — Copy summary uses the resident's real name, not one guessed from the id
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/alert/alertText.ts, web/src/alert/alertText.test.ts, web/src/alert/AlertView.tsx
- owner: ian-claude
- claimed: 2026-10-17T10:35Z
- pr: #214
- note: released by ian-claude-standard-2: run ended without progress; partial work on branch task/T221-wip-1031: start from it (git switch task/T221-wip-1031 && git merge origin/main)
- rating: 4/5 clear on the interface, but it didn't mention AlertView's h1 also calls residentDisplayName, so deleting it changes the heading too

What: T211 (#198) added `residentDisplayName` in `alertText.ts`, which builds "Mrs. K" from the id `mrs-k`, while the rest of the app (`App.tsx` ~line 50) shows `resident.name` from the API, so the two can disagree for other residents. Pass the real name in instead.
Interface: read `web/src/alert/alertText.ts`, `web/src/alert/alertText.test.ts`, `web/src/alert/AlertView.tsx` (it already calls `fetchResident(alert.resident_id)`). Change to `alertText(alert: Alert, residentName?: string)` using `residentName ?? alert.resident_id`; delete `residentDisplayName` and `TITLES`. In `AlertView.tsx`, keep the fetched resident's `name` in state next to the care records and pass it to `alertText`.
Acceptance:
* test: with a name, the first line is `Resident: <name>`; without, it falls back to the id; existing wording tests still pass
* `cd web && npm test` and `scripts/ci.sh` pass

### T222 — Review: Copy summary says "Change flagged" for slow-trend alerts
- status: todo
- class: light
- priority: 1
- kind: bug
- deps: T221
- area: web/src/alert/alertText.ts, web/src/alert/alertText.test.ts
- owner: —
- claimed: —
- pr: —
- source: reviewer

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
- status: claimed
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/live/LiveScreen.tsx, web/src/live/liveScreen.css
- owner: ian-claude-light-2
- claimed: 2026-10-17T10:40Z
- pr: —

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
- status: todo
- class: light
- priority: 2
- kind: feature
- deps: —
- area: web/src/evidence/GhostReplay.tsx, web/src/evidence/GhostReplay.test.tsx
- owner: —
- claimed: —
- pr: —

What: Since T207 (PR #205) the demo's recordings get a made-up body (`pipeline/src/routine_watch/stick_figure.py`) so the ghost replay has something to draw. A judge or nurse should not mistake it for tracked motion, so add a small muted caption under the replay: "Demo recording: the body is drawn as a stand-in; the hand follows the tracked hand box."
Interface: read `web/src/evidence/GhostReplay.tsx` and its test only. Caption is plain text under the existing canvas/caption row, using existing muted text tokens (`var(--muted)`), readable on the dark card (see T208 for the contrast bug to avoid).
Acceptance:
- caption renders under the ghost replay; test asserts the text
- `cd web && npx vitest run src/evidence` and `scripts/ci.sh` pass

### T227 — Test: stand-in skeleton never changes what the recogniser reads
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_stick_figure.py
- owner: —
- claimed: —
- pr: —

What: `evidence._with_skeleton` adds poses/hands to box-only frames and promises "a frame read by the recogniser still says exactly what it did before". Pin that promise for every frame-level scenario.
Interface: read `pipeline/src/routine_watch/evidence.py` (`_with_skeleton`), `pipeline/src/routine_watch/stick_figure.py`, `pipeline/src/routine_watch/replay.py` (`load_scenario`, `SCENARIOS_DIR`). For each scenario dir under `tests/scenarios/` with a `frames.jsonl`, assert the recogniser's step/error output on the original frames equals the output on `_with_skeleton`-mapped frames (use whatever function `replay.py` already uses to turn frames into errors).
Acceptance:
- parametrized over all frame scenarios; fails if a stand-in landmark changes any error
- `cd pipeline && python -m pytest tests/test_stick_figure.py -q` and `scripts/ci.sh` pass

### T228 — Bug: flaky "moves focus to the h1" tests turn main CI red
- status: in-review
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
- status: todo
- class: standard
- priority: 1
- kind: bug
- source: reviewer
- deps: T220
- area: pipeline/src/routine_watch/demo.py, pipeline/src/routine_watch/api.py, web/src/live/LiveSession.tsx, web/src/resident/types.ts
- owner: —
- claimed: —
- pr: —

What: `useResidentBaseline` in `web/src/live/LiveSession.tsx` averages `duration_s` and error totals over *every* non-assisted session of mrs-k, including the recent bad days that triggered her flag. So the end-of-session "usually ~Xs / ~N errors" is inflated by exactly the change we're flagging, and disagrees with the pipeline's baseline, which is anchored to the earliest `BASELINE_DAYS` (demo.py, SPEC §8 beat 6). It also re-implements baseline logic in the web.
Interface: in `demo.py`, where the resident baseline is built from the early window, also compute `usual_duration_s` and `usual_errors` (mean over the same early, non-assisted sessions) and serve them inside `baseline` from `GET /residents/{id}`. Add both as optional fields to `Baseline` in `web/src/resident/types.ts`; have `LiveSession.tsx` read them instead of averaging `sessions`, and delete `average`/`sessionErrorTotal`.
Acceptance:
- pytest: mrs-k's `baseline.usual_errors` equals the mean over her first `BASELINE_DAYS` own sessions, and is lower than the whole-history mean
- `LiveSession.test.tsx` shows the "usually" values from the mocked `baseline`, not from `sessions`
- `scripts/ci.sh` passes
