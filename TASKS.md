# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: d657310

## Tasks

### T340 — Resident detail: give monitoring controls their own row under the name
- status: claimed
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/ResidentDetail.tsx, web/src/resident/resident.css, web/src/resident/ResidentDetail.layout.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T16:56Z
- pr: —

What: Tester (TESTREPORT, main dc9a6ef) noted Mrs. K's header packs the monitoring switch, monitoring history and consent between the name and the status chip, so it reads cramped. Keep name, room and status chip on the first row; move the monitoring block (toggle, history, consent, error message) to a separate row below.
Interface: wrap name/room/StatusChip in `.resident-detail__title-row`; `.resident-detail__monitoring` becomes a full-width row after it. No behaviour change.
Acceptance:
- New test `ResidentDetail.layout.test.tsx`: in the header, the status chip appears in DOM order before the monitoring toggle, and both still render; existing ResidentDetail and keyboard tests pass unchanged.
- At 375 px nothing overflows horizontally (CSS uses wrap, no fixed widths).
- `scripts/ci.sh` passes.

### T341 — Test: pattern library urgency filter works keyboard-only
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/patterns/PatternLibrary.keyboard.test.tsx
- owner: —
- claimed: —
- pr: —

What: Add a keyboard-only test for the pattern library, like `web/src/overview/UnitOverview.keyboard.test.tsx` (read it first as the template). Read `web/src/patterns/PatternLibrary.tsx` and `web/src/patterns/PatternLibrary.filters.test.tsx` for how it is rendered with mock data.
Interface: new file only; uses @testing-library/user-event `tab()` and `keyboard('{Enter}')` / `keyboard(' ')`.
Acceptance:
- Tabbing reaches the back button and every urgency filter button (role group "Filter by urgency").
- Pressing Enter or Space on a filter sets its `aria-pressed="true"` and narrows the list; the back button fires `onBack` on Enter.
- `cd web && npx vitest run src/patterns` and `scripts/ci.sh` pass.

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

### T322 — Drift card: usable at phone width (375 px)
- status: done
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
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/live/sessionSummary.css, web/src/live/liveSession.css
- owner: max_API_light
- claimed: 2026-10-17T16:23Z
- pr: #317

What: `liveScreen.css` and `taskMap.css` already have phone-width rules, but the session summary and live session panels don't; at 375 px they must not scroll sideways and buttons are at least 44 px tall.
Interface: read `web/src/live/SessionSummary.tsx`, `web/src/live/LiveSession.tsx`, the two CSS files, and `web/src/live/liveScreen.css` (copy its `@media (max-width: 480px)` approach). CSS only; no behaviour change.
Acceptance:
- a `@media (max-width: 480px)` block in each of the two CSS files; no fixed widths over 375 px
- existing live tests still pass; `cd web && npm test` and `scripts/ci.sh` pass

### T324 — Shift handoff: "compared with the previous shift" per resident
- status: in-review
- class: heavy
- priority: 3
- kind: feature
- source: proposed
- deps: —
- area: pipeline/src/routine_watch/handoff.py, pipeline/tests/test_handoff_previous.py, pipeline/src/routine_watch/contracts.py, contracts/handoff.schema.json, contracts/examples/, web/src/handoff/HandoffDelta.tsx, web/src/handoff/HandoffDelta.test.tsx, web/src/handoff/types.ts, web/src/contracts.ts
- owner: ian-claude
- claimed: 2026-10-17T16:46Z
- pr: #324
- rating: 5/5 clear

What: Rationale: a nurse coming on shift wants to know if things are getting better or worse, not just counts. Add each resident's `flags` for the previous window of the same length (`previous_flags`) to `/handoff`, and a small "up / down / same vs previous shift" indicator component.
Interface: `build_handoff(now, hours)` adds `previous_flags: int` per resident (window `[now-2h, now-h)`); update `handoff.schema.json`, contracts.py and generated web types; new `HandoffDelta({flags, previousFlags})` component renders e.g. "2 more than last shift" / "same as last shift" with an accessible text (not colour only). Wiring it into `Handoff.tsx` is a follow-up task (keeps this off the files T203/T247 own). Wording: describes counts only, never a diagnosis.
Acceptance:
- pytest covers previous window bounds (session exactly at `now-h` counts in the current window only) and the demo data
- schema + example validate; smoke/contract tests pass
- `HandoffDelta.test.tsx` covers more/fewer/same/zero
- `scripts/ci.sh` passes

### T325 — Test: monitoring toggle works keyboard-only
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/about/MonitoringToggle.keyboard.test.tsx
- owner: Max_codex_light
- claimed: 2026-10-17T16:23Z
- pr: #315
- rating: 5/5 clear

What: The privacy monitoring switch is a key trust control; prove a nurse can pause and resume it with the keyboard alone.
Interface: read `web/src/about/MonitoringToggle.tsx`, `web/src/about/MonitoringToggle.test.tsx` and `web/src/about/PrivacyPanel.keyboard.test.tsx` (copy its user-event keyboard style). New test file only; no component changes (if a bug is found, mark the case `it.fails` and note it in the PR).
Acceptance:
- Tab reaches the switch; Space and Enter each call `onChange` with the flipped value; `aria-checked` matches `on`
- when paused, the "No camera data is processed while paused." text is shown
- `cd web && npm test` and `scripts/ci.sh` pass

### T326 — Test: unit tests for session_log
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_session_log.py
- owner: ian-claude-light-2
- claimed: 2026-10-17T16:30Z
- pr: #316
- rating: 5/5 clear

What: `pipeline/src/routine_watch/session_log.py` (the in-process log that makes a live session count for the demo) has no direct unit test.
Interface: read `pipeline/src/routine_watch/session_log.py`, `pipeline/tests/conftest.py`, and how `pipeline/tests/test_api_demo_reset.py` builds a Session/TaskError. New test file only; use a fixture that calls `session_log.reset()` before and after each test.
Acceptance:
- covers: record then sessions_for (oldest first), errors_for by session id, unknown resident/session gives an empty list, two residents stay separate, reset() clears everything
- `cd pipeline && python -m pytest tests/test_session_log.py` and `scripts/ci.sh` pass

### T327 — Test: unit tests for pattern_features.extract_features
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_pattern_features.py
- owner: ian-claude-standard-2
- claimed: 2026-10-17T16:26Z
- pr: #314
- rating: 5/5 clear

What: `pipeline/src/routine_watch/pattern_features.py` (378 lines; turns sessions + care records into the features the pattern library ranks on) is only tested indirectly through alerts; direct tests make a regression point at the right file.
Interface: read `pattern_features.py`, `patterns_library.py`, and the `pattern_*` scenarios under `tests/scenarios/` for realistic inputs. New test file only; no source changes (bugs found: `pytest.mark.xfail(strict=True)` + PR note).
Acceptance:
- covers at least: flat history (no drift); slow downward trend; sudden change; evening-only worsening; a sedating care record inside its window appears in the context and an old one doesn't; empty sessions don't crash
- deterministic (fixed `now`, no wall clock)
- `cd pipeline && python -m pytest tests/test_pattern_features.py` and `scripts/ci.sh` pass

### T328 — Test: /ws/live WebSocket routes in api_live.py
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_api_live_ws.py
- owner: Max_codex_light
- claimed: 2026-10-17T16:41Z
- pr: #321
- note: GitHub CI passed; local CI hit known App.test.tsx undici WebSocket environment error despite all tests passing.
- rating: 5/5 clear

What: `api_live.py` has no direct test file. Add WebSocket tests with FastAPI `TestClient` for the live route.
Interface: read `pipeline/src/routine_watch/api_live.py`, `pipeline/src/routine_watch/api_state.py`, `pipeline/src/routine_watch/monitoring.py` and one existing API test in `pipeline/tests/` for the client fixture. Call `api_state.reset()` before each test.
Acceptance:
- covers: a normal run sends at least one message then a session-end message; a paused room gets the "paused" message and no step events; an unknown scenario/room gets a clear error or close (whatever the code does today, asserted)
- offline only, no LIVE_API calls
- `scripts/ci.sh` passes

### T329 — Test: resident routes return 404 for an unknown resident
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_api_residents_404.py
- owner: ian-claude-light-2
- claimed: 2026-10-17T16:42Z
- pr: #323
- rating: 5/5 clear

What: Every `/residents/{id}/...` route in `api_residents.py` should answer an unknown id with 404, not 500 or an empty 200.
Interface: read `pipeline/src/routine_watch/api_residents.py` and `pipeline/src/routine_watch/api.py` (router wiring). Parametrise over every GET route under `/residents/{id}` found in `api_residents.py`.
Acceptance:
- one parametrised pytest; each route with id `nobody` returns 404 with a JSON `detail`
- if a route returns something else, don't change product code: mark that case `xfail(strict=True)` with reason and mention it in the PR body
- `scripts/ci.sh` passes

### T330 — Heat calendar: usable at phone width (375 px)
- status: claimed
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/heatCalendar.css
- owner: max_API_light
- claimed: 2026-10-17T16:43Z
- pr: —

What: Same series as T234/T239: at 375 px the heat calendar must fit without horizontal page scroll and keep readable cells.
Interface: read `web/src/resident/heatCalendar.css`, `web/src/resident/HeatCalendar.tsx`, and the `@media` block in `web/src/overview/overview.css` for the breakpoint convention. CSS only.
Acceptance:
- `@media (max-width: 480px)` rules: cells shrink or the grid scrolls inside its own card (not the page); labels stay ≥ 12 px
- dark theme tokens still used (no hard-coded colours)
- PR body has a 375 px screenshot from `scripts/dev.sh up` (or states why not)
- `scripts/ci.sh` passes

### T331 — Test: heat calendar cells have accessible names
- status: claimed
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/resident/HeatCalendar.a11y.test.tsx
- owner: Max_codex_light
- claimed: 2026-10-17T16:56Z
- pr: —

What: Colour alone must not carry meaning. Assert each heat calendar cell exposes its date and error count to screen readers.
Interface: read `web/src/resident/HeatCalendar.tsx` and `web/src/resident/HeatCalendar.test.tsx` (fixture). Use Testing Library `getAllByRole`/`getByLabelText`.
Acceptance:
- every rendered day cell has an accessible name containing the date and the count (e.g. "17 Oct: 2 errors"); zero-error days say "no errors"
- if the component lacks this today, mark the test `it.fails` and say so in the PR body (no product change in this task)
- `scripts/ci.sh` passes

### T332 — Replay and ghost replay respect prefers-reduced-motion
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/evidence/ReplayPlayer.tsx, web/src/evidence/GhostReplay.tsx, web/src/evidence/reducedMotion.ts, web/src/evidence/reducedMotion.test.ts, web/src/evidence/ReplayPlayer.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T16:36Z
- pr: #318
- rating: 4/5 task assumed GhostReplay autoplays on its own but it is a static render driven by AlertView's fixed t prop; nothing to gate there

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
- status: claimed
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_wording_guard.py
- owner: ian-claude-light-2
- claimed: 2026-10-17T16:58Z
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

### T336 — Review: unclear sessions are scored and can flag (quality.py never wired)
- status: done
- class: standard
- priority: 1
- kind: bug
- source: reviewer
- deps: —
- area: pipeline/src/routine_watch/replay.py, pipeline/src/routine_watch/live.py, pipeline/src/routine_watch/live_camera.py, pipeline/tests/test_replay.py
- owner: ian-claude-standard
- claimed: 2026-10-17T16:35Z
- pr: #322
- rating: 5/5 clear, precise diff; the one gap was that wiring quality broke two pre-existing test_live_camera.py tests outside the listed area (zero-event fixtures became unclear by session_quality's own pinned min_events rule), which needed a surgical fix not mentioned in the task

What: `quality.session_quality` (SPEC §7/§12: low-confidence sessions are "unclear", never errors) is imported nowhere in `pipeline/src`. `replay.score_session` scores and flags every session regardless, so a session with mostly unclear/low-confidence events (bad lighting, walker) can push a resident to a flag. Fix: in `replay.score_session`, compute `session_quality(events)`; when `"unclear"`, return score 0.0 and flag False (same treatment as assisted). Add `"quality": "ok"|"unclear"` to the dict `replay_scenario` returns. `live.py` (~line 290) and `live_camera.py` (~line 150) call `score_session`, so they inherit the fix; pass events through if the signature changes, nothing else there.
Interface: `score_session(scenario, errors, events)` -> unchanged `(score, assisted, flag)` tuple; update the three call sites.
Acceptance:
- new test: a scenario built in-test with >40% `unclear` or sub-threshold events gets `flag: False`, `score: 0.0`, `quality: "unclear"`
- every existing scenario in `tests/scenarios/` still matches its expected.yaml (replay tests / `scripts/e2e.sh` pass)
- `scripts/ci.sh` passes

### T337 — Unit overview: remember filter and sort for the session
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/overview/UnitOverview.tsx, web/src/overview/overviewPrefs.ts, web/src/overview/overviewPrefs.test.ts, web/src/overview/UnitOverview.prefs.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T16:45Z
- pr: #320
- rating: 5/5 clear

What: A nurse who picks "Flagged" or "Most recent change first", opens a resident and comes back loses the choice. Store filter + sort mode in `sessionStorage` so they survive navigation and reload within the tab.
Interface: `overviewPrefs.ts` exports `loadOverviewPrefs(): { filter: UnitFilter; sort: SortMode }` and `saveOverviewPrefs(prefs)`; key `rw.overview.prefs`; unknown/corrupt stored values fall back to `{ filter: 'all', sort: 'default' }`. `UnitOverview.tsx` initialises its state from it and saves on change (move the `UnitFilter` type into `overviewPrefs.ts` or `types.ts` if needed).
Acceptance:
- unit tests: round trip, corrupt JSON, unknown values → defaults, sessionStorage throwing → defaults
- component test: choose Flagged + recent sort, unmount, remount → both still selected (`aria-pressed`)
- `cd web && npm test` and `scripts/ci.sh` pass

### T338 — Test: unit overview sort combined with filters
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/overview/ResidentSort.filter.test.tsx
- owner: —
- claimed: —
- pr: —

What: T318 added "Most recent change first" but tests cover sort alone. Add a test that sort and filter compose correctly.
Interface: read `web/src/overview/UnitOverview.tsx`, `web/src/overview/ResidentSort.tsx`, `web/src/overview/ResidentSort.test.tsx` (copy its fetch mocking). New file only.
Acceptance:
- with 4 residents (mixed status, different latest `scores[].ts`): Watch filter + recent sort shows only watch residents, newest first; switching back to Default order restores flagged→watch→normal order; All filter + recent sort shows all four newest first
- a resident with empty `scores` sorts last under recent
- `cd web && npx vitest run src/overview/ResidentSort.filter.test.tsx` passes

### T339 — Test: /residents returns each resident's scores oldest-first
- status: claimed
- class: standard
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_api_residents_order.py
- owner: ian-claude-standard-2
- claimed: 2026-10-17T16:54Z
- pr: —

What: The dashboard's "Most recent change first" sort (T318, `web/src/overview/ResidentSort.tsx`) assumes `scores` is oldest-first with ISO `ts`. Pin that contract on the API side so a backend change can't silently break the sort.
Interface: read `pipeline/src/routine_watch/api_residents.py`, `api_state.py`, and an existing API test (e.g. `pipeline/tests/test_feedback_reset.py`) for the client fixture. New test file only.
Acceptance:
- after demo reset, every resident in `GET /residents` has `scores` sorted ascending by `ts`, every `ts` parses as ISO 8601
- after a live session completes (use the existing fake/replay path, no real APIs), that resident's newest score is last
- `cd pipeline && uv run pytest tests/test_api_residents_order.py` passes
