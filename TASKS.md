# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: dc9a6ef

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
- status: claimed
- class: heavy
- priority: 3
- kind: feature
- source: proposed
- deps: T284
- area: web/src/alert/TimeOfDayStrip.tsx, web/src/alert/TimeOfDayStrip.test.tsx, web/src/alert/AlertView.tsx, pipeline/src/routine_watch/api_alerts.py, pipeline/tests/test_time_of_day.py, contracts/alert_detail.schema.json, web/src/contracts.ts
- owner: ian-claude
- claimed: 2026-10-17T16:19Z
- pr: —

What: Rationale: evening-only worsening (SPEC §7.5, already in pipeline/src/routine_watch/patterns.py) appears on the alert as text only; a nurse can't see why. Show a small strip of errors per session bucketed morning/afternoon/evening over the last 14 days, as visible evidence for that pattern.
Interface: optional alert-detail field `errors_by_time_of_day: [{bucket: "morning"|"afternoon"|"evening", sessions: int, errors: int}]` (buckets <12:00, 12:00–17:00, ≥17:00 local); contracts change, so regenerate alert_detail.schema.json and update web/src/contracts.ts and every consumer in this PR. `<TimeOfDayStrip>` under the error list, caption "Errors by time of day, last 14 days"; hidden when the field is absent. No "diagnos" wording.
Acceptance:
- pytest: buckets from mrs-k demo history; summed errors equal the 14-day total; payload validates against the schema.
- Vitest: three buckets with text labels (not colour only); hidden when absent.
- `scripts/ci.sh` and `scripts/e2e.sh` pass.

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
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/tea_two_errors_one_session/, tests/scenarios/tea_long_pause_not_error/, tests/scenarios/README.md
- owner: ian-claude-standard-2
- claimed: 2026-10-17T16:19Z
- pr: #303
- rating: 5/5 clear task, well-specified acceptance criteria and known README conflict called out in advance
- note: fix CI on PR #303: T313 has merged; on branch task/T314-tea-scenarios, git merge origin/main, then add rows for tea_two_errors_one_session and tea_long_pause_not_error to tests/scenarios/README.md (now in area)

What: Add a tea session with two different errors in one session, and a correct session with one unusually long gap between steps that must produce no task error (long gaps are hesitations from `hesitation.py`, not errors) and no flag.
Interface: new dirs `tests/scenarios/<name>/{steps.jsonl,expected.yaml}` in the format of `tests/scenarios/tea_normal/` and `tests/scenarios/tea_sequence_error/`. Read pipeline/src/routine_watch/hesitation.py. Don't edit tests/scenarios/README.md (T313 owns it); list the two names in the PR body. If the README-lists-every-scenario test then fails, add a deps-free follow-up note in the PR rather than widening scope. No pipeline code changes; bugs found → known-failing + PR note.
Acceptance:
- Both run in `scripts/e2e.sh`; the long-pause one expects zero errors and no flag.
- `scripts/ci.sh` and `scripts/e2e.sh` pass.

### T315 — Refactor: shared fake WebSocket helper for live tests
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/live/testWebSocket.ts, web/src/live/LiveSession.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T16:03Z
- pr: #306
- rating: 5/5 clear

What: web/src/live/LiveSession.test.tsx is 625 lines, much of it hand-rolled WebSocket mocking. Move the fake socket and message helpers into `web/src/live/testWebSocket.ts` and use them from LiveSession.test.tsx, with no change to what is tested.
Interface: `testWebSocket.ts` exports a fake socket class/installer and a helper to push server messages; test-only (never imported by app code).
Acceptance:
- Same number of test cases before and after (state both counts in the PR); LiveSession.test.tsx at least 100 lines shorter.
- No app code changes. `scripts/ci.sh` passes.

### T316 — Test: every scenario uses real task-graph step ids
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_scenario_step_ids.py
- owner: ian-claude-standard-2
- claimed: 2026-10-17T16:07Z
- pr: #309
- rating: 5/5 clear

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
- status: in-review
- class: standard
- priority: 3
- kind: feature
- source: proposed
- deps: —
- area: web/src/overview/ResidentSort.tsx, web/src/overview/ResidentSort.test.tsx, web/src/overview/UnitOverview.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T16:22Z
- pr: #313
- rating: 5/5 clear

What: Rationale: on a busy unit the nurse wants the newest flags first. Add a small sort control ("Default order" / "Most recent change first") to the unit overview; the default keeps today's order so the demo path is unchanged.
Interface: `ResidentSort.tsx` exports the control and a pure `sortResidents(residents, mode)`; UnitOverview uses it. Read web/src/overview/UnitOverview.tsx for the resident fields (use the latest flag/alert time it already has; if none exists, sort by status urgency and say so in the PR). No API or contract changes.
Acceptance:
- Unit tests for `sortResidents` (both modes, stable ties) and one UI test switching the control by keyboard.
- Default order identical to before (existing UnitOverview tests untouched and passing).
- `scripts/ci.sh` passes.

### T319 — Bug: integration check failing on main
- status: done
- class: standard
- priority: 0
- kind: bug
- deps: —
- area: scripts/dev.sh, pipeline/src/routine_watch/api.py, web/src/
- owner: —
- claimed: —
- pr: —
- source: integration
- note: orch: scripts/integration.sh passes on main dc9a6ef (OK integration); transient at 08ab990

What: `scripts/integration.sh` (stack up offline → API endpoints → dashboard render → live WebSocket) fails on main @ 08ab990:
  FAIL dashboard did not render (no 'Routine Watch' in DOM)
Interface: reproduce with `scripts/integration.sh`; logs in `.dev/api.log` / `.dev/web.log`. Fix the cause (not the check) unless the check itself is wrong.
Acceptance:
- `scripts/integration.sh` prints OK; `scripts/ci.sh` passes.

### T320 — Test: unit overview works keyboard-only
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/overview/UnitOverview.keyboard.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T16:05Z
- pr: #307
- rating: 5/5 clear

What: Add a keyboard-only test for the unit overview, mirroring `web/src/about/PrivacyPanel.keyboard.test.tsx` and `web/src/alert/AlertView.keyboard.test.tsx`.
Interface: read `web/src/overview/UnitOverview.tsx`, `web/src/overview/UnitOverview.test.tsx` (mocks/fixtures) and one existing `*.keyboard.test.tsx`. Create only `web/src/overview/UnitOverview.keyboard.test.tsx`.
Acceptance:
* Tab reaches every resident card/link in DOM order; Enter on a card opens that resident (assert the callback/route the existing tests use).
* Every focusable element has an accessible name.
* If a real bug is found, don't fix it; note it in the PR body.
* `cd web && npm test -- UnitOverview.keyboard` passes; `scripts/ci.sh` passes.

### T321 — Test: shift handoff works keyboard-only
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/handoff/Handoff.keyboard.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T16:16Z
- pr: #311
- rating: 5/5 clear

What: Add a keyboard-only test for the shift handoff screen, mirroring `web/src/alert/AlertView.keyboard.test.tsx`.
Interface: read `web/src/handoff/Handoff.tsx`, `web/src/handoff/Handoff.test.tsx`, `web/src/handoff/mockHandoff.ts` and one existing `*.keyboard.test.tsx`. Create only `web/src/handoff/Handoff.keyboard.test.tsx`.
Acceptance:
* Tab reaches each resident entry and each open-alert link/button in DOM order; Enter activates it (assert the callback/route the existing tests use).
* Every focusable element has an accessible name.
* If a real bug is found, don't fix it; note it in the PR body.
* `cd web && npm test -- Handoff.keyboard` passes; `scripts/ci.sh` passes.

### T322 — Drift card: usable at phone width (375 px)
- status: in-review
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/driftCard.css, web/src/resident/DriftCard.mobile.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T16:23Z
- pr: #312
- rating: 5/5 clear

What: The resident drift card has no small-screen rules; at 375 px it must not scroll sideways and its rows should stack.
Interface: read `web/src/resident/DriftCard.tsx`, `web/src/resident/driftCard.css` and `web/src/resident/resident.css` (copy its `@media (max-width: 480px)` approach). CSS only; no behaviour change. New test `DriftCard.mobile.test.tsx` asserts the card renders with its existing class names (smoke-level, like other `*.mobile.test.tsx` files if any exist).
Acceptance:
- a `@media (max-width: 480px)` block in `driftCard.css`; no fixed widths over 375 px
- `cd web && npm test` and `scripts/ci.sh` pass

### T323 — Live session summary: usable at phone width (375 px)
- status: claimed
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/live/sessionSummary.css, web/src/live/liveSession.css
- owner: max_API_light
- claimed: 2026-10-17T16:23Z
- pr: —

What: `liveScreen.css` and `taskMap.css` already have phone-width rules, but the session summary and live session panels don't; at 375 px they must not scroll sideways and buttons are at least 44 px tall.
Interface: read `web/src/live/SessionSummary.tsx`, `web/src/live/LiveSession.tsx`, the two CSS files, and `web/src/live/liveScreen.css` (copy its `@media (max-width: 480px)` approach). CSS only; no behaviour change.
Acceptance:
- a `@media (max-width: 480px)` block in each of the two CSS files; no fixed widths over 375 px
- existing live tests still pass; `cd web && npm test` and `scripts/ci.sh` pass

### T324 — Shift handoff: "compared with the previous shift" per resident
- status: todo
- class: heavy
- priority: 3
- kind: feature
- source: proposed
- deps: —
- area: pipeline/src/routine_watch/handoff.py, pipeline/tests/test_handoff_previous.py, pipeline/src/routine_watch/contracts.py, contracts/handoff.schema.json, contracts/examples/, web/src/handoff/HandoffDelta.tsx, web/src/handoff/HandoffDelta.test.tsx, web/src/handoff/types.ts, web/src/contracts.ts
- owner: —
- claimed: —
- pr: —

What: Rationale: a nurse coming on shift wants to know if things are getting better or worse, not just counts. Add each resident's `flags` for the previous window of the same length (`previous_flags`) to `/handoff`, and a small "up / down / same vs previous shift" indicator component.
Interface: `build_handoff(now, hours)` adds `previous_flags: int` per resident (window `[now-2h, now-h)`); update `handoff.schema.json`, contracts.py and generated web types; new `HandoffDelta({flags, previousFlags})` component renders e.g. "2 more than last shift" / "same as last shift" with an accessible text (not colour only). Wiring it into `Handoff.tsx` is a follow-up task (keeps this off the files T203/T247 own). Wording: describes counts only, never a diagnosis.
Acceptance:
- pytest covers previous window bounds (session exactly at `now-h` counts in the current window only) and the demo data
- schema + example validate; smoke/contract tests pass
- `HandoffDelta.test.tsx` covers more/fewer/same/zero
- `scripts/ci.sh` passes

### T325 — Test: monitoring toggle works keyboard-only
- status: claimed
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/about/MonitoringToggle.keyboard.test.tsx
- owner: Max_codex_light
- claimed: 2026-10-17T16:23Z
- pr: —

What: The privacy monitoring switch is a key trust control; prove a nurse can pause and resume it with the keyboard alone.
Interface: read `web/src/about/MonitoringToggle.tsx`, `web/src/about/MonitoringToggle.test.tsx` and `web/src/about/PrivacyPanel.keyboard.test.tsx` (copy its user-event keyboard style). New test file only; no component changes (if a bug is found, mark the case `it.fails` and note it in the PR).
Acceptance:
- Tab reaches the switch; Space and Enter each call `onChange` with the flipped value; `aria-checked` matches `on`
- when paused, the "No camera data is processed while paused." text is shown
- `cd web && npm test` and `scripts/ci.sh` pass

### T326 — Test: unit tests for session_log
- status: claimed
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_session_log.py
- owner: ian-claude-light-2
- claimed: 2026-10-17T16:30Z
- pr: —

What: `pipeline/src/routine_watch/session_log.py` (the in-process log that makes a live session count for the demo) has no direct unit test.
Interface: read `pipeline/src/routine_watch/session_log.py`, `pipeline/tests/conftest.py`, and how `pipeline/tests/test_api_demo_reset.py` builds a Session/TaskError. New test file only; use a fixture that calls `session_log.reset()` before and after each test.
Acceptance:
- covers: record then sessions_for (oldest first), errors_for by session id, unknown resident/session gives an empty list, two residents stay separate, reset() clears everything
- `cd pipeline && python -m pytest tests/test_session_log.py` and `scripts/ci.sh` pass

### T327 — Test: unit tests for pattern_features.extract_features
- status: claimed
- class: standard
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_pattern_features.py
- owner: ian-claude-standard-2
- claimed: 2026-10-17T16:26Z
- pr: —

What: `pipeline/src/routine_watch/pattern_features.py` (378 lines; turns sessions + care records into the features the pattern library ranks on) is only tested indirectly through alerts; direct tests make a regression point at the right file.
Interface: read `pattern_features.py`, `patterns_library.py`, and the `pattern_*` scenarios under `tests/scenarios/` for realistic inputs. New test file only; no source changes (bugs found: `pytest.mark.xfail(strict=True)` + PR note).
Acceptance:
- covers at least: flat history (no drift); slow downward trend; sudden change; evening-only worsening; a sedating care record inside its window appears in the context and an old one doesn't; empty sessions don't crash
- deterministic (fixed `now`, no wall clock)
- `cd pipeline && python -m pytest tests/test_pattern_features.py` and `scripts/ci.sh` pass

### T328 — Test: /ws/live WebSocket routes in api_live.py
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_api_live_ws.py
- owner: —
- claimed: —
- pr: —

What: `api_live.py` has no direct test file. Add WebSocket tests with FastAPI `TestClient` for the live route.
Interface: read `pipeline/src/routine_watch/api_live.py`, `pipeline/src/routine_watch/api_state.py`, `pipeline/src/routine_watch/monitoring.py` and one existing API test in `pipeline/tests/` for the client fixture. Call `api_state.reset()` before each test.
Acceptance:
- covers: a normal run sends at least one message then a session-end message; a paused room gets the "paused" message and no step events; an unknown scenario/room gets a clear error or close (whatever the code does today, asserted)
- offline only, no LIVE_API calls
- `scripts/ci.sh` passes

### T329 — Test: resident routes return 404 for an unknown resident
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_api_residents_404.py
- owner: —
- claimed: —
- pr: —

What: Every `/residents/{id}/...` route in `api_residents.py` should answer an unknown id with 404, not 500 or an empty 200.
Interface: read `pipeline/src/routine_watch/api_residents.py` and `pipeline/src/routine_watch/api.py` (router wiring). Parametrise over every GET route under `/residents/{id}` found in `api_residents.py`.
Acceptance:
- one parametrised pytest; each route with id `nobody` returns 404 with a JSON `detail`
- if a route returns something else, don't change product code: mark that case `xfail(strict=True)` with reason and mention it in the PR body
- `scripts/ci.sh` passes

### T330 — Heat calendar: usable at phone width (375 px)
- status: todo
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/heatCalendar.css
- owner: —
- claimed: —
- pr: —

What: Same series as T234/T239: at 375 px the heat calendar must fit without horizontal page scroll and keep readable cells.
Interface: read `web/src/resident/heatCalendar.css`, `web/src/resident/HeatCalendar.tsx`, and the `@media` block in `web/src/overview/overview.css` for the breakpoint convention. CSS only.
Acceptance:
- `@media (max-width: 480px)` rules: cells shrink or the grid scrolls inside its own card (not the page); labels stay ≥ 12 px
- dark theme tokens still used (no hard-coded colours)
- PR body has a 375 px screenshot from `scripts/dev.sh up` (or states why not)
- `scripts/ci.sh` passes

### T331 — Test: heat calendar cells have accessible names
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/resident/HeatCalendar.a11y.test.tsx
- owner: —
- claimed: —
- pr: —

What: Colour alone must not carry meaning. Assert each heat calendar cell exposes its date and error count to screen readers.
Interface: read `web/src/resident/HeatCalendar.tsx` and `web/src/resident/HeatCalendar.test.tsx` (fixture). Use Testing Library `getAllByRole`/`getByLabelText`.
Acceptance:
- every rendered day cell has an accessible name containing the date and the count (e.g. "17 Oct: 2 errors"); zero-error days say "no errors"
- if the component lacks this today, mark the test `it.fails` and say so in the PR body (no product change in this task)
- `scripts/ci.sh` passes

### T332 — Replay and ghost replay respect prefers-reduced-motion
- status: todo
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/evidence/ReplayPlayer.tsx, web/src/evidence/GhostReplay.tsx, web/src/evidence/reducedMotion.ts, web/src/evidence/reducedMotion.test.ts, web/src/evidence/ReplayPlayer.test.tsx
- owner: —
- claimed: —
- pr: —

What: Accessibility: when the OS asks for reduced motion, replays must not autoplay; they show the first (or flagged) frame and wait for Play.
Interface: `prefersReducedMotion(): boolean` in `reducedMotion.ts` (matchMedia, safe when matchMedia is missing); ReplayPlayer and GhostReplay read it on mount. Manual Play still animates.
Acceptance:
- tests mock `matchMedia` both ways: autoplay unchanged when false; no autoplay + Play button focused-able when true
- existing ReplayPlayer keyboard tests still pass
- `scripts/ci.sh` passes

### T333 — Resident detail: print-friendly layout
- status: todo
- class: standard
- priority: 3
- kind: feature
- source: proposed
- deps: —
- area: web/src/resident/residentPrint.css, web/src/resident/ResidentDetail.tsx, web/src/resident/ResidentDetail.print.test.tsx
- owner: —
- claimed: —
- pr: —

What: Rationale: nurses bring a resident's summary to care conferences/family meetings; matches the alert (T289) and handoff (T203) print layouts. Add a Print button and `@media print` styles for resident detail.
Interface: `residentPrint.css` imported by `ResidentDetail.tsx`; a "Print" button calling `window.print()`; print hides nav, buttons and the replay, shows name, consent line, baseline chart, heat calendar, drift card and feedback history on white. Follow the approach of `web/src/alert/alert.css` print rules.
Acceptance:
- test: Print button exists, is keyboard reachable, calls `window.print` (mocked)
- no new wording that diagnoses; screen layout unchanged
- `scripts/ci.sh` passes

### T334 — Test: pattern checks and summaries never use diagnosis wording
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_wording_guard.py
- owner: —
- claimed: —
- pr: —

What: Guard SPEC's wording rule in code: every pattern name, description, rule-out check and generated summary says "consistent with"/"check", never "diagnos", "has <condition>", or treatment advice.
Interface: read `pipeline/src/routine_watch/patterns_library.py`, `pipeline/src/routine_watch/checks.py`, `pipeline/src/routine_watch/explain.py` (offline/fake path). Iterate every pattern and the offline explanation for each scenario alert you can build cheaply (use `demo.py` data).
Acceptance:
- case-insensitive banned list: `diagnos`, `has delirium`, `has dementia`, `suffers from`, `prescribe`, `dose`; test fails with the offending string
- offline only; `scripts/ci.sh` passes

### T335 — Test: dashboard source has no diagnosis wording
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/wording.test.ts
- owner: —
- claimed: —
- pr: —

What: Same rule as T334 for the dashboard: a vitest that reads every non-test `.ts`/`.tsx` under `web/src/` and fails on banned user-facing wording.
Interface: use `import.meta.glob('./**/*.{ts,tsx}', { query: '?raw', eager: true })` (or node `fs`), skip `*.test.*` and `contracts.ts`.
Acceptance:
- banned (case-insensitive): `diagnos`, `suffers from`, `has delirium`, `has dementia`; failure message names file + line
- passes on current main (if not, list hits in PR body and leave the fix to a follow-up bug task)
- `scripts/ci.sh` passes
