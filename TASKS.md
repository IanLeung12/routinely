# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: 8f29909

## Tasks

### T118 — Pattern library page: what each pattern looks for and its source
- status: todo
- class: standard
- priority: 3
- kind: feature
- deps: T084
- area: pipeline/src/routine_watch/api.py (add the route only), pipeline/tests/test_api_patterns.py (new), web/src/patterns/ (new), web/src/App.tsx (one nav entry)
- owner: —
- claimed: —
- pr: —
- source: proposed

What: Rationale: judges (Clarity, responsible design §12) can see every pattern's signals, rule-out checks and source citation, showing it is a cited rules library, not an LLM guess. Read-only screen, separate from the demo path.
Interface: `GET /patterns` → the library as JSON (id, name, signals, time profile, checks, urgency, source); `web/src/patterns/PatternLibrary.tsx` lists them with "consistent with" wording.
Acceptance:
- pytest: route returns every library entry with a non-empty source; vitest: renders each pattern, urgent one visually distinct, no "diagnos" text.
- `scripts/ci.sh` passes.

### T149 — API: GET /monitoring and PUT /rooms/{room}/monitoring
- status: todo
- class: standard
- priority: 3
- kind: feature
- deps: T148
- area: pipeline/src/routine_watch/api.py, pipeline/tests/test_api_monitoring.py (new)
- source: proposed
- owner: —
- claimed: —
- pr: —

What: Expose the T148 store so the dashboard's pause switch is real. While a room is paused, `/ws/live` for a scenario whose resident is in that room sends one `{"type": "paused", "room": ...}` message and closes instead of streaming frames (no camera data processed).
Interface: `GET /monitoring` → `{"paused_rooms": [...]}`; `PUT /rooms/{room}/monitoring` body `{"on": bool}` → `{"room": str, "on": bool}`; uses `monitoring.get_monitoring_store()`. Room→resident comes from `demo.demo_residents()`; unknown room → 404.
Acceptance:
- tests: default empty, pause/resume round trip, 404 for unknown room, paused live session gets the `paused` message and no frames (TestClient websocket); store reset between tests.
- `scripts/ci.sh` passes.

### T155 — Bug: alert opened after the live session shows other errors than the live session made
- status: done
- class: heavy
- priority: 0
- kind: bug
- deps: —
- area: pipeline/src/routine_watch/demo.py, pipeline/src/routine_watch/alerts.py, pipeline/src/routine_watch/session_log.py, pipeline/tests/
- source: tester
- owner: ian-claude
- claimed: 2026-10-17T09:36Z
- pr: #192
- rating: 4/5 clear repro and interface; the step id is teabag_in_cup not add_teabag, and the fix needs evidence.known_session (outside the listed area) or 'Open evidence' 404s on the live session's errors

What: On stage the live session (default demo scenario) flags "skipped Put the teabag in the cup · 1:10" and "repeated Pour the water · 1:30". Clicking "Open alert" then shows `alert-mrs-k` with errors "skipped fill kettle 0:51, repeated boil 1:42, skipped fill kettle 0:33, repeated boil 1:06" (sessions mrs-k-22, mrs-k-23): the recorded live session's score is merged into Mrs. K's history, but its actual errors are not; the alert's errors for that session are synthetic. The summary also says "4 errors this session" for errors spread over two sessions.
Interface: the session recorded by `routine_watch.live` (via `session_log`) must carry its real `ErrorEvent`s into the resident's newest session, so `build_alerts` lists them (with their real step ids and times) for that session; the summary should count errors per session or say "across 2 sessions".
Repro: `OFFLINE_MODE=true scripts/dev.sh up`, open http://localhost:5173, wait ~90 s for the live session to finish, click "Open alert"; compare the alert's Errors list with the live session's Errors list. Or `curl localhost:8000/alerts/alert-mrs-k` after the live session.
Acceptance:
- test: after playing the demo live scenario through the pipeline, `/alerts/alert-mrs-k` contains its omission of `add_teabag` and perseveration of `pour` with the live session's session_id.
- summary wording no longer says "this session" for multi-session errors; `scripts/ci.sh` and `scripts/e2e.sh` pass.

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

### T183 — Review: overview/handoff top pattern ignores nurse-feedback weights
- status: done
- class: light
- priority: 1
- kind: bug
- source: reviewer
- deps: T182
- area: pipeline/src/routine_watch/api.py, pipeline/src/routine_watch/handoff.py, pipeline/tests/test_api_residents.py
- owner: ian-claude
- claimed: 2026-10-17T09:23Z
- pr: #185
- rating: 5/5 clear - the fix, the helper and the acceptance test were all named exactly; only unstated bit was that alerts.py is outside the listed area

What: `/residents` shows `top_pattern` from `demo.py` (`score_patterns` with no weights), while the alert's `patterns[0]` is re-weighted by `FeedbackStore.pattern_weights` (T130). After a nurse answers "what was it?", the overview chip and the alert can name different patterns for the same resident. `handoff.build_handoff` also calls `build_alerts(residents)` without `feedback=`. Fix: in `api._tuned`, when the resident has pattern weights, recompute `top_pattern` with `score_patterns(features, weights=..., answers=...)` (reuse `alerts._patterns` or expose a small helper) and pass the store into `build_alerts` in handoff.
Acceptance:
* Test: confirm an alert with a cause that reorders the ranking; `/residents` top_pattern id equals `/alerts/{id}` `patterns[0].pattern_id`.
* `scripts/ci.sh` passes.

### T184 — Test: status_for with the raw threshold gives each resident's own status
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_status_for.py (new)
- owner: max_API_light
- claimed: 2026-10-17T09:13Z
- pr: #172
- rating: 5/5 clear

What: T167 (PR #163) added `demo.status_for(resident, threshold)`, which repeats the flag rule from `demo_residents()`. Pin that the two agree, so `/residents` can't drift from the demo's own status when no feedback has been given.
Interface: Read only `pipeline/src/routine_watch/demo.py` (`status_for`, `demo_residents`), `pipeline/tests/conftest.py` (autouse `session_log.reset`) and `pipeline/tests/test_live_flag.py` (how a live session is recorded). New file only.
Acceptance:
* For every resident in `demo_residents()`, `status_for(r, r["baseline"]["threshold"]) == r["status"]`.
* Same check after recording Mrs. K's live tea session the way `test_live_flag.py` does (she becomes flagged).
* `status_for(r, 1e9)` is never "flagged".
* `scripts/ci.sh` passes.

### T185 — demo.py: one flag rule shared by demo_residents and status_for
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: T184
- area: pipeline/src/routine_watch/demo.py, pipeline/tests/test_demo.py
- owner: ian-claude-standard-2
- claimed: 2026-10-17T09:21Z
- pr: #180
- rating: 5/5 clear

What: `demo_residents()` and `status_for()` each build `timestamped`, call `flag_change` and `_watch`, then `_status` (the second copy calls `_watch(sessions, sessions, ...)` instead of `(history, sessions, ...)`, which only works because live sessions fall after the baseline cutoff). Pull this into one private helper both call, with no behaviour change.
Interface: one private helper (e.g. `_status_from(history, sessions, scores, baseline: Baseline) -> str`); `status_for` signature unchanged; `api.py` untouched.
Acceptance:
* `flag_change(` and `_watch(` are each called once in `demo.py`.
* T184's test and `pipeline/tests/test_demo*.py` pass unchanged.
* `scripts/ci.sh` passes.

### T186 — Live screen: ?task=meds opens on the medication routine
- status: done
- class: light
- priority: 2
- kind: feature
- deps: —
- area: web/src/live/LiveScreen.tsx, web/src/live/LiveScreen.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T09:15Z
- pr: #173
- rating: 5/5 clear

What: The presenter wants to link straight to the second routine. `LiveScreen` (T161) always starts on tea; let `?task=meds` pick "Medication with water" first; `?task=tea`, anything else or no param keeps tea. Clicking a button still switches as now.
Interface: Read only `web/src/live/LiveScreen.tsx` and its test. Read `window.location.search` once in the `useState` initializer (`URLSearchParams`); no router, don't write to the URL.
Acceptance:
* Tests: no param → "Making tea" `aria-pressed=true`; `?task=meds` → "Medication with water" pressed and `LiveSession` gets `meds_skip_water`; `?task=bogus` → tea.
* `scripts/ci.sh` passes.

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

### T188 — Docs: DEMO.md covers /demo/reset and ?task=meds
- status: done
- class: light
- priority: 2
- kind: docs
- deps: —
- area: docs/DEMO.md
- owner: ian-claude-light-2
- claimed: 2026-10-17T09:22Z
- pr: #179
- rating: 5/5 clear

What: The demo runbook doesn't say how to put the demo back between rehearsals or how to open the medication routine directly. Add both.
Interface: read `docs/DEMO.md`, `pipeline/src/routine_watch/api.py` (`demo_reset`, `_demo_reset_enabled`), `web/src/live/LiveScreen.tsx` (the `?task=meds` query), `.env.example` (`DEMO_RESET`).
Acceptance:
- DEMO.md has a "Between rehearsals" step: `curl -X POST http://localhost:8000/demo/reset`, only works with `OFFLINE_MODE=true` or `DEMO_RESET=1`, returns `{"ok": true}`.
- DEMO.md mentions opening the live screen with `?task=meds` for the medication routine (tea stays the default).
- Only docs/DEMO.md changes; `scripts/ci.sh` passes.

### T189 — Demo banner: "Reset demo" button
- status: done
- class: standard
- priority: 2
- kind: feature
- deps: —
- area: web/src/ui/DemoBanner.tsx, web/src/ui/DemoBanner.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T09:23Z
- pr: #182
- rating: 5/5 clear

What: Presenters need a one-click way to undo a rehearsal's flag and feedback. Add a "Reset demo" button to the demo banner that POSTs `/demo/reset` and then reloads the page.
Interface: `DemoBanner({ onDismiss?, onReset? })`; default `onReset` does `fetch(\`${apiBase}/demo/reset\`, {method:'POST'})` using the API base from `web/src/config.ts`, then `window.location.reload()`. On a non-2xx/network error show inline "Couldn't reset the demo" text, no throw.
Acceptance:
- Button is a secondary `btn`, labelled "Reset demo"; disabled while the request is in flight.
- Tests (mock fetch): success calls reload; 404 shows the error text and doesn't reload.
- `cd web && npm test -- DemoBanner` and `scripts/ci.sh` pass.

### T190 — Test: LiveScreen ignores unknown ?task values
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/live/LiveScreen.test.tsx
- owner: max_API_light
- claimed: 2026-10-17T09:23Z
- pr: #181
- rating: 5/5 clear

What: T186 added `?task=meds`; pin that anything else (absent, `?task=tea`, `?task=foo`) still opens the tea routine.
Interface: read `web/src/live/LiveScreen.tsx` and its existing test; set `window.history.replaceState(null, '', '/?task=foo')` per case and restore afterwards.
Acceptance:
- Three cases (no query, `tea`, `foo`) all show tea selected in the picker.
- Only the test file changes; `cd web && npm test -- LiveScreen` and `scripts/ci.sh` pass.

### T191 — Test: FeedbackStore.reset() puts threshold and weights back to base
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_feedback.py
- owner: ian-claude-light-2
- claimed: 2026-10-17T09:26Z
- pr: #183
- rating: 5/5 clear

What: `FeedbackStore.reset()` (added by T144) has no unit test.
Interface: read `pipeline/src/routine_watch/feedback.py` and `pipeline/tests/test_feedback.py`.
Acceptance:
- Test: log a false alarm and a cause, call `reset()`, assert threshold equals the no-feedback base, the feedback for that alert id is None, and `cause_of` is None.
- `cd pipeline && pytest tests/test_feedback.py` and `scripts/ci.sh` pass.

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

### T193 — Scenario: medication taken twice is a repetition error
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/meds_pill_twice/ (new), tests/scenarios/README.md
- owner: ian-claude-standard-2
- claimed: 2026-10-17T09:27Z
- pr: #184
- rating: 5/5 clear

What: The medication routine has skip and order scenarios but none for a repeated step, the most safety-relevant meds error. Add one.
Interface: copy the shape of `tests/scenarios/meds_normal/` and `tests/scenarios/tea_kettle_twice/`; `frames.jsonl` + `expected.yaml` with one repetition error on the take-pill step.
Acceptance:
- `scripts/e2e.sh` passes including the new scenario; README lists it (the README coverage test passes).
- If the meds graph can't express it, stop and set the task blocked with the reason (don't change pipeline code).

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

### T195 — Unit overview: All / Flagged / Watch filter
- status: done
- class: standard
- priority: 3
- kind: feature
- source: proposed
- deps: —
- area: web/src/overview/UnitOverview.tsx, web/src/overview/UnitOverview.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T09:35Z
- pr: #187
- rating: 5/5 clear

What: Rationale: on a real unit a nurse wants only the residents needing attention in one tap (Clarity). Add a three-way filter above the resident list; All stays default so the demo path is unchanged.
Interface: local state in `UnitOverview`; buttons with `aria-pressed`; filters on the existing resident `status`; empty filter result uses `EmptyState` "No residents flagged for review." / "No residents to watch.".
Acceptance:
- Tests: each filter shows only matching residents; empty case shows the message; default is All.
- `cd web && npm test -- UnitOverview` and `scripts/ci.sh` pass.

### T196 — App: Alerts list names residents; alert Back returns to where it was opened
- status: done
- class: standard
- priority: 1
- kind: bug
- deps: —
- area: web/src/App.tsx, web/src/App.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T09:43Z
- pr: #190
- rating: 5/5 clear

What: The overview's Alerts list shows the raw id ("mrs-k: Change flagged for review"), not a name a nurse reads; and an alert opened from the shift handoff (T152, PR #177) goes Back to the overview instead of the handoff.
Interface: In `App.tsx`, label each alert with the resident's display name from `fetchResidents()` (`web/src/overview/api.ts`; fall back to the id if not found). Track where the alert was opened from (`'overview' | 'handoff' | 'live'`) so `AlertView`'s `onBack` returns there.
Acceptance:
* App test: Alerts list shows "Mrs. K" (mock residents), not "mrs-k".
* App test: Shift handoff → Open alert → Back lands on the handoff screen; overview → alert → Back lands on the overview.
* `cd web && npx vitest run src/App.test.tsx` and `scripts/ci.sh` pass.

### T197 — Heat calendar legend: CSS classes instead of inline styles
- status: in-review
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/HeatCalendar.tsx, web/src/resident/heatCalendar.css, web/src/resident/HeatCalendar.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T09:51Z
- pr: #193
- note: released by ian-claude-light-2: run ended without progress; partial work on branch task/T197-wip-0932: start from it (git switch task/T197-wip-0932 && git merge origin/main)
- rating: 5/5 clear

What: T172 (PR #176) added three legend swatches with long inline `style={{...}}` objects. Move them to classes so the colours live in one place with the grid cells.
Interface: Read only `web/src/resident/HeatCalendar.tsx` and `web/src/alert/alert.css` (example of a component stylesheet). Create `heatCalendar.css` with `.heat-swatch`, `.heat-swatch--low`, `.heat-swatch--high`, `.heat-swatch--none` using the same CSS variables; import it in `HeatCalendar.tsx`. No visible change.
Acceptance:
* No `style={{` left on the legend swatches; legend text unchanged ("Lighter = fewer errors", "Darker = more errors", "Grey = no session").
* `cd web && npx vitest run src/resident/HeatCalendar.test.tsx` passes.

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

### T199 — Alert view: "Copy summary" for the chart note
- status: done
- class: standard
- priority: 3
- kind: feature
- source: proposed
- deps: —
- area: web/src/alert/AlertView.tsx, web/src/alert/alertText.ts, web/src/alert/alertText.test.ts, web/src/alert/AlertView.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T09:44Z
- pr: #189
- rating: 5/5 clear

What: Rationale: nurses chart what they saw; one tap copies the alert as plain text (like the handoff's Copy summary, T151) so the flag reaches the care record without retyping (Usefulness).
Interface: `alertText(alert: Alert): string` in `alertText.ts`: resident, "Change flagged for review", the summary, errors with times, "Consistent with: …" pattern names, suggested checks. A `Copy summary` button in `AlertView` using `navigator.clipboard.writeText`, with a "Copied" status like `web/src/handoff/Handoff.tsx`.
Acceptance:
* Unit test on `alertText` for the mock alert: contains "flagged for review" and "Consistent with", never "diagnos".
* AlertView test: clicking Copy summary calls clipboard with `alertText(alert)` and shows "Copied".
* `scripts/ci.sh` passes.

### T200 — Demo banner: CSS classes and an announced reset error
- status: claimed
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/ui/DemoBanner.tsx, web/src/ui/DemoBanner.test.tsx, web/src/ui/demoBanner.css
- owner: ian-claude-standard-2
- claimed: 2026-10-17T09:51Z
- pr: —

What: DemoBanner (PR #182) uses inline styles and its "Couldn't reset the demo" text is not announced to screen readers. Move styles to `demoBanner.css` and give the error `role="alert"`.
Interface: read only web/src/ui/DemoBanner.tsx, web/src/ui/DemoBanner.test.tsx and web/src/styles/ (design tokens). No behaviour change.
Acceptance:
- no `style={{` left in DemoBanner.tsx; classes use existing `var(--...)` tokens
- test: a failing onReset renders an element with role="alert" containing "Couldn't reset the demo"
- `cd web && npm test -- DemoBanner` passes; `scripts/ci.sh` passes

### T201 — Scenario: medication routine abandoned halfway
- status: claimed
- class: light
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/meds_abandoned/
- owner: ian-claude-light-2
- claimed: 2026-10-17T09:53Z
- pr: —

What: add a meds scenario where the resident stops after the first steps, mirroring tea_abandoned, so the second task's abandonment path is covered end to end.
Interface: read tests/scenarios/README.md, tests/scenarios/tea_abandoned/, tests/scenarios/meds_normal/ and tasks/meds.yaml (or the meds task graph named in meds_normal/expected.yaml). Write steps.jsonl + expected.yaml only.
Acceptance:
- expected.yaml has `task:` set to the meds graph and the errors/flag the replay actually produces (run the replay and pin its output; comment on why)
- `scripts/e2e.sh tests/scenarios/meds_abandoned` prints PASS; `scripts/ci.sh` passes

### T202 — Scenario: medication slip corrected inside the window is not flagged
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/meds_self_corrected/
- owner: —
- claimed: —
- pr: —

What: meds counterpart of tea_self_corrected: a sequence slip the resident corrects within the self-correction window, so the reduced weight is pinned for the second task too.
Interface: read tests/scenarios/README.md, tests/scenarios/tea_self_corrected/ and tests/scenarios/meds_pill_before_water/. Write steps.jsonl + expected.yaml only.
Acceptance:
- expected.yaml pins `score:` and `flag: false`, with a comment saying what full weighting would score
- `scripts/e2e.sh tests/scenarios/meds_self_corrected` prints PASS; `scripts/ci.sh` passes

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

### T204 — Review: demo tour misstates the flag rule ("two sessions in a row")
- status: todo
- class: light
- priority: 2
- kind: bug
- source: reviewer
- deps: —
- area: web/src/tour/steps.ts, web/src/tour/Tour.test.tsx
- owner: —
- claimed: —
- pr: —

What: the "Alert" step (T164, #186) says an alert appears "when two sessions in a row cross a resident's own threshold". The real rule (`pipeline/src/routine_watch/change_detection.py` `flag_change`) is at least `FLAG_MIN_SESSIONS` (2) sessions above threshold within a 48-hour window, consecutive or not. A presenter reading this card would misdescribe the product to judges. Reword to "when at least two sessions within 48 hours cross a resident's own threshold".
Interface: read only the area files.
Acceptance:
- Alert step copy names "within 48 hours", no "in a row"
- Tour test asserts the Alert step body contains "48 hours"
- `cd web && npm test -- Tour` and `scripts/ci.sh` pass

### T205 — Tour: Escape closes it, arrow keys step through
- status: todo
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/tour/Tour.tsx, web/src/tour/Tour.test.tsx
- owner: —
- claimed: —
- pr: —

What: The presenter drives the `?tour=1` cue card from a keyboard on stage; today only mouse clicks work. Add Escape = Close, ArrowRight = Next, ArrowLeft = Back (respecting first/last bounds).
Interface: `Tour` in web/src/tour/Tour.tsx adds one `keydown` listener on `window` in a `useEffect` (removed on unmount/close). No other files; do not edit steps.ts (T204 owns it).
Acceptance:
- Escape hides the card and calls `onClose`; ArrowRight/ArrowLeft move one step and never go past step 1 or the last step.
- New tests in Tour.test.tsx using `fireEvent.keyDown(window, { key: ... })`.
- `cd web && npm test -- --run src/tour` and `scripts/ci.sh` pass.

### T206 — Test: alerts.top_pattern_for edge cases
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_top_pattern_for.py
- owner: —
- claimed: —
- pr: —

What: `top_pattern_for` (pipeline/src/routine_watch/alerts.py, added in T183) has only API-level coverage. Add unit tests for it directly.
Interface: read pipeline/src/routine_watch/alerts.py (`top_pattern_for`, `_patterns`), pipeline/src/routine_watch/demo.py (`demo_residents`), and pipeline/tests/test_api_residents.py for fixture style. New file only.
Acceptance:
- With `feedback=None`, for every resident from `demo_residents()` whose `top_pattern` is set, `top_pattern_for(resident)["pattern_id"] == resident["top_pattern"]["pattern_id"]`.
- Returned dict has exactly the keys `pattern_id`, `name`, `urgency`, and `urgency` is a plain string.
- A resident whose patterns all fall below threshold (build one by copying a demo resident and clearing its errors/sessions as needed) returns `None`.
- `cd pipeline && python -m pytest tests/test_top_pattern_for.py -q` and `scripts/ci.sh` pass.

### T207 — Bug: skeleton view and evidence ghost replay show no skeleton, only object boxes
- status: todo
- class: standard
- priority: 1
- kind: bug
- deps: —
- area: pipeline/src/routine_watch/live.py, pipeline/src/routine_watch/evidence.py, pipeline/tests/
- owner: —
- claimed: —
- pr: —

What: Tester (main 355d6b1). Every stand-in frame the demo serves is built with `poses=[]` and `hands=[]` (`live._synthetic_frames`, and the recordings behind `/sessions/{id}/replay` and `/residents/{id}/normal_replay`), so the live "Skeleton view" and the alert's "Today / Usual" ghost replay draw only labelled object boxes, never a body skeleton or hands (SPEC §5 ghost replay, §10 step 3 "skeleton view").
Repro: `OFFLINE_MODE=true scripts/dev.sh up`; open the dashboard, wait for the live session to flag, click "Open alert", press Play under Evidence. `curl "localhost:8000/sessions/mrs-k-22/replay?t_start=40&t_end=60"` → every frame has `"poses": [], "hands": []`.
Expected: a simple stick-figure pose (and a hand near the active object) in each synthetic frame, moving between the objects of each step; Usual replay differs visibly from Today. Actual: boxes only.
Interface: `_synthetic_frames` (and whatever builds the replay stand-in frames) fill `poses`/`hands` with keypoints per the `contracts/` CaptureFrame schema (no contract change); see `contracts/examples/capture.jsonl` for the shape.
Acceptance:
- Pipeline test: synthetic live frames and `/sessions/{id}/replay` frames have ≥1 pose with keypoints in [0,1].
- No change to step/error/flag results: `scripts/e2e.sh` still 23/23.
- `scripts/ci.sh` passes.

### T208 — Bug: ghost replay "Today" caption is dark blue on the dark card, unreadable
- status: done
- class: light
- priority: 1
- kind: bug
- deps: —
- area: web/src/evidence/GhostReplay.tsx, web/src/evidence/
- owner: ian-claude-light-2
- claimed: 2026-10-17T09:47Z
- pr: #191
- rating: 5/5 clear

What: Tester (main 355d6b1). `web/src/evidence/GhostReplay.tsx:44` colours the caption with inline `color: 'blue'` / `'grey'`; on the dark evidence card "Today" is near-invisible. Use the colours the replay strokes use (CSS classes, no inline styles) so both labels are readable and match the lines they name.
Repro: `OFFLINE_MODE=true scripts/dev.sh up`, open alert-mrs-k, scroll to Evidence: caption under the replay.
Acceptance:
- No inline colour in the figcaption; "Today" and "Usual" each match their replay stroke colour and pass WCAG AA contrast on the card background.
- `cd web && npm test` and `scripts/ci.sh` pass.
