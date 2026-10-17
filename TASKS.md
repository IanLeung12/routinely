# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: e5558ab

## Tasks

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
- note: released by ian-claude-light-2: run ended without progress; partial work on branch task/T187-wip-1503: start from it (git switch task/T187-wip-1503 && git merge origin/main)

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

### T290 — Alert: errors by time of day (morning / afternoon / evening)
- status: todo
- class: heavy
- priority: 3
- kind: feature
- source: proposed
- deps: T284
- area: web/src/alert/TimeOfDayStrip.tsx, web/src/alert/TimeOfDayStrip.test.tsx, web/src/alert/AlertView.tsx, pipeline/src/routine_watch/api_alerts.py, pipeline/tests/test_time_of_day.py, contracts/alert_detail.schema.json, web/src/contracts.ts
- owner: —
- claimed: —
- pr: —

What: Rationale: evening-only worsening (SPEC §7.5, already in pipeline/src/routine_watch/patterns.py) appears on the alert as text only; a nurse can't see why. Show a small strip of errors per session bucketed morning/afternoon/evening over the last 14 days, as visible evidence for that pattern.
Interface: optional alert-detail field `errors_by_time_of_day: [{bucket: "morning"|"afternoon"|"evening", sessions: int, errors: int}]` (buckets <12:00, 12:00–17:00, ≥17:00 local); contracts change, so regenerate alert_detail.schema.json and update web/src/contracts.ts and every consumer in this PR. `<TimeOfDayStrip>` under the error list, caption "Errors by time of day, last 14 days"; hidden when the field is absent. No "diagnos" wording.
Acceptance:
- pytest: buckets from mrs-k demo history; summed errors equal the 14-day total; payload validates against the schema.
- Vitest: three buckets with text labels (not colour only); hidden when absent.
- `scripts/ci.sh` and `scripts/e2e.sh` pass.

### T292 — Review: generate web resident/handoff/monitoring types from contracts.py
- status: in-review
- class: standard
- priority: 2
- kind: improvement
- source: reviewer
- deps: T291
- area: pipeline/src/routine_watch/contracts.py, web/src/contracts.ts, web/src/overview/types.ts, web/src/handoff/types.ts, web/src/about/monitoringApi.ts, pipeline/tests/test_contracts.py
- owner: ian-claude-standard
- claimed: 2026-10-17T15:14Z
- pr: #297
- rating: 5/5 clear, required judgment on Handoff's always-optional fields but task scope was well-defined

What: T269/T280 added JSON Schemas for `ResidentSummary`/`Resident`, `Handoff` and room monitoring, but the web still hand-mirrors them (`web/src/overview/types.ts` ResidentSummary/TopPattern/consent, `web/src/handoff/types.ts` Handoff/HandoffResident/PausedRoom, `web/src/about/monitoringApi.ts` MonitoringChange). T291 only covers drift/patterns/replay. Same fix, after T291 lands: emit these models into the generated `web/src/contracts.ts` and have those files re-export the generated types.
Acceptance:
- The listed web files re-export (or are replaced by) generated types; no hand-written copy of these shapes left.
- `test_generated_files_are_up_to_date` covers them; existing web tests pass with import-only changes.
- `scripts/ci.sh` passes.

### T293 — Test: api_state.reset() clears feedback without replacing the store
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_api_state.py
- owner: ian-claude-light-2
- claimed: 2026-10-17T14:31Z
- pr: #282
- rating: 5/5 clear

What: T284 moved the feedback store to `api_state.py`; routers import `_feedback_store` at load time, so `reset()` must clear it in place. Pin that with a direct unit test.
Interface: Read `pipeline/src/routine_watch/api_state.py` and `pipeline/tests/test_api_feedback.py` (for how feedback is recorded). New file `pipeline/tests/test_api_state.py`: keep a reference `store = api_state._feedback_store`, record one feedback answer, call `api_state.reset()`, assert `api_state._feedback_store is store` and the answer is gone; also assert `_flagged_residents()` returns only residents whose raw `status` is "flagged". Test-only.
Acceptance: `cd pipeline && python -m pytest tests/test_api_state.py -q` passes; `scripts/ci.sh` passes.

### T294 — Test: shift handoff works keyboard-only
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/handoff/Handoff.test.tsx
- owner: ian-claude
- claimed: 2026-10-17T15:14Z
- pr: #285
- rating: 4/5 clear, but the task didn't say the handoff screen already had a user-event-free copy test to match, and 'fix CI on PR #285' hid that the failure was tsc in npm run build, not vitest

What: Nurses at a shared workstation may use only the keyboard; prove the handoff screen's "Copy summary" and back button need no mouse.
Interface: Read `web/src/handoff/Handoff.tsx` and its test. With `@testing-library/user-event`: Tab to "Copy summary", press Enter, check the status text ("Copied" with a mocked `navigator.clipboard.writeText`); Tab to the back button, press Enter, check `onBack` was called. Test-only: if a real keyboard bug shows up, describe it in the PR body instead of fixing it.
Acceptance: `cd web && npx vitest run src/handoff/Handoff.test.tsx` passes; `scripts/ci.sh` passes.

### T295 — Test: unit overview opens a resident keyboard-only
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/overview/UnitOverview.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T14:48Z
- pr: #288
- rating: 5/5 clear

What: The first demo step is opening Mrs. K from the unit overview; prove a keyboard user can do it.
Interface: Read `web/src/overview/UnitOverview.tsx` and its test. With `@testing-library/user-event`: Tab until a resident row's control is focused, press Enter, assert the select/open callback fires with that resident's id; also Tab to a status filter and activate it with Space. Test-only: if a real keyboard bug shows up, describe it in the PR body instead of fixing it.
Acceptance: `cd web && npx vitest run src/overview/UnitOverview.test.tsx` passes; `scripts/ci.sh` passes.

### T296 — Scenarios: meds_unclear_not_error and meds_bad_sessions_far_apart
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/meds_unclear_not_error/, tests/scenarios/meds_bad_sessions_far_apart/
- owner: ian-claude-standard
- claimed: 2026-10-17T14:39Z
- pr: #284
- rating: 5/5 clear

What: The meds routine lacks the two "must not flag" scenarios the tea routine has. Mirror `tests/scenarios/tea_unclear_not_error` and `tests/scenarios/tea_bad_sessions_far_apart` for meds (step names from the meds task graph and the existing `meds_*` scenarios), so a low-confidence meds moment is never counted as an error and two isolated bad meds sessions do not raise a flag.
Interface: two new scenario dirs, each `expected.yaml` + `steps.jsonl` (format in `tests/scenarios/README.md`). No pipeline code changes; if a scenario exposes a pipeline bug, say so in the PR and leave the expectation matching SPEC §7.
Acceptance:
- `scripts/e2e.sh tests/scenarios/meds_unclear_not_error` and `scripts/e2e.sh tests/scenarios/meds_bad_sessions_far_apart` PASS; `scripts/e2e.sh` all PASS.
- `scripts/ci.sh` passes.

### T297 — Web: page title names the screen and resident
- status: done
- class: standard
- priority: 3
- kind: improvement
- deps: —
- area: web/src/ui/useDocumentTitle.ts, web/src/ui/useDocumentTitle.test.ts, web/src/App.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T14:45Z
- pr: #286
- rating: 5/5 clear

What: Every tab reads "Routine Watch", so a nurse with several tabs open (or a screen reader announcing the page) can't tell the overview from Mrs. K's alert. Add a small `useDocumentTitle(title)` hook and set it once per route in `App.tsx`: "Unit overview — Routine Watch", "<resident> — Routine Watch", "Alert · <resident> — Routine Watch", "Shift handoff — Routine Watch", etc. (use names already available at the route level; fall back to the screen name).
Interface: `export function useDocumentTitle(title: string): void` in `web/src/ui/useDocumentTitle.ts` (sets `document.title`, restores the previous title on unmount).
Acceptance:
- Vitest test for the hook: sets the title, updates on change, restores on unmount.
- No changes to screen components outside `App.tsx`; `scripts/ci.sh` passes.

### T298 — Test: pattern library works keyboard-only
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/patterns/PatternLibrary.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T14:54Z
- pr: #289
- rating: 5/5 clear

What: Add a test that the pattern library screen is usable with the keyboard alone, like T287 did for alert feedback (see `web/src/alert/FeedbackButtons.test.tsx` for the style).
Interface: read `web/src/patterns/PatternLibrary.tsx`, `web/src/patterns/PatternLibrary.test.tsx`, `web/src/alert/FeedbackButtons.test.tsx`. Only edit `web/src/patterns/PatternLibrary.test.tsx`.
Acceptance:
- Test tabs to the Back button with `@testing-library/user-event` (or `fireEvent.keyDown` if user-event isn't installed), presses Enter, and asserts `onBack` was called once.
- Test asserts every pattern name is an `h3` under the page's heading (heading order intact for screen readers).
- `cd web && npx vitest run src/patterns` and `scripts/ci.sh` pass.

### T299 — Scenarios: meds_single_bad_no_flag and meds_pill_three_times
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/meds_single_bad_no_flag/, tests/scenarios/meds_pill_three_times/
- owner: ian-claude-standard-2
- claimed: 2026-10-17T14:55Z
- pr: #291
- rating: 5/5 clear

What: The meds routine has fewer scenarios than tea. Mirror `tea_single_bad_no_flag` (one bad session among normal ones must not flag) and `tea_teabag_three_times` (a step repeated three times) for the meds routine, so the tester's e2e covers both routines equally.
Interface: new dirs `tests/scenarios/<name>/{steps.jsonl,expected.yaml}` in the same format as `tests/scenarios/tea_single_bad_no_flag/` and `tests/scenarios/meds_pill_twice/`. No pipeline code changes; if a scenario exposes a pipeline bug, keep the expected (correct) behaviour, mark it as known-failing the way tests/scenarios/README.md describes (or note it in the PR) and say so in the PR.
Acceptance:
- Both scenarios run in `scripts/e2e.sh` and pass.
- `meds_single_bad_no_flag` expects no flag; `meds_pill_three_times` expects the repeated-step error type used by `meds_pill_twice`.
- `scripts/ci.sh` and `scripts/e2e.sh` pass.

### T300 — Pattern library: filter by urgency
- status: done
- class: standard
- priority: 3
- kind: feature
- source: proposed
- deps: —
- area: web/src/patterns/PatternLibrary.tsx, web/src/patterns/PatternLibrary.test.tsx, web/src/patterns/urgencyFilter.css
- owner: ian-claude-standard
- claimed: 2026-10-17T15:04Z
- pr: #293
- rating: 5/5 clear

What: Rationale: the library lists every pattern in one long column; a nurse wants to see "what needs checking this shift" first. Add a row of filter buttons (All / Urgent / Check this shift / Check next round / Routine) above the list.
Interface: `PatternLibrary` keeps fetching the same data; filter state is local (`useState`), buttons use `aria-pressed`, labels come from the existing `URGENCY_LABELS`. Put new styles in the new `urgencyFilter.css` (don't touch `PatternLibrary.css`, T240 owns it). Separate screen, not on the demo path.
Acceptance:
- Default is All; picking a level shows only those patterns; a level with no patterns shows an `EmptyState` ("No patterns at this level."), not an error.
- Buttons are reachable and togglable by keyboard; test covers filtering and the empty case.
- `cd web && npx vitest run src/patterns` and `scripts/ci.sh` pass.

### T301 — Review: contract schema + smoke check for GET /residents/{id}/feedback
- status: todo
- class: heavy
- priority: 1
- kind: improvement
- source: reviewer
- deps: T291
- area: pipeline/src/routine_watch/contracts.py, contracts/resident_feedback.schema.json, contracts/README.md, web/src/contracts.ts, web/src/resident/types.ts, pipeline/tests/test_api_payload_contracts.py, scripts/smoke.sh
- owner: —
- claimed: —
- pr: —

What: T283 added `GET /residents/{id}/feedback` (`api_residents.resident_feedback`) returning `{resident_id, answers[{alert_id, verdict, cause, at}], pattern_weights, pattern_names}`, but there is no model in `contracts.py`/schema in `contracts/`, and `web/src/resident/types.ts` hand-writes `FeedbackAnswer`/`ResidentFeedback` (already missing `resident_id`). Same drift class as T250/T292. Fix: add `ResidentFeedback` (+ `FeedbackAnswer`) pydantic models in `contracts.py`, generate `contracts/resident_feedback.schema.json` and the TS type into `web/src/contracts.ts`, make `types.ts` re-export it, validate the route body in `test_api_payload_contracts.py`, and add a `check_schema` for `GET /residents/mrs-k/feedback` in `scripts/smoke.sh`.
Acceptance:
- Route body validates against the new schema in a pipeline test (empty, and with one answer + cause).
- `web/src/resident/types.ts` has no hand-written copy of these shapes; `test_generated_files_are_up_to_date` covers it.
- `scripts/ci.sh` passes.

### T302 — Test: alert view works keyboard-only
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/alert/AlertView.keyboard.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T15:06Z
- pr: #294
- rating: 5/5 clear

What: Like T295 (`web/src/overview/UnitOverview.test.tsx`, keyboard section), prove a nurse can work Mrs. K's alert with Tab/Enter/Space only.
Interface: read `web/src/alert/AlertView.tsx`, `web/src/alert/AlertView.test.tsx` (for fixtures/mocks) and `web/src/alert/FeedbackButtons.test.tsx`. New file only; use `@testing-library/user-event` `user.tab()` / `user.keyboard('{Enter}')`.
Acceptance:
- Test tabs from the top of the alert to each feedback button and confirms one with the keyboard; the confirmation text appears; no element in the tab order lacks an accessible name.
- If a real keyboard trap is found, don't fix it: note it in the PR body.
- `cd web && npx vitest run src/alert` and `scripts/ci.sh` pass.

### T303 — Test: resident detail works keyboard-only
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/resident/ResidentDetail.keyboard.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T15:18Z
- pr: #295
- rating: 5/5 clear

What: Prove a nurse can move through Mrs. K's resident page (drift card, heat calendar, feedback history, back button) with keyboard only.
Interface: read `web/src/resident/ResidentDetail.tsx` and `web/src/resident/ResidentDetail.test.tsx` (copy its fetch mocks). New file only; `user-event` `user.tab()`.
Acceptance:
- Test reaches the back control and every interactive element on the page by Tab, each has an accessible name, and Enter on back calls the back handler.
- Real keyboard bugs are noted in the PR body, not fixed here.
- `cd web && npx vitest run src/resident` and `scripts/ci.sh` pass.

### T304 — Test: demo reset clears feedback history
- status: claimed
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_feedback_reset.py
- owner: ian-claude
- claimed: 2026-10-17T15:24Z
- pr: —

What: `GET /residents/{id}/feedback` (T283) must be empty again after `/demo/reset`, or a second demo run shows the first run's answers.
Interface: read `pipeline/src/routine_watch/api_state.py` (`reset`), `pipeline/src/routine_watch/feedback.py` (`history`, `reset`), and `pipeline/tests/test_feedback_history.py` for the client fixture. New file only.
Acceptance:
- Test posts a feedback answer for an alert, sees it in `/residents/{id}/feedback`, calls `/demo/reset`, then sees `answers == []` and `pattern_weights == {}`.
- `cd pipeline && python -m pytest tests/test_feedback_reset.py` and `scripts/ci.sh` pass.

### T305 — Feedback history card: usable at phone width (375 px)
- status: todo
- class: light
- priority: 3
- kind: improvement
- deps: —
- area: web/src/resident/feedbackHistory.css, web/src/resident/FeedbackHistory.mobile.test.tsx
- owner: —
- claimed: —
- pr: —

What: Same as T247 but for the new feedback history card on the resident page: no horizontal scroll and readable rows at 375 px.
Interface: read `web/src/resident/FeedbackHistory.tsx` and `web/src/resident/feedbackHistory.css`. CSS-only change (add a `@media (max-width: 480px)` block); don't edit the component.
Acceptance:
- At ≤480 px each answer's verdict, cause and time wrap onto their own lines instead of overflowing; long pattern names wrap (`overflow-wrap: anywhere`).
- The new test asserts the card renders its rows with the classes the media query targets (jsdom can't measure layout).
- `cd web && npx vitest run src/resident` and `scripts/ci.sh` pass.

### T306 — Test: live screen works keyboard-only
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: web/src/live/LiveScreen.keyboard.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T15:16Z
- pr: #296
- rating: 5/5 clear

What: The demo path runs through the live screen, but only the other screens have keyboard-only tests (T287, T295, T298). Prove a nurse can pick a routine, start the session and open its alert using only Tab/Enter/Space, with the mock live stream.
Interface: new `web/src/live/LiveScreen.keyboard.test.tsx` only; render `LiveScreen` with the existing mock stream (`mockLiveStream.ts`, fake timers) as `LiveScreen.test.tsx` does; drive with `@testing-library/user-event` keyboard/tab only (no `click`).
Acceptance:
- Tab reaches the routine picker, arrow/Enter selects a routine, Tab+Enter starts the session; the task map and session summary render.
- When the mock session ends with a flag, the link/button to the alert is reachable by Tab and activates with Enter.
- Every focused control has an accessible name (`getByRole(..., { name })`).
- No production files changed. `cd web && npm test -- LiveScreen.keyboard` and `scripts/ci.sh` pass.

### T307 — Test: replay player works keyboard-only
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/evidence/ReplayPlayer.keyboard.test.tsx
- owner: —
- claimed: —
- pr: —
- note: released by ian-claude-light-2: run ended without progress; partial work on branch task/T307-wip-1531: start from it (git switch task/T307-wip-1531 && git merge origin/main)

What: Prove the evidence replay player (play/pause, scrub, ghost toggle) is usable with Tab/Enter/Space/arrow keys only.
Interface: new test file only; read web/src/evidence/ReplayPlayer.tsx, web/src/evidence/ReplayPlayer.test.tsx and web/src/alert/AlertView.keyboard.test.tsx (copy its style).
Acceptance:
- Test tabs to each control, operates it by keyboard, asserts the visible state changes; no mouse events used.
- If a control is unreachable, mark that case `it.todo` and say so in the PR (don't change ReplayPlayer.tsx).
- `scripts/ci.sh` passes.

### T308 — Test: privacy panel and monitoring toggle work keyboard-only
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/about/PrivacyPanel.keyboard.test.tsx
- owner: —
- claimed: —
- pr: —

What: Prove the privacy panel opens/closes and the room monitoring pause/resume toggle works with keyboard only (Tab, Enter/Space, Escape).
Interface: new test file only; read web/src/about/PrivacyPanel.tsx, web/src/about/MonitoringToggle.tsx, their .test.tsx files, and web/src/alert/AlertView.keyboard.test.tsx for style. Mock the API as the existing tests do.
Acceptance:
- Keyboard-only: open panel, reach the toggle, pause then resume a room, focus is not lost after each action.
- No production code changes. `scripts/ci.sh` passes.

### T309 — Monitoring history card: usable at phone width (375 px)
- status: todo
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/MonitoringHistory.tsx, web/src/resident/monitoringHistory.css, web/src/resident/MonitoringHistory.test.tsx
- owner: —
- claimed: —
- pr: —

What: The resident page's monitoring audit trail (who paused/resumed, when) should read cleanly at 375 px, matching how T239 made resident detail work on phones.
Interface: CSS media query in monitoringHistory.css; markup changes only if needed for wrapping.
Acceptance:
- At 375 px: no horizontal scroll, rows wrap to two lines (who/action, then time), text >= 14 px.
- Test asserts the wrapping class/structure is present; `scripts/ci.sh` passes.

### T310 — Test: pattern library urgency + level filters combine correctly
- status: todo
- class: standard
- priority: 2
- kind: test
- deps: —
- area: web/src/patterns/PatternLibrary.filters.test.tsx
- owner: —
- claimed: —
- pr: —

What: T300 added an urgency filter next to the existing level filter; test that both together narrow the list, that clearing one keeps the other, and that "no match" shows the empty state.
Interface: new test file only; read web/src/patterns/PatternLibrary.tsx and PatternLibrary.test.tsx.
Acceptance:
- Covers: urgency only, level only, both, both with zero matches (empty state text), reset.
- Filters reachable and operable by keyboard in at least one case.
- `scripts/ci.sh` passes.
