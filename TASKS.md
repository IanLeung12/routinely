# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: 325c252

## Tasks

### T350 — Review: wire HandoffDelta into the shift handoff rows
- status: done
- class: light
- priority: 1
- kind: improvement
- source: reviewer
- deps: —
- area: web/src/handoff/Handoff.tsx, web/src/handoff/Handoff.test.tsx
- rating: 5/5 clear - interface named the component, the props and the exact line to append to; only unstated call was that 'same as last shift' renders as 'Nothing flagged either shift' when both counts are 0
- owner: ian-claude
- claimed: 2026-10-17T17:15Z
- pr: #335

What: T324 (#324) added `previous_flags` to `/handoff` and a `HandoffDelta` component, but nothing renders it: `Handoff.tsx` never imports `HandoffDelta`, so the "better or worse than last shift" signal is dead code on the demo screen.
Interface: in `Handoff.tsx`, render `<HandoffDelta flags={resident.flags} previousFlags={resident.previous_flags} />` in each resident row (next to the flags reason), and append the same delta text to the copy/read-aloud line built around line 147 ("…, 2 more than last shift"). No new styles; reuse `HandoffDelta.css`.
Acceptance:
- `Handoff.test.tsx` asserts a row with flags 2 / previous_flags 0 shows "2 more than last shift" and a row with equal counts shows "same as last shift"
- `scripts/ci.sh` passes

### T351 — Review: time-of-day strip and evening pattern use different "evening" cut-offs
- status: blocked
- class: light
- priority: 2
- kind: bug
- source: reviewer
- deps: —
- area: pipeline/src/routine_watch/api_alerts.py, pipeline/tests/test_time_of_day.py
- rating: —
- owner: Max_codex_light
- claimed: 2026-10-17T17:45Z
- note: Fix committed as c881255 on task/T351-evening-cutoff in Max_codex_light_T351 worktree. Targeted tests: 21 passed; full Python CI: 1193 passed, 1 skipped. Two scripts/ci.sh attempts fail in unrelated web App.test.tsx with undici WebSocket ERR_INVALID_ARG_TYPE (Event instance mismatch), despite 540 web tests passing. No listener on local port 8000 when checked. Not pushed because local CI must pass. Follow-up: TimeOfDay contracts docstring still says until 17:00; heavy-only.

What: `pattern_features.EVENING_HOUR = 16` decides the evening-only pattern, but `api_alerts.EVENING_START_HOUR = 17` buckets the strip shown as its evidence. A session at 16:xx counts as "evening" for the pattern and "afternoon" on the strip, so an alert "consistent with evening worsening" can show its errors under afternoon. The code comment admits it only holds because no demo session starts 16:00–17:00.
Interface: in `api_alerts.py`, set `EVENING_START_HOUR = pattern_features.EVENING_HOUR` (import it, drop the hard-coded 17) and update the comment. The `TimeOfDay` docstring in `contracts.py`/schemas says "until 17:00": contracts are heavy-only, so don't touch them; note the stale docstring in the PR for a follow-up.
Acceptance:
- new test in `test_time_of_day.py`: a session at 16:30 buckets as `evening`, matching `pattern_features`' late-day rule
- `scripts/ci.sh` passes

### T349 — worker.sh: always disallow Monitor/ScheduleWakeup for claude and re-read MODELS.md flags
- status: done
- class: light
- priority: 1
- kind: improvement
- source: retro
- deps: —
- area: scripts/worker.sh
- owner: Max_codex_light
- claimed: 2026-10-17T17:12Z
- pr: #333
- note: Hosted CI passed. Local bash syntax and dry checks passed; shellcheck unavailable. Local full CI passed all tests but Vitest reported shared localhost:8000 WebSocket Event error.
- rating: 5/5 clear

What: E4's `--disallowedTools Monitor ScheduleWakeup` (MODELS.md, PR #271) never reached any running worker: worker.sh reads FLAGS once at start, and the host launcher passes a `FLAGS=` override for the heavy worker (`--model opus --effort max`) that drops it. Since then 2 light-worker sessions (T187, T307) still ended with "I'll wait for the CI monitor notification" and were released.
Interface: in `scripts/worker.sh`, (1) inside the loop, before each claude/codex run, recompute flags from MODELS.md unless the caller set FLAGS (keep `FLAGS` env as the override); (2) for `TOOL=claude`, always append `--disallowedTools Monitor ScheduleWakeup` if the effective flags don't already contain `--disallowedTools`. Keep `MODEL=` in the prompt in sync.
Acceptance:
- `bash -n scripts/worker.sh` and shellcheck (if installed) pass
- a dry check (e.g. `FLAGS='--model opus' TOOL=claude` with the claude call echoed, not run) shows `--disallowedTools Monitor ScheduleWakeup` in the command line; no change to codex flags
- `scripts/ci.sh` passes

### T198 — Docs: DEMO.md mentions opening an alert from the shift handoff
- status: claimed
- class: light
- priority: 3
- kind: docs
- deps: —
- area: docs/DEMO.md
- owner: Max_codex_light
- claimed: 2026-10-17T18:12Z
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

### T344 — Scenario: tea_session_unclear_no_flag (whole session too unclear to score)
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/tea_session_unclear_no_flag/
- owner: ian-claude-standard-2
- claimed: 2026-10-17T17:05Z
- pr: #330
- rating: 5/5 clear

What: #322 added an optional `quality:` assertion to `expected.yaml`, but no scenario uses it. Add one where most tea steps come through low-confidence/unclear (bad lighting), with history that would otherwise flag, so replay must report `quality: unclear`, `score: 0.0`, `flag: false`.
Interface: copy `tests/scenarios/tea_unclear_not_error/` as the template (read its README comment and `tests/scenarios/README.md`); see `Expected` and `score_session` in `pipeline/src/routine_watch/replay.py` and `pipeline/src/routine_watch/quality.py` for the rule (>40% unclear or <3 events).
Acceptance:
- `expected.yaml` sets `quality: unclear`, `flag: false`, `score: 0.0`, and a header comment says why
- `scripts/e2e.sh` passes with the new scenario counted; `scripts/ci.sh` passes

### T345 — Resident detail: session list usable at phone width (375 px)
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/SessionList.tsx, web/src/resident/sessionList.css, web/src/resident/SessionList.mobile.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T17:36Z
- pr: #341
- rating: 5/5 clear

What: Make the resident's session list readable on a phone, the same way the drift card was done. Read `web/src/resident/SessionList.tsx`, `web/src/resident/DriftCard.mobile.test.tsx` (test template) and `web/src/resident/driftCard.css` (the `@media (max-width: 480px)` pattern). Put new styles in a new `sessionList.css` imported by `SessionList.tsx`; don't edit `resident.css`.
Interface: CSS + class names only; no behaviour change.
Acceptance:
- at ≤480 px rows stack (date/time above score/errors), no horizontal scroll, text wraps
- new `SessionList.mobile.test.tsx` checks the stylesheet has the 480 px media rule and the list still renders every session
- `cd web && npx vitest run src/resident` and `scripts/ci.sh` pass

### T346 — Test: alert time-of-day strip has accessible names
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/alert/TimeOfDayStrip.a11y.test.tsx, web/src/alert/TimeOfDayStrip.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T17:52Z
- pr: #347
- note: earlier attempt lost to a shared-checkout reset; its work is on branch wip/Max_codex_light-1017-1745 (commit b09a18e). Start from origin/main, cherry-pick b09a18e if useful, run scripts/ci.sh, open the PR. Use your own worktree.
- rating: 5/5 clear

What: Each morning/afternoon/evening cell in the alert's time-of-day strip should be readable by a screen reader ("Evening: 3 errors"). Read `web/src/alert/TimeOfDayStrip.tsx` and `web/src/alert/TimeOfDayStrip.test.tsx`. Add the test; only if a cell has no accessible name, add an `aria-label` in `TimeOfDayStrip.tsx` (no visual change).
Interface: new test file; at most `aria-label`/`role` attributes in the component.
Acceptance:
- every cell has an accessible name with its part of day and count (`getByRole(..., { name })` / `toHaveAccessibleName`), including zero-count cells
- `cd web && npx vitest run src/alert` and `scripts/ci.sh` pass

### T347 — Unit overview: show how many residents each filter holds
- status: todo
- class: standard
- priority: 3
- kind: feature
- source: proposed
- deps: —
- area: web/src/overview/UnitOverview.tsx, web/src/overview/overview.css, web/src/overview/UnitOverview.counts.test.tsx
- owner: —
- claimed: —
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
- status: claimed
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/evidence/
- owner: ian-claude-standard
- claimed: 2026-10-17T17:43Z
- pr: —

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
- status: claimed
- class: standard
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/meds_late_start_normal/, pipeline/tests/test_scenarios_meds_late_start.py
- owner: ian-claude-standard-2
- claimed: 2026-10-17T18:12Z
- pr: —

What: Medication twin of T362: a resident idles a long time before picking up the pill bottle, then completes the routine correctly; must produce zero errors and no flag.
Interface: copy the layout of `tests/scenarios/meds_normal/` (`steps.jsonl`, `expected.yaml`) and the test style of `pipeline/tests/test_scenarios_meds_unclear.py` (`load_scenario`, `replay`). Pipeline code is out of scope: if it fails, set the task blocked with the failing output.
Acceptance:
- new pytest passes; `scripts/e2e.sh` runs the scenario: zero errors, `flag: false`.
- one line added to `tests/scenarios/README.md`.
- `scripts/ci.sh` passes.

### T365 — Test: live session summary has accessible names
- status: claimed
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/live/SessionSummary.a11y.test.tsx, web/src/live/SessionSummary.tsx
- owner: Max_codex_light
- claimed: 2026-10-17T18:05Z
- pr: —

What: The end-of-session summary on the live screen must be readable by a screen reader: a heading, and each figure (duration, errors, quality) with a text label, not only an icon or colour.
Interface: read `web/src/live/SessionSummary.tsx` and `web/src/live/SessionSummary.test.tsx`. Add `SessionSummary.a11y.test.tsx` using `getByRole('heading')` and `getByText`/`getByLabelText`. Only if a figure has no accessible name, add an `aria-label` in `SessionSummary.tsx` (no visual change).
Acceptance:
- new test passes; `cd web && npx vitest run src/live/SessionSummary` green.
- `scripts/ci.sh` passes.

### T366 — Test: unit overview error and empty states use the shared ui components
- status: claimed
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/overview/UnitOverview.states.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T18:08Z
- pr: —

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
