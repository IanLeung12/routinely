# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: 88693bd

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

### T246 — Unit overview: "Monitoring paused" chip on residents whose room is paused
- status: done
- class: light
- priority: 2
- kind: feature
- deps: T242
- area: web/src/overview/UnitOverview.tsx, web/src/overview/UnitOverview.test.tsx, web/src/overview/overview.css
- owner: ian-claude-light-2
- claimed: 2026-10-17T12:59Z
- pr: #257
- rating: 5/5 clear

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
- status: in-review
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_live_flag_consistency.py
- owner: ian-claude-standard
- claimed: 2026-10-17T13:05Z
- pr: #258
- rating: 4/5 clear, though the 'area' example file in the task wasn't new behavior to add but a new guard test to write across all scenarios (not just the few named ones) - also required a small fix to explain.py for a real bug it surfaced (abandonment errors with step_id=None)

What: Guard T236 across all recordings: after a live replay of each scenario in `tests/scenarios/`, `session_end.flag` must equal that resident's flagged state from `/residents`, and `alert_id` must be `None` or an id that `/alerts/{id}` returns 200 for.
Interface: read `pipeline/tests/test_live.py` (how it drives `session_messages` / `/ws/live` with the FastAPI `TestClient`) and `pipeline/tests/test_api_demo_reset.py` (calling `/demo/reset` between cases). New file only; parametrize over scenario dirs; reset state between cases.
Acceptance:
- one parametrized test per scenario; fakes only, no real API calls
- `cd pipeline && python -m pytest tests/test_live_flag_consistency.py` and `scripts/ci.sh` pass

### T253 — Shift handoff screen: show the rooms whose monitoring is paused
- status: claimed
- class: light
- priority: 2
- kind: feature
- deps: T251
- area: web/src/handoff/types.ts, web/src/handoff/mockHandoff.ts, web/src/handoff/Handoff.tsx, web/src/handoff/Handoff.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T13:06Z
- pr: —

What: Show T251's new `paused` list on the handoff screen so the incoming nurse sees which rooms weren't watched.
Interface: Read `web/src/handoff/types.ts`, `Handoff.tsx`, `mockHandoff.ts` and T251's docstring in `pipeline/src/routine_watch/handoff.py`. Add `paused: { room: string; resident_id: string; name: string }[]` to the `Handoff` type (treat missing as `[]` for older APIs) and `monitoring_paused?: boolean` to `HandoffResident`. When non-empty, render one line above the rows: "Monitoring paused: <name> (room <room>), ..." and a "Monitoring paused" chip on those residents' rows. Include the line in `handoffText`. Mock gets `paused: []`.
Acceptance:
- Tests: no line when `paused` is empty or missing; line + chip when one room is paused; `handoffText` includes it.
- `scripts/ci.sh` passes.

### T255 — Resident detail: show who consented to monitoring
- status: todo
- class: light
- priority: 2
- kind: feature
- source: proposed
- deps: T254
- area: web/src/overview/types.ts, web/src/mock/residents.ts, web/src/mock/residentDetail.ts, web/src/resident/ResidentDetail.tsx, web/src/resident/ResidentDetail.test.tsx, web/src/resident/resident.css
- owner: —
- claimed: —
- pr: —
- note: released by ian-claude-light-2: run ended without progress; partial work on branch task/T255-wip-1310: start from it (git switch task/T255-wip-1310 && git merge origin/main)

What: Show T254's consent record under the monitoring switch: "Consent: Substitute decision-maker (daughter), 2026-09-28". Small grey text, nothing when the field is missing (older API / mock without it).
Interface: Read `web/src/overview/types.ts` (resident type), `web/src/resident/ResidentDetail.tsx` (header with `MonitoringToggle`), and `pipeline/src/routine_watch/demo.py` (T254's `consent: {given_by, on}`). Add optional `consent?: { given_by: string; on: string }` to the resident type; give the three mock residents in `web/src/mock/residents.ts` a consent record.
Acceptance:
- Tests in `ResidentDetail.test.tsx`: consent line renders with given_by and date; no line when `consent` is absent.
- `scripts/ci.sh` passes.

### T258 — Test: pause flow end to end in the API (pause → handoff → live → reset)
- status: done
- class: standard
- priority: 2
- kind: test
- deps: T251
- area: pipeline/tests/test_pause_flow.py
- owner: ian-claude-standard
- claimed: 2026-10-17T12:16Z
- pr: #242
- rating: 5/5 clear

What: Pausing a room now touches four places (monitoring store, `/handoff`, `/ws/live`, `/demo/reset`) built in separate PRs. One test walks the whole flow so a regression in any shows up.
Interface: FastAPI `TestClient` only, fakes only. Steps: `PUT /rooms/204/monitoring {"on": false}` → `GET /monitoring` lists 204 → `GET /handoff` lists Mrs. K's room as paused (T251 field) → `/ws/live` first message is `{"type":"paused","room":"204"}` → `POST /demo/reset` → `/monitoring` empty and `/ws/live` sends `session_start`. Read `pipeline/tests/test_api_monitoring.py` and `conftest.py` for fixtures.
Acceptance:
- New test file passes; no source changes; `scripts/ci.sh` passes.

### T259 — Shift handoff summary sentence mentions paused rooms
- status: done
- class: standard
- priority: 2
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/handoff.py, pipeline/tests/test_handoff.py
- owner: ian-claude-standard-2
- claimed: 2026-10-17T12:20Z
- pr: #243
- rating: 5/5 clear

What: Since #238 the handoff payload lists paused rooms, but the plain-language `summary` still reads "all quiet" for a window where a room wasn't watched. Pass the paused rooms to the explainer as context so the summary says e.g. "Room 204 (Mrs. K) was paused, so no flags are expected from it."
Interface: `_summary(rows, flagged_sessions, hours)` gains the `paused` list (or derives it from `rows[*].monitoring_paused`) and adds one context line per paused room to the `Explainer.summarise` call; the fake explainer's output must include the paused room. No contract or API change.
Acceptance:
- Test: with room 204 paused, `build_handoff(DEMO_NOW)["summary"]` mentions room 204; with nothing paused the summary is unchanged from today (existing tests still pass).
- Wording follows SPEC §7.5 (no "diagnose"); fakes only, no real API calls.
- `scripts/ci.sh` passes.

### T260 — Test: first-load JS bundle size budget for the dashboard
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: web/scripts/check-bundle.mjs, web/package.json, web/README.md
- owner: ian-claude-standard-2
- claimed: 2026-10-17T12:45Z
- pr: #251
- note: released by ian-claude-standard: run ended without progress; partial work on branch task/T260-wip-1234: start from it (git switch task/T260-wip-1234 && git merge origin/main)
- rating: 4/5 clear, but the acceptance check (eager-import Handoff fails the budget) doesn't hold once the existing lazy-split screens are already small relative to a 10% margin on today's size -- documented in the PR

What: #237 lazy-loaded the handoff, pattern library and tour screens to shrink first paint. Lock that in: a small Node script that, after `vite build`, sums the gzipped size of the JS the entry `index.html` loads (not lazy chunks) and fails above a budget set ~10% over today's size.
Interface: `web/scripts/check-bundle.mjs` (Node built-ins only: `fs`, `zlib`, `path`), `npm run check:bundle` in `web/package.json` that runs it against `web/dist/`. Print the measured size and the budget. Document the budget and how to raise it in `web/README.md`. Don't edit `scripts/ci.sh` (note in the PR if it should be wired in).
Acceptance:
- `cd web && npm run build && npm run check:bundle` passes on main and prints sizes; temporarily importing `Handoff` eagerly in `App.tsx` makes it fail (describe this check in the PR, don't commit it).
- `scripts/ci.sh` passes.

### T261 — Review: tests can hit paid APIs if LIVE_API=1 is exported in the shell
- status: done
- class: light
- priority: 1
- kind: bug
- source: reviewer
- deps: —
- area: scripts/ci.sh, pipeline/tests/conftest.py
- owner: ian-claude-light-2
- claimed: 2026-10-17T12:25Z
- pr: #244
- rating: 5/5 clear

What: `scripts/ci.sh` and pytest never force `LIVE_API` off (only e2e.sh/integration.sh do), and `.env.example` documents `LIVE_API`. An agent or teammate with `LIVE_API=1` exported who runs `scripts/ci.sh` makes real Claude/Gemini calls from unit tests (AGENTS.md: tests never make real calls).
Interface: in `scripts/ci.sh` add `export LIVE_API=0` right after the `cd` line. In `pipeline/tests/conftest.py` add an autouse fixture doing `monkeypatch.setenv("LIVE_API", "0")` so plain `pytest` is safe too; a test that checks the live path can still override it with its own monkeypatch.
Acceptance:
- `LIVE_API=1 bash scripts/ci.sh` passes and makes no network calls.
- `scripts/ci.sh` passes.

### T262 — Monitoring audit trail: who paused/resumed a room and when
- status: done
- class: heavy
- priority: 2
- kind: feature
- source: proposed
- deps: T256
- area: pipeline/src/routine_watch/monitoring.py, pipeline/src/routine_watch/api_live.py, pipeline/tests/test_monitoring_audit.py, web/src/resident/, web/src/about/monitoringApi.ts
- owner: ian-claude
- claimed: 2026-10-17T12:38Z
- pr: #253
- rating: 5/5 clear

What: Rationale: SPEC §12 privacy accountability; judges see that pausing a camera is logged. Record each pause/resume (room, on/off, by, at) in memory and show the last 5 on resident detail under the monitoring switch.
Interface: `MonitoringState.history(room) -> list[dict(on: bool, by: str, at: iso str)]`; PUT /rooms/{room}/monitoring accepts optional `by` (default "nurse"); GET /rooms/{room}/monitoring/history returns the list (newest first, max 20); `/demo/reset` clears it. Web: small "Recent changes" list under the switch, empty state "No changes this shift". Use the real file names after T256's refactor (adjust area paths in the PR if they differ).
Acceptance:
- pytest test covers pause → resume → history order and reset clearing it.
- web test renders the list and the empty state.
- `scripts/ci.sh` passes.

### T263 — Contracts: JSON Schema for GET /alerts/{id} and the feedback POST body
- status: claimed
- class: heavy
- priority: 2
- kind: improvement
- deps: T257
- area: contracts/, pipeline/src/routine_watch/contracts.py, pipeline/tests/test_contracts.py, web/src/contracts.ts
- owner: ian-claude
- claimed: 2026-10-17T12:59Z
- pr: —

What: Same pattern as T250/T257: the alert detail response and the feedback request are hand-mirrored in web/src/contracts.ts; generate schemas from pydantic so drift fails CI.
Interface: `contracts/alert_detail.schema.json`, `contracts/feedback.schema.json` generated from contracts.py; a test validates real API responses (fakes only) against them and checks web/src/contracts.ts field names match.
Acceptance:
- schemas generated, README in contracts/ updated.
- test fails if a field is added on one side only.
- `scripts/ci.sh` passes.

### T264 — Test: consent record survives /demo/reset and shows in /handoff residents
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_demo_consent.py
- owner: ian-claude-standard-2
- claimed: 2026-10-17T12:27Z
- pr: #245
- rating: 5/5 clear

What: T254 added per-resident consent; nothing checks it survives `/demo/reset` or that every resident in GET /residents (not just mrs-k) carries it.
Interface: extend pipeline/tests/test_demo_consent.py using the FastAPI TestClient with fakes.
Acceptance:
- every resident from GET /residents has consent.given_by and consent.on, before and after POST /demo/reset.
- `scripts/ci.sh` passes.

### T265 — Refactor: move alert routes out of api.py into api_alerts.py
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: pipeline/src/routine_watch/api.py, pipeline/src/routine_watch/api_alerts.py (new), docs/CODEMAP.md
- owner: ian-claude-standard-2
- claimed: 2026-10-17T12:34Z
- pr: #248
- rating: 5/5 clear

What: Same pattern as T256 (api_live.py): move `GET /alerts`, `GET /alerts/{id}`, `POST /alerts/{id}/feedback` and their helpers (`AlertFeedbackIn`, `_alerts_by_id`, `_alert_payload`) into an `APIRouter` in `api_alerts.py` that `api.py` includes. No behaviour change.
Interface: `routine_watch.api_alerts.router`; names tests import from `routine_watch.api` keep working (re-export), so tests need no edits.
Acceptance:
- api.py shrinks by the moved code; all existing pipeline tests pass unchanged.
- docs/CODEMAP.md api.py note updated and an api_alerts.py note added.
- `scripts/ci.sh` passes.

### T266 — Live screen: "Check again" after a room is unpaused
- status: done
- class: standard
- priority: 2
- kind: feature
- deps: —
- area: web/src/live/useLiveSession.ts, web/src/live/useLiveSession.test.ts, web/src/live/LiveScreen.tsx, web/src/live/LiveScreen.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T12:49Z
- pr: #252
- rating: 3/5 area was stale (LiveScreen.tsx has no paused UI; it lives in LiveSession.tsx, which the listed area didn't include)

What: Once /ws/live sends `{"type":"paused"}` the hook stops for good, so after a nurse resumes the room the live screen stays on "Monitoring is paused" until a full reload. Add a "Check again" button on the paused state that reconnects.
Interface: `useLiveSession` returns `retry(): void` that clears `paused`, resets state and opens a new socket; LiveScreen's paused panel renders a button calling it.
Acceptance:
- test: paused message → button shown → click → a new WebSocket is opened and, if it streams steps, the paused panel disappears.
- test: still paused on retry → panel stays, no mock-data fallback.
- `scripts/ci.sh` passes.

### T267 — Web: visible keyboard focus and a skip-to-content link
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/index.css, web/src/App.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T12:57Z
- pr: #256
- rating: 5/5 clear

What: Accessibility pass for keyboard users (Clarity/Execution). Add a global `:focus-visible` outline in the design-system accent colour (min 2 px, 3:1 contrast) and a "Skip to main content" link as the first focusable element in App, targeting `<main id="main">`.
Interface: `.skip-link` class in index.css (visually hidden until focused); `<main id="main">` in App.tsx.
Acceptance:
- `cd web && npx vitest run src/App.test.tsx` still passes; PR describes a manual Tab check.
- no layout change for mouse users.
- `scripts/ci.sh` passes.

### T268 — Test: GET /handoff window bounds
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_handoff_window.py (new)
- owner: —
- claimed: —
- pr: —

What: `GET /handoff?hours=` is declared `Query(ge=1, le=168)` in pipeline/src/routine_watch/api.py (read `shift_handoff`), but nothing tests the bounds.
Interface: new pytest file using `fastapi.testclient.TestClient(routine_watch.api.app)`; read pipeline/tests/test_handoff.py for fixtures and fakes.
Acceptance:
- hours=1 and hours=168 → 200 with `window_hours` echoed; hours=0 and hours=169 → 422.
- the summary never contains "diagnos".
- `scripts/ci.sh` passes.

### T269 — Contracts: JSON Schema for GET/PUT /monitoring payloads
- status: todo
- class: heavy
- priority: 2
- kind: improvement
- deps: T263, T262
- area: contracts/, pipeline/src/routine_watch/contracts.py, pipeline/tests/test_contracts.py, web/src/contracts.ts
- owner: —
- claimed: —
- pr: —

What: Same pattern as T257/T263: the monitoring state (incl. T262's audit trail) is hand-mirrored in web/src/contracts.ts; generate a schema from pydantic so drift fails CI.
Interface: `contracts/monitoring.schema.json` generated from contracts.py; a test validates real GET /monitoring and PUT responses (fakes only) against it and checks web/src/contracts.ts field names match.
Acceptance:
- schema generated, contracts/README.md updated.
- test fails if a field is added on one side only.
- `scripts/ci.sh` passes.

### T270 — Bug: integration check failing on main
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
- note: closed by orchestrator: tester confirms integration.sh passes @1d6ee98 (fixed by T231)

What: `scripts/integration.sh` (stack up offline → API endpoints → dashboard render → live WebSocket) fails on main @ 21fc468:
  FAIL dashboard did not render (no 'Routine Watch' in DOM)
Interface: reproduce with `scripts/integration.sh`; logs in `.dev/api.log` / `.dev/web.log`. Fix the cause (not the check) unless the check itself is wrong.
Acceptance:
- `scripts/integration.sh` prints OK; `scripts/ci.sh` passes.

### T271 — Review: handoff summary counts a paused resident as "nothing to review"
- status: done
- class: light
- priority: 1
- kind: bug
- source: reviewer
- deps: —
- area: pipeline/src/routine_watch/handoff.py, pipeline/tests/test_handoff.py
- owner: ian-claude-light-2
- claimed: 2026-10-17T12:53Z
- pr: #254
- rating: 5/5 clear

What: T259 (#243) adds "Room X (name) was paused, so no flags are expected from it" to the handoff context, but `_context` still computes `quiet = len(rows) - len(review)` including paused residents, so a paused, otherwise-quiet room also reads as "N residents with nothing to review" — the exact "all quiet" reading T259 meant to stop.
Interface: in `handoff._context`, exclude rows with `monitoring_paused` (and not `_needs_review`) from `quiet`; keep the paused line as is.
Acceptance:
- test: pause a quiet resident's room; the context has its paused line and the "nothing to review" count drops by one (line omitted when it reaches 0).
- existing handoff tests pass; `scripts/ci.sh` passes.

### T272 — Review: duplicate scenario-README test in tests/ and pipeline/tests/
- status: todo
- class: light
- priority: 2
- kind: test
- source: reviewer
- deps: —
- area: tests/test_scenarios_readme.py, pipeline/tests/test_scenarios_readme.py
- owner: —
- claimed: —
- pr: —

What: `tests/test_scenarios_readme.py` and `pipeline/tests/test_scenarios_readme.py` both check that every `tests/scenarios/*` folder has a README row, with slightly different rules (expected.yaml dirs vs all dirs). Two copies drift and both run in CI.
Interface: keep the pipeline/tests one (runs with the other scenario tests), fold in any check only the root one has, delete `tests/test_scenarios_readme.py`.
Acceptance:
- one README-coverage test remains; adding a scenario folder without a README row still fails it.
- `scripts/ci.sh` passes.

### T273 — CI: run the first-load bundle budget check after the web build
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: scripts/ci.sh
- owner: —
- claimed: —
- pr: —

What: T260 (#251) added `npm run check:bundle` in web/ but nothing runs it, so the budget never fails a PR. Wire it into CI right after the build.
Interface: in `scripts/ci.sh`, the node loop line `(cd "$d" && npm ci ... && npm run build --if-present)`: append `&& npm run check:bundle --if-present` so it only runs for packages that define it. Read only `scripts/ci.sh` and `web/package.json`. Touch nothing else.
Acceptance:
- `scripts/ci.sh` passes and its output includes the "First-load JS (gzipped):" and "Budget:" lines from web/scripts/check-bundle.mjs.

### T274 — Refactor: smoke.sh JSON checks through one helper; demo room read from /residents
- status: todo
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: scripts/smoke.sh
- owner: —
- claimed: —
- pr: —

What: `scripts/smoke.sh` repeats the same `python3 -c 'import json, sys ... assert ...'` block for every check, and T245 hardcoded `demo_room="204"`. Add one `check_json <label> <body> <python-expr>` helper and use it everywhere; read the demo room from the first resident in `GET /residents` instead of hardcoding it.
Interface: `scripts/smoke.sh` only; same PASS/FAIL output lines and exit code.
Acceptance:
- Every existing check still runs and passes with `scripts/dev.sh up && scripts/smoke.sh; scripts/dev.sh down`.
- No `"204"` literal left in smoke.sh; script is shorter than before.
- `scripts/ci.sh` passes.
