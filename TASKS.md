# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: 4008ae3

## Tasks

### T350 — Review: wire HandoffDelta into the shift handoff rows
- status: in-review
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
- status: todo
- class: light
- priority: 2
- kind: bug
- source: reviewer
- deps: —
- area: pipeline/src/routine_watch/api_alerts.py, pipeline/tests/test_time_of_day.py
- rating: —

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

### T340 — Resident detail: give monitoring controls their own row under the name
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/ResidentDetail.tsx, web/src/resident/resident.css, web/src/resident/ResidentDetail.layout.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T16:56Z
- pr: #326
- rating: 5/5 clear

What: Tester (TESTREPORT, main dc9a6ef) noted Mrs. K's header packs the monitoring switch, monitoring history and consent between the name and the status chip, so it reads cramped. Keep name, room and status chip on the first row; move the monitoring block (toggle, history, consent, error message) to a separate row below.
Interface: wrap name/room/StatusChip in `.resident-detail__title-row`; `.resident-detail__monitoring` becomes a full-width row after it. No behaviour change.
Acceptance:
- New test `ResidentDetail.layout.test.tsx`: in the header, the status chip appears in DOM order before the monitoring toggle, and both still render; existing ResidentDetail and keyboard tests pass unchanged.
- At 375 px nothing overflows horizontally (CSS uses wrap, no fixed widths).
- `scripts/ci.sh` passes.

### T341 — Test: pattern library urgency filter works keyboard-only
- status: claimed
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/patterns/PatternLibrary.keyboard.test.tsx
- owner: max_API_light
- claimed: 2026-10-17T17:31Z
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

### T330 — Heat calendar: usable at phone width (375 px)
- status: in-review
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/heatCalendar.css
- owner: ian-claude-light-2
- claimed: 2026-10-17T17:26Z
- pr: #337
- note: re-queued by orch: previous attempt blocked only by local Windows env (rolldown EPERM / port clash, see LESSONS), not the fix; branch was never pushed, so redo the small CSS change from origin/main
- rating: 4/5 clear, but acceptance criteria conflicted (0.6875rem shrink from a prior attempt violated the >=12px rule)

What: Same series as T234/T239: at 375 px the heat calendar must fit without horizontal page scroll and keep readable cells.
Interface: read `web/src/resident/heatCalendar.css`, `web/src/resident/HeatCalendar.tsx`, and the `@media` block in `web/src/overview/overview.css` for the breakpoint convention. CSS only.
Acceptance:
- `@media (max-width: 480px)` rules: cells shrink or the grid scrolls inside its own card (not the page); labels stay ≥ 12 px
- dark theme tokens still used (no hard-coded colours)
- PR body has a 375 px screenshot from `scripts/dev.sh up` (or states why not)
- `scripts/ci.sh` passes

### T334 — Test: pattern checks and summaries never use diagnosis wording
- status: in-review
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_wording_guard.py
- owner: max_API_light
- claimed: 2026-10-17T17:16Z
- pr: #336
- note: released by ian-claude-light-2: run ended without progress; partial work on branch task/T334-wip-1701: start from it (git switch task/T334-wip-1701 && git merge origin/main)

What: Guard SPEC's wording rule in code: every pattern name, description, rule-out check and generated summary says "consistent with"/"check", never "diagnos", "has <condition>", or treatment advice.
Interface: read `pipeline/src/routine_watch/patterns_library.py`, `pipeline/src/routine_watch/checks.py`, `pipeline/src/routine_watch/explain.py` (offline/fake path). Iterate every pattern and the offline explanation for each scenario alert you can build cheaply (use `demo.py` data).
Acceptance:
- case-insensitive banned list: `diagnos`, `has delirium`, `has dementia`, `suffers from`, `prescribe`, `dose`; test fails with the offending string
- offline only; `scripts/ci.sh` passes

### T335 — Test: dashboard source has no diagnosis wording
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/wording.test.ts
- owner: ian-claude-light-2
- claimed: 2026-10-17T17:16Z
- pr: #331
- rating: 4/5 clear, but test file already existed with partial check

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
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/overview/ResidentSort.filter.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T17:21Z
- pr: #332
- rating: 5/5 clear

What: T318 added "Most recent change first" but tests cover sort alone. Add a test that sort and filter compose correctly.
Interface: read `web/src/overview/UnitOverview.tsx`, `web/src/overview/ResidentSort.tsx`, `web/src/overview/ResidentSort.test.tsx` (copy its fetch mocking). New file only.
Acceptance:
- with 4 residents (mixed status, different latest `scores[].ts`): Watch filter + recent sort shows only watch residents, newest first; switching back to Default order restores flagged→watch→normal order; All filter + recent sort shows all four newest first
- a resident with empty `scores` sorts last under recent
- `cd web && npx vitest run src/overview/ResidentSort.filter.test.tsx` passes

### T339 — Test: /residents returns each resident's scores oldest-first
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_api_residents_order.py
- owner: ian-claude-standard-2
- claimed: 2026-10-17T16:54Z
- pr: #325
- rating: 5/5 clear

What: The dashboard's "Most recent change first" sort (T318, `web/src/overview/ResidentSort.tsx`) assumes `scores` is oldest-first with ISO `ts`. Pin that contract on the API side so a backend change can't silently break the sort.
Interface: read `pipeline/src/routine_watch/api_residents.py`, `api_state.py`, and an existing API test (e.g. `pipeline/tests/test_feedback_reset.py`) for the client fixture. New test file only.
Acceptance:
- after demo reset, every resident in `GET /residents` has `scores` sorted ascending by `ts`, every `ts` parses as ISO 8601
- after a live session completes (use the existing fake/replay path, no real APIs), that resident's newest score is last
- `cd pipeline && uv run pytest tests/test_api_residents_order.py` passes

### T342 — Review: unclear live sessions still go into the resident's history and can flag
- status: done
- class: standard
- priority: 1
- kind: bug
- source: orchestrator (review of #322)
- deps: —
- area: pipeline/src/routine_watch/live.py, pipeline/tests/test_live_unclear.py
- owner: ian-claude
- claimed: 2026-10-17T17:02Z
- pr: #328
- rating: 4/5 clear diagnosis and fix; the acceptance criterion's 'fake WebSocket helper from pipeline/tests/ used by test_api_live_ws.py' does not exist - that file uses fastapi's TestClient.websocket_connect, and an in-test scenario needs api_live.scenario_path monkeypatched to be reachable by ?scenario= at all

What: PR #322 made `replay.score_session` return score 0.0 / flag False for an unclear session (`quality.session_quality`), but `live.session_messages` (~line 290) still calls `_record(...)` with that session's errors and `assisted=False`. `demo.py` recomputes scores from recorded errors and only skips assisted sessions, so an unclear session's errors still count toward the 24–48 h flag and a 0.0 score enters the baseline. Fix: when `session_quality(events) == "unclear"`, don't record the session into `session_log` at all (nothing to trust), and keep `was_flagged`/alert logic unchanged.
Interface: `live.py` only; `from .quality import session_quality`. No contract change (T343 adds the `quality` field to `session_end`).
Acceptance:
- new test: a live session whose events are mostly `unclear` (build in-test, reuse the fake WebSocket helper from `pipeline/tests/` used by `test_api_live_ws.py`) leaves `session_log` for that resident unchanged and the resident's flag state unchanged; a clean session is still recorded
- `cd pipeline && uv run pytest tests/test_live_unclear.py tests/test_live*.py` and `scripts/ci.sh` pass

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
- status: todo
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/SessionList.tsx, web/src/resident/sessionList.css, web/src/resident/SessionList.mobile.test.tsx
- owner: —
- claimed: —
- pr: —

What: Make the resident's session list readable on a phone, the same way the drift card was done. Read `web/src/resident/SessionList.tsx`, `web/src/resident/DriftCard.mobile.test.tsx` (test template) and `web/src/resident/driftCard.css` (the `@media (max-width: 480px)` pattern). Put new styles in a new `sessionList.css` imported by `SessionList.tsx`; don't edit `resident.css`.
Interface: CSS + class names only; no behaviour change.
Acceptance:
- at ≤480 px rows stack (date/time above score/errors), no horizontal scroll, text wraps
- new `SessionList.mobile.test.tsx` checks the stylesheet has the 480 px media rule and the list still renders every session
- `cd web && npx vitest run src/resident` and `scripts/ci.sh` pass

### T346 — Test: alert time-of-day strip has accessible names
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/alert/TimeOfDayStrip.a11y.test.tsx, web/src/alert/TimeOfDayStrip.tsx
- owner: —
- claimed: —
- pr: —

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
- status: claimed
- class: heavy
- priority: 0
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/api_live.py, pipeline/src/routine_watch/live_camera.py, pipeline/src/routine_watch/capture.py, scripts/camera.sh, pipeline/tests/test_api_live_camera.py, docs/DEMO.md
- owner: ian-claude
- claimed: 2026-10-17T17:34Z
- pr: —

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
- status: in-review
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
- status: claimed
- class: standard
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/meds_session_unclear_no_flag/, pipeline/tests/test_scenarios_meds_unclear.py
- owner: ian-claude-standard
- claimed: 2026-10-17T17:29Z
- pr: —

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
