# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: ca08f66

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
- status: claimed
- class: heavy
- priority: 1
- kind: improvement
- source: reviewer
- deps: T291
- area: pipeline/src/routine_watch/contracts.py, contracts/resident_feedback.schema.json, contracts/README.md, web/src/contracts.ts, web/src/resident/types.ts, pipeline/tests/test_api_payload_contracts.py, scripts/smoke.sh
- owner: ian-claude
- claimed: 2026-10-17T16:03Z
- pr: —
- note: released by ian-claude: run ended without progress; partial work on branch task/T301-wip-1548: start from it (git switch task/T301-wip-1548 && git merge origin/main)

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
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_feedback_reset.py
- owner: ian-claude
- claimed: 2026-10-17T15:24Z
- pr: #298
- rating: 4/5 the acceptance it spells out was already covered by test_feedback_history.py::test_demo_reset_empties_what_nurses_said; the new file's value is the second-demo-run angle (weights/threshold counted from scratch, fresh alert unanswered), which the task only hints at in its 'What'

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
- status: claimed
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/evidence/ReplayPlayer.keyboard.test.tsx
- owner: max_API_light
- claimed: 2026-10-17T15:44Z
- pr: —
- note: released by ian-claude-light-2: run ended without progress; partial work on branch task/T307-wip-1531: start from it (git switch task/T307-wip-1531 && git merge origin/main)

What: Prove the evidence replay player (play/pause, scrub, ghost toggle) is usable with Tab/Enter/Space/arrow keys only.
Interface: new test file only; read web/src/evidence/ReplayPlayer.tsx, web/src/evidence/ReplayPlayer.test.tsx and web/src/alert/AlertView.keyboard.test.tsx (copy its style).
Acceptance:
- Test tabs to each control, operates it by keyboard, asserts the visible state changes; no mouse events used.
- If a control is unreachable, mark that case `it.todo` and say so in the PR (don't change ReplayPlayer.tsx).
- `scripts/ci.sh` passes.

### T308 — Test: privacy panel and monitoring toggle work keyboard-only
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/about/PrivacyPanel.keyboard.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T15:46Z
- pr: #302
- rating: 5/5 clear

What: Prove the privacy panel opens/closes and the room monitoring pause/resume toggle works with keyboard only (Tab, Enter/Space, Escape).
Interface: new test file only; read web/src/about/PrivacyPanel.tsx, web/src/about/MonitoringToggle.tsx, their .test.tsx files, and web/src/alert/AlertView.keyboard.test.tsx for style. Mock the API as the existing tests do.
Acceptance:
- Keyboard-only: open panel, reach the toggle, pause then resume a room, focus is not lost after each action.
- No production code changes. `scripts/ci.sh` passes.

### T309 — Monitoring history card: usable at phone width (375 px)
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/MonitoringHistory.tsx, web/src/resident/monitoringHistory.css, web/src/resident/MonitoringHistory.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T15:36Z
- pr: #299
- rating: 5/5 clear

What: The resident page's monitoring audit trail (who paused/resumed, when) should read cleanly at 375 px, matching how T239 made resident detail work on phones.
Interface: CSS media query in monitoringHistory.css; markup changes only if needed for wrapping.
Acceptance:
- At 375 px: no horizontal scroll, rows wrap to two lines (who/action, then time), text >= 14 px.
- Test asserts the wrapping class/structure is present; `scripts/ci.sh` passes.

### T310 — Test: pattern library urgency filter (every option, reset, empty state)
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/patterns/PatternLibrary.filters.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T15:57Z
- pr: #304
- note: rewritten by orchestrator: the library has one filter (urgency); there is no level filter. Test that one axis only.
- rating: 5/5 clear

What: The pattern library has a single urgency filter (T300). Test each option narrows the list to matching patterns, "All" restores the full list, and an urgency with no matching patterns shows the empty state.
Interface: new test file only. Read web/src/patterns/PatternLibrary.tsx and web/src/patterns/PatternLibrary.test.tsx (copy its fetch mock). Do not change PatternLibrary.tsx.
Acceptance:
- Covers: every urgency button, "All" reset, exactly one button has aria-pressed="true", empty state when a mocked list has no pattern of the chosen urgency.
- At least one case operates the filter by keyboard (Tab + Enter/Space).
- `scripts/ci.sh` passes.

### T311 — Test: handoff payload without `paused` / `monitoring_paused` still validates and renders
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_handoff_defaults.py, web/src/handoff/Handoff.defaults.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T15:42Z
- pr: #300
- rating: 5/5 clear

What: T292 (#297) made `Handoff.paused` and `HandoffResident.monitoring_paused` optional with defaults (false / []); lock that in on both sides so an older or trimmed payload never breaks the shift handoff.
Interface: new test files only; read pipeline/src/routine_watch/contracts.py (Handoff, HandoffResident, PausedRoom), web/src/handoff/Handoff.tsx, web/src/handoff/mockHandoff.ts.
Acceptance:
- Pipeline: a Handoff dict without `paused` and residents without `monitoring_paused` validates; defaults are `[]` / `False`; round-trips through `model_dump`.
- Web: Handoff renders a payload missing both fields with no crash, no paused-rooms section, and no "paused" label on any row.
- `scripts/ci.sh` passes.

### T312 — Test: resident detail feedback history after reset shows the empty state
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: web/src/resident/ResidentDetail.reset.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T15:47Z
- pr: #301
- rating: 5/5 clear

What: T304 (#298) proved the API clears feedback on demo reset; add the dashboard side: after a reset the resident detail "What nurses said" card shows "No nurse answers yet" instead of stale answers.
Interface: new test file only; read web/src/resident/ResidentDetail.tsx and its existing tests for how the feedback API is mocked; pipeline/tests/test_feedback_reset.py for the reset behaviour.
Acceptance:
- Mock feedback API returns one answer, then an empty list after a reset; the card updates to the empty-state text on re-fetch/re-mount.
- No raw video or real API calls; fakes only.
- `scripts/ci.sh` passes.

### T313 — Scenarios: meds_two_errors_one_session and meds_pill_substitution
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/meds_two_errors_one_session/, tests/scenarios/meds_pill_substitution/, tests/scenarios/README.md
- owner: ian-claude-standard-2
- claimed: 2026-10-17T15:56Z
- pr: #305
- rating: 5/5 clear

What: Meds still lacks two cases tea has. Add a meds session with two different errors in one session (e.g. skipped water plus pill taken twice), and a substitution case mirroring `tea_substitution` if the meds graph (pipeline/src/routine_watch/tasks/meds.yaml) allows one; otherwise pick another error type tea covers and meds doesn't, and say which in the PR.
Interface: new dirs `tests/scenarios/<name>/{steps.jsonl,expected.yaml}` in the format of `tests/scenarios/meds_pill_twice/` and `tests/scenarios/tea_substitution/`; add both to the README list. No pipeline code changes; if a scenario exposes a pipeline bug, keep the correct expected behaviour, mark it known-failing as tests/scenarios/README.md describes, and say so in the PR.
Acceptance:
- Both scenarios run in `scripts/e2e.sh`; the two-error one expects both error types.
- `scripts/ci.sh` and `scripts/e2e.sh` pass.

### T314 — Scenarios: tea_two_errors_one_session and tea_long_pause_not_error
- status: in-review
- class: standard
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/tea_two_errors_one_session/, tests/scenarios/tea_long_pause_not_error/
- owner: ian-claude-standard
- claimed: 2026-10-17T15:56Z
- pr: #303
- rating: 5/5 clear task, well-specified acceptance criteria and known README conflict called out in advance
- note: PR #303 CI fails only on test_scenarios_readme_lists_every_scenario_folder (tea_two_errors_one_session, tea_long_pause_not_error not yet in README.md, which T313 owns per this task's own instructions not to edit it). Scenarios themselves pass scripts/e2e.sh and all other tests pass. Needs a follow-up task to add these two rows to tests/scenarios/README.md once T313 settles.

What: Add a tea session with two different errors in one session, and a correct session with one unusually long gap between steps that must produce no task error (long gaps are hesitations from `hesitation.py`, not errors) and no flag.
Interface: new dirs `tests/scenarios/<name>/{steps.jsonl,expected.yaml}` in the format of `tests/scenarios/tea_normal/` and `tests/scenarios/tea_sequence_error/`. Read pipeline/src/routine_watch/hesitation.py. Don't edit tests/scenarios/README.md (T313 owns it); list the two names in the PR body. If the README-lists-every-scenario test then fails, add a deps-free follow-up note in the PR rather than widening scope. No pipeline code changes; bugs found → known-failing + PR note.
Acceptance:
- Both run in `scripts/e2e.sh`; the long-pause one expects zero errors and no flag.
- `scripts/ci.sh` and `scripts/e2e.sh` pass.

### T315 — Refactor: shared fake WebSocket helper for live tests
- status: claimed
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/live/testWebSocket.ts, web/src/live/LiveSession.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T16:03Z
- pr: —

What: web/src/live/LiveSession.test.tsx is 625 lines, much of it hand-rolled WebSocket mocking. Move the fake socket and message helpers into `web/src/live/testWebSocket.ts` and use them from LiveSession.test.tsx, with no change to what is tested.
Interface: `testWebSocket.ts` exports a fake socket class/installer and a helper to push server messages; test-only (never imported by app code).
Acceptance:
- Same number of test cases before and after (state both counts in the PR); LiveSession.test.tsx at least 100 lines shorter.
- No app code changes. `scripts/ci.sh` passes.

### T316 — Test: every scenario uses real task-graph step ids
- status: claimed
- class: standard
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_scenario_step_ids.py
- owner: ian-claude-standard-2
- claimed: 2026-10-17T16:07Z
- pr: —

What: A typo in a scenario's step id silently makes it test nothing. Add a pipeline test that loads every `tests/scenarios/*/` scenario and checks each step id it references (steps.jsonl and expected.yaml errors) exists in that scenario's task graph.
Interface: use `routine_watch.replay.load_scenario` and `routine_watch.tasks.load_task`; read pipeline/src/routine_watch/replay.py and tasks/graph.py. Parametrise over scenario folders.
Acceptance:
- Failure message names the scenario and the bad id (show it once locally, note in PR).
- An existing scenario with a bad id is not fixed here: mark that case xfail with the reason and note it in the PR.
- `scripts/ci.sh` passes.

### T317 — Test: each screen sets its page title
- status: todo
- class: light
- priority: 3
- kind: test
- deps: —
- area: web/src/App.title.test.tsx
- owner: —
- claimed: —
- pr: —

What: T297 made document.title name the screen and resident. Add one App-level test that navigates to the overview, a resident, and the pattern library and checks document.title each time.
Interface: new test file only. Read web/src/App.tsx, web/src/ui/useDocumentTitle.ts and web/src/App.test.tsx (copy its fetch mocks and navigation setup).
Acceptance:
- Three cases, each asserting the exact title the app sets (read it from the code, e.g. "Mrs. K — Routine Watch").
- `scripts/ci.sh` passes.

### T318 — Unit overview: sort residents by most recent change
- status: todo
- class: standard
- priority: 3
- kind: feature
- source: proposed
- deps: —
- area: web/src/overview/ResidentSort.tsx, web/src/overview/ResidentSort.test.tsx, web/src/overview/UnitOverview.tsx
- owner: —
- claimed: —
- pr: —

What: Rationale: on a busy unit the nurse wants the newest flags first. Add a small sort control ("Default order" / "Most recent change first") to the unit overview; the default keeps today's order so the demo path is unchanged.
Interface: `ResidentSort.tsx` exports the control and a pure `sortResidents(residents, mode)`; UnitOverview uses it. Read web/src/overview/UnitOverview.tsx for the resident fields (use the latest flag/alert time it already has; if none exists, sort by status urgency and say so in the PR). No API or contract changes.
Acceptance:
- Unit tests for `sortResidents` (both modes, stable ties) and one UI test switching the control by keyboard.
- Default order identical to before (existing UnitOverview tests untouched and passing).
- `scripts/ci.sh` passes.

### T319 — Bug: integration check failing on main
- status: todo
- class: standard
- priority: 0
- kind: bug
- deps: —
- area: scripts/dev.sh, pipeline/src/routine_watch/api.py, web/src/
- owner: —
- claimed: —
- pr: —
- source: integration

What: `scripts/integration.sh` (stack up offline → API endpoints → dashboard render → live WebSocket) fails on main @ 08ab990:
  FAIL dashboard did not render (no 'Routine Watch' in DOM)
Interface: reproduce with `scripts/integration.sh`; logs in `.dev/api.log` / `.dev/web.log`. Fix the cause (not the check) unless the check itself is wrong.
Acceptance:
- `scripts/integration.sh` prints OK; `scripts/ci.sh` passes.

### T320 — Test: unit overview works keyboard-only
- status: claimed
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/overview/UnitOverview.keyboard.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T16:05Z
- pr: —

What: Add a keyboard-only test for the unit overview, mirroring `web/src/about/PrivacyPanel.keyboard.test.tsx` and `web/src/alert/AlertView.keyboard.test.tsx`.
Interface: read `web/src/overview/UnitOverview.tsx`, `web/src/overview/UnitOverview.test.tsx` (mocks/fixtures) and one existing `*.keyboard.test.tsx`. Create only `web/src/overview/UnitOverview.keyboard.test.tsx`.
Acceptance:
* Tab reaches every resident card/link in DOM order; Enter on a card opens that resident (assert the callback/route the existing tests use).
* Every focusable element has an accessible name.
* If a real bug is found, don't fix it; note it in the PR body.
* `cd web && npm test -- UnitOverview.keyboard` passes; `scripts/ci.sh` passes.

### T321 — Test: shift handoff works keyboard-only
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/handoff/Handoff.keyboard.test.tsx
- owner: —
- claimed: —
- pr: —

What: Add a keyboard-only test for the shift handoff screen, mirroring `web/src/alert/AlertView.keyboard.test.tsx`.
Interface: read `web/src/handoff/Handoff.tsx`, `web/src/handoff/Handoff.test.tsx`, `web/src/handoff/mockHandoff.ts` and one existing `*.keyboard.test.tsx`. Create only `web/src/handoff/Handoff.keyboard.test.tsx`.
Acceptance:
* Tab reaches each resident entry and each open-alert link/button in DOM order; Enter activates it (assert the callback/route the existing tests use).
* Every focusable element has an accessible name.
* If a real bug is found, don't fix it; note it in the PR body.
* `cd web && npm test -- Handoff.keyboard` passes; `scripts/ci.sh` passes.
