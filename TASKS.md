# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: 1e4fdef

## Tasks

### T351 — Review: time-of-day strip and evening pattern use different "evening" cut-offs
- status: todo
- class: light
- priority: 2
- kind: bug
- source: reviewer
- deps: T368
- area: pipeline/src/routine_watch/api_alerts.py, pipeline/tests/test_time_of_day.py
- rating: —
- owner: —
- claimed: —
- note: orch: local ci.sh failed only on the known undici WebSocket flake (fixed by T368, now a dep). A fix exists unpushed as c881255 on task/T351-evening-cutoff in Max's worktree; reuse it if available, else redo (tiny). Leave the contracts TimeOfDay docstring alone.

What: `pattern_features.EVENING_HOUR = 16` decides the evening-only pattern, but `api_alerts.EVENING_START_HOUR = 17` buckets the strip shown as its evidence. A session at 16:xx counts as "evening" for the pattern and "afternoon" on the strip, so an alert "consistent with evening worsening" can show its errors under afternoon. The code comment admits it only holds because no demo session starts 16:00–17:00.
Interface: in `api_alerts.py`, set `EVENING_START_HOUR = pattern_features.EVENING_HOUR` (import it, drop the hard-coded 17) and update the comment. The `TimeOfDay` docstring in `contracts.py`/schemas says "until 17:00": contracts are heavy-only, so don't touch them; note the stale docstring in the PR for a follow-up.
Acceptance:
- new test in `test_time_of_day.py`: a session at 16:30 buckets as `evening`, matching `pattern_features`' late-day rule
- `scripts/ci.sh` passes

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
- pr: #353
- rating: 4/5 acceptance asked for the .no-print rule inside handoff.css, but T353 already moved it to the shared print.css; the area also left out vite.config.ts's test.css.include, which a ?raw CSS assertion needs
- note: merge conflict with main on PR #353: check out its branch, merge origin/main, fix, push

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

### T343 — Live: session_end says when a session was too unclear to score
- status: todo
- class: heavy
- priority: 1
- kind: feature
- deps: T342
- area: pipeline/src/routine_watch/contracts.py, contracts/live_message.schema.json, pipeline/src/routine_watch/live.py, pipeline/src/routine_watch/live_camera.py, web/src/contracts.ts, web/src/live/SessionSummary.tsx, web/src/live/SessionSummary.test.tsx, web/src/live/mockLiveStream.ts, pipeline/tests/test_live_quality.py
- owner: —
- claimed: —
- pr: —

What: SPEC §12 says low-confidence capture (walker, bad lighting) is "unclear", never an error. Today the nurse just sees score 0 with no explanation. Add `quality: "ok" | "unclear"` to `LiveSessionEnd`, send it from both `live.py` and `live_camera.py` (`session_quality(events)`), and have `SessionSummary` show "Capture unclear — this session wasn't scored" with one line on why (lighting, view blocked, walker) instead of the score.
Interface: `LiveSessionEnd.quality: Quality` (required; regenerate `contracts/live_message.schema.json` the way the repo does it and update web types + mock stream in the same PR).
Acceptance:
- pipeline test: unclear session → `session_end.quality == "unclear"`, clean → `"ok"`, for both `live` and `live_camera` paths; schema validates
- web test: SessionSummary renders the unclear copy and no score for `quality: "unclear"`; unchanged for `"ok"`; no diagnosis wording
- `scripts/ci.sh` passes

### T347 — Unit overview: show how many residents each filter holds
- status: claimed
- class: standard
- priority: 3
- kind: feature
- source: proposed
- deps: —
- area: web/src/overview/UnitOverview.tsx, web/src/overview/overview.css, web/src/overview/UnitOverview.counts.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T18:30Z
- pr: —

What: Rationale: a charge nurse should see "Flagged (1) · Watch (4) · Paused (0)" at a glance before clicking. Add the count to each filter button label in the unit overview, computed from the loaded residents and paused rooms the component already holds.
Interface: `UnitOverview.tsx` only (+ css). Accessible name stays clear, e.g. "Flagged, 1 resident".
Acceptance:
- counts match the residents each filter would show (incl. Paused) and update after a reset/refresh
- existing overview tests (`UnitOverview*.test.tsx`) still pass unchanged or with label-matcher updates only
- `cd web && npx vitest run src/overview` and `scripts/ci.sh` pass

### T348 — Docs: CODEMAP note that unclear sessions are never scored
- status: todo
- class: light
- priority: 3
- kind: docs
- deps: —
- area: docs/CODEMAP.md
- owner: —
- claimed: —
- pr: —

What: Add a 2–3 line note to the pipeline section of `docs/CODEMAP.md` (notes only; the file list is generated): `quality.session_quality` gates `replay.score_session`; an unclear session (fewer than 3 events or >40% unclear/low-confidence) gets score 0.0 and never flags, like an assisted one. Read `pipeline/src/routine_watch/quality.py` and `score_session` in `pipeline/src/routine_watch/replay.py`.
Interface: docs only.
Acceptance:
- note sits next to the existing scoring/replay notes; `scripts/ci.sh` passes

### T352 — Test: web mockPatterns stays in step with the pipeline pattern library
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_mock_patterns_match_web.py
- owner: ian-claude-standard
- claimed: 2026-10-17T17:20Z
- pr: #334
- rating: 5/5 clear

What: `web/src/patterns/mockPatterns.ts` says it mirrors `routine_watch.patterns_library.LIBRARY` (offline fallback, SPEC §13), but nothing checks it, so the offline pattern library can silently drift from the real one.
Interface: new `pipeline/tests/test_mock_patterns_match_web.py`, modelled on `pipeline/tests/test_error_phrases_match_web.py` (regex-parse the TS file; no node). Read only those two files plus `pipeline/src/routine_watch/patterns_library.py`.
Acceptance:
- Asserts the set of `pattern_id`s in mockPatterns.ts equals LIBRARY's, and per pattern the `urgency` and `checks` list match.
- If the mock has already drifted, do not edit web/; mark the failing case `xfail` with the reason and list the drift in the PR body.
- `cd pipeline && uv run pytest tests/test_mock_patterns_match_web.py` and `scripts/ci.sh` pass.

### T356 — Live camera on the dashboard: one command, laptop webcam → /ws/live
- status: todo
- class: heavy
- priority: 0
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/api_live.py, pipeline/src/routine_watch/live_camera.py, pipeline/src/routine_watch/capture.py, scripts/camera.sh, pipeline/tests/test_api_live_camera.py, docs/DEMO.md
- owner: —
- claimed: —
- pr: —
- note: released by ian-claude: run ended without progress

What: Ian wants to try the real camera locally. `capture.py --camera 0` already writes JSONL and `live_camera.camera_session_messages()` already turns a frame stream into live messages, but `/ws/live` only plays recorded scenarios. Wire them together so the dashboard's Live screen shows his webcam session.
Interface:
- `/ws/live?source=camera[&camera=0]` streams `camera_session_messages()` from a capture iterator running in a background thread (same pause handling as scenarios). Default stays the recorded scenario.
- `scripts/camera.sh`: on a laptop, `uv sync --extra capture`, download the two MediaPipe task bundles into `models/` if missing (URLs in `capture._MODEL_URLS`), start the stack (`dev.sh up`), and print the dashboard URL with the Live screen pointed at the camera (a `?source=camera` toggle or query param in `web/src/live/` if needed). Optional `--record out.jsonl` also saves the capture stream (never video).
- Without detector weights (`DETECTOR_WEIGHTS`), skeleton and hands still stream live and steps show as "waiting for object detector"; say so on screen instead of looking broken.
- macOS: note camera permission for the terminal in `docs/DEMO.md`; Windows/Linux index 0 default.
Acceptance:
- Test with a fake capture iterator: `/ws/live?source=camera` yields session_start, frames, steps, session_end like a scenario.
- `scripts/ci.sh` passes without mediapipe/opencv installed (lazy imports).
- `docs/DEMO.md` has a "Live camera on your laptop" section with the exact commands.

### T353 — Improvement: one shared print stylesheet for alert view and resident detail
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/print.css, web/src/main.tsx, web/src/alert/alert.css, web/src/resident/residentPrint.css, web/src/resident/ResidentDetail.tsx, web/src/print.test.ts
- owner: ian-claude-standard-2
- claimed: 2026-10-17T17:22Z
- pr: #338
- rating: 5/5 clear

What: `web/src/alert/alert.css` (T289) and `web/src/resident/residentPrint.css` (T333) carry the same `@media print` block (`.no-print`, black-on-white `html, body, body *`). Move the shared rules into one `web/src/print.css` imported once from `main.tsx`; keep only screen-specific print rules (e.g. hiding the app header while a resident is open) in each component's CSS, and delete `residentPrint.css` if nothing specific remains.
Interface: `web/src/print.css` with `.no-print` utility + black-on-white rules; no TSX behaviour change beyond the import.
Acceptance:
- `grep -c '@media print' web/src/alert/alert.css web/src/resident/*.css` shows the shared rules exist only in `web/src/print.css`
- existing `AlertView.test.tsx` and `ResidentDetail.print.test.tsx` still pass unchanged; add `web/src/print.test.ts` that asserts `print.css` defines `.no-print`
- `scripts/ci.sh` passes

### T354 — Scenario: meds_session_unclear_no_flag (whole medication session too unclear to score)
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/meds_session_unclear_no_flag/, pipeline/tests/test_scenarios_meds_unclear.py
- owner: ian-claude-standard
- claimed: 2026-10-17T17:29Z
- pr: #339
- rating: 5/5 clear

What: The medication task's twin of T344 (PR #330): a medication session whose capture is low-confidence throughout must be classed unclear by `routine_watch.quality.session_quality`, score 0.0, raise no errors and never flag, even after a prior bad session. Generate frames the way `tests/scenarios/meds_unclear_not_error/` and the synth scripts do; read `tests/scenarios/README.md` for the format.
Interface: `tests/scenarios/meds_session_unclear_no_flag/{frames.jsonl,expected.yaml}`; consumed by `scripts/e2e.sh`.
Acceptance:
- `scripts/e2e.sh` runs the new scenario green; `expected.yaml` asserts no errors, no flag, quality unclear
- pytest asserts `session_quality(events) == "unclear"` for it
- `scripts/ci.sh` passes

### T355 — Shift handoff: say when a room's capture was too unclear to score this shift
- status: todo
- class: heavy
- priority: 2
- kind: feature
- source: proposed
- deps: T343
- area: pipeline/src/routine_watch/contracts.py, contracts/, pipeline/src/routine_watch/live.py, pipeline/src/routine_watch/handoff.py, pipeline/src/routine_watch/store.py, pipeline/tests/test_handoff_unclear.py, web/src/contracts.ts, web/src/handoff/HandoffRow.tsx, web/src/handoff/mockHandoff.ts
- owner: —
- claimed: —
- pr: —

What: Rationale: since T342 unclear sessions are dropped from history, so repeated bad lighting or a blocked camera goes unnoticed; the incoming nurse should see "2 sessions too unclear to score — check the camera view" for that room. Keep a per-room count of unclear sessions (timestamps only, never frames, never in the resident's scored history) and surface it as `HandoffResident.unclear_sessions: int` for the window.
Interface: `HandoffResident.unclear_sessions: int` (default 0; regenerate schema and web types the repo's way, update every consumer and mock in the same PR); the handoff row shows the line only when > 0. Wording is about the capture, never the resident.
Acceptance:
- pytest: two unclear live sessions in the window → `unclear_sessions == 2`, resident's history and flag unchanged; outside the window → 0
- web test: row shows the camera line when > 0 and nothing when 0
- `scripts/ci.sh` passes

### T357 — Scenario: meds_long_pause_not_error (long pause under the abandonment cut-off)
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/meds_long_pause_not_error/
- owner: ian-claude-standard-2
- claimed: 2026-10-17T17:39Z
- pr: #344
- rating: 5/5 clear

What: The medication task's version of `tests/scenarios/tea_long_pause_not_error`: an otherwise-correct meds session with one ~100 s gap between two steps (under `routine_watch.errors.ABANDON_AFTER_S`), which must not surface as an error or flag.
Interface: `tests/scenarios/meds_long_pause_not_error/{steps.jsonl,expected.yaml}`, step-level like `meds_normal`; copy the comment style of `tea_long_pause_not_error/expected.yaml`. No pipeline code changes.
Acceptance:
- `expected.yaml`: `task: meds`, full correct step list, `errors: []`, `score: 0.0`, `flag: false`
- `scripts/e2e.sh` passes with the new scenario counted; `scripts/ci.sh` passes

### T358 — Evidence replay player: usable at phone width (375 px)
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/evidence/
- owner: ian-claude-standard
- claimed: 2026-10-17T17:43Z
- pr: #350
- rating: 5/5 clear

What: A nurse opening an alert on a phone should be able to watch the skeleton replay and use its controls without horizontal scrolling. Follow the 375 px pattern other screens already use (see `web/src/alert/alert.css`, `web/src/live/liveScreen.css`).
Interface: `ReplayPlayer.tsx` / `GhostReplay.tsx` keep their props; styles go in the existing stylesheet for `.replay-player` (or a new `web/src/evidence/evidence.css` imported by `ReplayPlayer.tsx`). No behaviour change.
Acceptance:
- at 375 px the replay canvas scales to the container width and the play/scrub controls wrap onto their own row, touch targets ≥ 44 px
- a vitest checks the stylesheet has a `max-width: 375px`-or-narrower media rule for `.replay-player` (same approach as existing phone-width tests)
- `scripts/ci.sh` passes

### T359 — Test: guided tour copy uses flag-for-review wording
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/tour/steps.test.ts
- owner: ian-claude-light-2
- claimed: 2026-10-17T17:45Z
- pr: #343
- rating: 5/5 clear

What: Guard the demo tour text against diagnosis wording, since judges read it first.
Interface: read only `web/src/tour/steps.ts` (exports `TOUR_STEPS: {title, body}[]`) and `web/src/wording.test.ts` (existing wording-guard style to copy). Create `web/src/tour/steps.test.ts`.
Acceptance:
- for every step, `title` and `body` do not match `/diagnos|\bhas (delirium|dementia|a stroke)\b|treatment/i`
- at least one step body contains "flags a change for review"; every step has a non-empty title and body
- `cd web && npx vitest run src/tour/steps.test.ts` passes; `scripts/ci.sh` passes

### T360 — Guided tour: usable at phone width (375 px)
- status: claimed
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/tour/
- owner: max_API_light
- claimed: 2026-10-17T18:04Z
- pr: —

What: The `?tour=1` guided tour card must fit a 375 px phone without horizontal scroll or clipped buttons, like the other phone-width tasks (T234, T238).
Interface: read `web/src/tour/Tour.tsx` and `web/src/tour/Tour.test.tsx`; add `web/src/tour/tour.css` (if styles are inline, move only the layout ones) with an `@media (max-width: 480px)` block: card max-width `calc(100vw - 2rem)`, buttons wrap. Add `tour` to `css.include` only if you need `?raw` (that file is web/vite.config.ts — note it in the PR instead of editing it; read the CSS with `fs.readFileSync` in the test).
Acceptance:
- New test asserts the phone media query exists and sets the card's max-width and button wrapping.
- No behaviour change; existing tour tests still pass.
- `scripts/ci.sh` passes.

### T361 — Test: overview sparklines have a text alternative
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/overview/Sparkline.a11y.test.tsx, web/src/overview/Sparkline.tsx
- owner: max_API_light
- claimed: 2026-10-17T17:47Z
- pr: #346

What: Screen-reader users must get the trend a sparkline shows. Test that each sparkline exposes an accessible name describing the trend (e.g. "Error rate over last 14 sessions, rising"); if it doesn't, add `role="img"` + `aria-label` in `Sparkline.tsx`.
Interface: read `web/src/overview/Sparkline.tsx` and `web/src/overview/Sparkline.test.tsx` first; new test file uses `getByRole('img', { name: /.../ })`.
Acceptance:
- Test covers rising, flat and empty-data sparklines.
- Wording never says "diagnose" or names a condition.
- `scripts/ci.sh` passes.

### T362 — Scenario: tea_late_start_normal (long idle before the first step is not an error)
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/tea_late_start_normal/
- owner: ian-claude-standard-2
- claimed: 2026-10-17T17:59Z
- pr: #348
- rating: 5/5 clear

What: A resident who sits for a long time before touching the kettle and then makes tea correctly must not get an error or a flag. Guards against the abandonment timer starting before the first step.
Interface: copy the layout of `tests/scenarios/tea_long_pause_not_error/` (`steps.jsonl`, `expected.yaml`); generate frames with the same generator/script that scenario's README or `tests/scenarios/README.md` names. Pipeline code is out of scope: if the scenario fails, file it in the PR and set the task blocked with the failing output.
Acceptance:
- `scripts/e2e.sh` runs the new scenario and it passes: zero errors, no flag.
- `scripts/ci.sh` passes.

### T363 — Test: task map legend has accessible names for every step state
- status: todo
- class: light
- priority: 3
- kind: test
- deps: —
- area: web/src/live/TaskMapLegend.a11y.test.tsx
- owner: —
- claimed: —
- pr: —

What: Each legend entry (done, current, missed, error…) must be readable without colour, by text or accessible name.
Interface: read `web/src/live/TaskMapLegend.tsx` and `web/src/live/TaskMapLegend.test.tsx`; new test file only. If an entry relies on colour alone, set the task blocked with a note naming the entry (don't change the component).
Acceptance:
- One assertion per legend state, by role/name or visible text.
- `scripts/ci.sh` passes.

### T364 — Scenario: meds_late_start_normal (long idle before the first step is not an error)
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/meds_late_start_normal/, pipeline/tests/test_scenarios_meds_late_start.py
- owner: ian-claude-standard-2
- claimed: 2026-10-17T18:12Z
- pr: #351
- rating: 5/5 clear

What: Medication twin of T362: a resident idles a long time before picking up the pill bottle, then completes the routine correctly; must produce zero errors and no flag.
Interface: copy the layout of `tests/scenarios/meds_normal/` (`steps.jsonl`, `expected.yaml`) and the test style of `pipeline/tests/test_scenarios_meds_unclear.py` (`load_scenario`, `replay`). Pipeline code is out of scope: if it fails, set the task blocked with the failing output.
Acceptance:
- new pytest passes; `scripts/e2e.sh` runs the scenario: zero errors, `flag: false`.
- one line added to `tests/scenarios/README.md`.
- `scripts/ci.sh` passes.

### T365 — Test: live session summary has accessible names
- status: in-review
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/live/SessionSummary.a11y.test.tsx, web/src/live/SessionSummary.tsx
- owner: Max_codex_light
- claimed: 2026-10-17T18:05Z
- pr: #355
- rating: 4/5 clear except quality is not rendered by this component

What: The end-of-session summary on the live screen must be readable by a screen reader: a heading, and each figure (duration, errors, quality) with a text label, not only an icon or colour.
Interface: read `web/src/live/SessionSummary.tsx` and `web/src/live/SessionSummary.test.tsx`. Add `SessionSummary.a11y.test.tsx` using `getByRole('heading')` and `getByText`/`getByLabelText`. Only if a figure has no accessible name, add an `aria-label` in `SessionSummary.tsx` (no visual change).
Acceptance:
- new test passes; `cd web && npx vitest run src/live/SessionSummary` green.
- `scripts/ci.sh` passes.

### T366 — Test: unit overview error and empty states use the shared ui components
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/overview/UnitOverview.states.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T18:08Z
- pr: #349
- rating: 3/5 task assumed ErrorState is wired into UnitOverview but it isn't; fetchResidents swallows errors and falls back to mock data

What: Guard the overview's failure paths: when the residents API rejects, the screen shows the shared ErrorState with a retry button; when it returns no residents, it shows the shared EmptyState with nurse-readable copy.
Interface: read `web/src/overview/UnitOverview.tsx`, `web/src/overview/api.ts`, `web/src/ui/ErrorState.tsx`, `web/src/ui/EmptyState.tsx` and the mocking style in `web/src/overview/UnitOverview.test.tsx`. Test only; if a state is missing, note it in the PR instead of changing the component.
Acceptance:
- `cd web && npx vitest run src/overview/UnitOverview.states` green.
- `scripts/ci.sh` passes.

### T367 — Bug: integration check failing on main
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
- note: tester saw this once on a cold start (TESTREPORT: likely Vite cold-start/dep-optimise timing; re-run passed). If it is timing, make scripts/integration.sh wait for Vite readiness (fixing the check is fine here); otherwise fix the render.

What: `scripts/integration.sh` (stack up offline → API endpoints → dashboard render → live WebSocket) fails on main @ c332a28:
  FAIL dashboard did not render (no 'Routine Watch' in DOM)
Interface: reproduce with `scripts/integration.sh`; logs in `.dev/api.log` / `.dev/web.log`. Fix the cause (not the check) unless the check itself is wrong.
Acceptance:
- `scripts/integration.sh` prints OK; `scripts/ci.sh` passes.

### T368 — Test infra: every web test gets a fake WebSocket by default
- status: claimed
- class: light
- priority: 1
- kind: improvement
- deps: —
- area: web/vite.config.ts, web/src/testSetup.ts, web/src/App.test.tsx
- owner: Max_codex_light
- claimed: 2026-10-17T18:37Z
- pr: #354
- rating: 5/5 clear
- note: merge conflict with main on PR #354: check out its branch, merge origin/main, fix, push

What: Local `scripts/ci.sh` keeps failing with an undici `ERR_INVALID_ARG_TYPE` WebSocket error (blocked T351, LESSONS lines 28 and 42) because some web tests render screens that open a real socket to localhost:8000. Stub it once for the whole suite.
Interface: new `web/src/testSetup.ts` that, in a global `beforeEach`, does `vi.stubGlobal('WebSocket', FakeWebSocket)` using the existing helper in `web/src/live/testWebSocket.ts` (read it first), and registers it as `test.setupFiles: ['src/testSetup.ts']` in `web/vite.config.ts`. Tests that already stub WebSocket keep working (their own stub wins). Drop the now-redundant stub in `App.test.tsx` only if it stays green.
Acceptance:
- with a local `uvicorn` listening on :8000 (or not), `cd web && npx vitest run` exits 0 with no uncaught exception
- `scripts/ci.sh` passes

### T369 — Privacy panel: usable at phone width (375 px)
- status: claimed
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/about/PrivacyPanel.tsx, web/src/about/privacyPanel.css, web/src/about/PrivacyPanel.mobile.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T18:30Z
- pr: —

What: Make the privacy panel readable at 375 px (no horizontal scroll, controls stack, text wraps), like the other phone-width tasks.
Interface: read `web/src/about/PrivacyPanel.tsx` and the pattern in `web/src/resident/DriftCard.mobile.test.tsx` + `web/src/resident/driftCard.css`. Add a `@media (max-width: 480px)` block in a new `privacyPanel.css` imported by the panel; keep existing class names.
Acceptance:
- new `PrivacyPanel.mobile.test.tsx` renders at 375 px and checks the stacked class names exist
- `scripts/ci.sh` passes

### T370 — Alert time-of-day strip: usable at phone width (375 px)
- status: todo
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/alert/TimeOfDayStrip.css, web/src/alert/TimeOfDayStrip.mobile.test.tsx
- owner: —
- claimed: —
- pr: —

What: The morning/afternoon/evening strip on the alert view must fit 375 px: the three buckets stay readable (stack or shrink), labels never truncate.
Interface: read `web/src/alert/TimeOfDayStrip.tsx` and `TimeOfDayStrip.css`; follow `web/src/resident/DriftCard.mobile.test.tsx`. CSS-only change plus the test; don't change the component's props.
Acceptance:
- new `TimeOfDayStrip.mobile.test.tsx` renders at 375 px and finds all three bucket labels
- `scripts/ci.sh` passes

### T371 — Test: error list and suggested checks have accessible names
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/alert/ErrorList.a11y.test.tsx, web/src/alert/SuggestedChecks.a11y.test.tsx
- owner: —
- claimed: —
- pr: —

What: Screen-reader check for the two alert evidence lists: each is a labelled list/region and every item's name includes its time and step (errors) or check text (suggested checks).
Interface: read `web/src/alert/ErrorList.tsx`, `SuggestedChecks.tsx` and the style of `web/src/alert/TimeOfDayStrip.a11y.test.tsx`. Tests only; if a name is missing, note it in the PR instead of changing the component.
Acceptance:
- two new test files using `getByRole(..., { name })` queries
- `scripts/ci.sh` passes

### T372 — Test: every error type and pattern is covered by a recorded scenario
- status: todo
- class: standard
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_scenario_coverage.py
- owner: —
- claimed: —
- pr: —
- note: released by ian-claude-standard: run ended without progress; partial work on branch task/T372-wip-1833: start from it (git switch task/T372-wip-1833 && git merge origin/main)

What: Guard against scenario rot: a pipeline test that loads every `tests/scenarios/*/expected.yaml` and asserts each `ErrorType` (contracts.py) appears in at least one scenario's `errors`, each task (tea, meds) has a `*_normal` and an `*_abandoned` scenario, and each pattern in the pattern library has a `pattern_*` scenario (or is listed in an explicit, commented allow-list).
Interface: read-only use of `routine_watch.contracts.ErrorType`, the pattern library module, and the scenario folder; no new scenarios.
Acceptance:
- `pytest pipeline/tests/test_scenario_coverage.py` passes; removing a scenario's error makes it fail with a message naming the missing type
- `scripts/ci.sh` passes

### T373 — Docs: CODEMAP note that web tests share one default WebSocket stub
- status: todo
- class: light
- priority: 3
- kind: docs
- deps: T368
- area: docs/CODEMAP.md
- owner: —
- claimed: —
- pr: —

What: One-line note in the web section of `docs/CODEMAP.md` (notes only, not the generated list) that `web/src/testSetup.ts` stubs WebSocket for every test and tests needing a socket use `web/src/live/testWebSocket.ts`.
Acceptance:
- note added; `scripts/ci.sh` passes

### T374 — Test infra: load every web stylesheet in Vitest so tasks stop editing vite.config.ts
- status: todo
- class: light
- priority: 1
- kind: improvement
- deps: T368
- area: web/vite.config.ts
- owner: —
- claimed: —
- pr: —

What: every phone-width / print task appends a folder to `test.css.include` in `web/vite.config.ts`, so sibling PRs conflict on that one line (T203's PR #353 is conflicting now; LESSONS.md line 19). Replace the per-folder list with one pattern that matches all `src/**/*.css`.
Interface: read `web/vite.config.ts` only. Set `css: { include: [/src\/.*\.css/] }` (or equivalent) and shorten the comment to say why: `?raw` CSS assertions need it and no task should have to edit this line again.
Acceptance:
- `cd web && npm test` passes with no other file changed (if a test becomes slower or breaks because its CSS is now loaded, say so in the PR rather than widening scope)
- `scripts/ci.sh` passes

### T375 — Unit overview: say when it is showing demo data because the API is unreachable
- status: todo
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/overview/api.ts, web/src/overview/UnitOverview.tsx, web/src/overview/UnitOverview.states.test.tsx, web/src/overview/overview.css
- owner: —
- claimed: —
- pr: —

What: `fetchResidents()` silently falls back to `mockResidents` when `/residents` fails (T366 rating), so a nurse or judge can't tell live data from demo data. Keep the fallback (demo robustness) but surface it as a one-line notice above the list.
Interface: `fetchResidents()` returns `{ residents: ResidentSummary[], source: 'api' | 'demo' }` via a new `fetchResidentsWithSource()` (keep `fetchResidents()` returning the array so `web/src/App.tsx` is untouched). UnitOverview renders `<p role="status" class="overview__demo-notice">Showing demo residents: the Routine Watch service isn't reachable.</p>` when `source === 'demo'`, nothing otherwise.
Acceptance:
- tests in `UnitOverview.states.test.tsx`: API rejects → notice shown and mock residents listed; API non-OK → notice shown; API OK → no notice
- `cd web && npm test` and `scripts/ci.sh` pass
