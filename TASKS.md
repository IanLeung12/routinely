# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: 369fc9b

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
- note: released by ian-claude-light-2: run ended without progress; partial work on branch task/T229-wip-1210: start from it (git switch task/T229-wip-1210 && git merge origin/main)

What: `PatternList.test.tsx > never uses diagnostic wording` renders two `pattern()` fixtures that both have `pattern_id: 'delirium'`, so React logs "Encountered two children with the same key" in every CI run, hiding real warnings.
Interface: read `web/src/alert/PatternList.test.tsx` only. Give the second fixture a different `pattern_id` (e.g. `pattern({ pattern_id: 'infection', urgency: 'urgent' })`); fix any other test in the file that renders duplicate ids the same way.
Acceptance:
- `cd web && npx vitest run src/alert/PatternList.test.tsx 2>&1 | grep -c "same key"` prints 0; all tests pass
- `scripts/ci.sh` passes

### T231 — Test: integration.sh dashboard check retries instead of failing on a cold Vite start
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: scripts/integration.sh
- owner: —
- claimed: —
- pr: —
- source: integration

What: The integration run on main @ 60dce5a failed with "dashboard did not render (no 'Routine Watch' in DOM)", but the orchestrator reran `scripts/integration.sh` on the same sha at 10:52 UTC and it passed, so it is a flake (likely the headless-Chrome DOM dump racing Vite's first compile). Make the check robust, not looser.
Interface: in `scripts/integration.sh`, the "Rendered dashboard" block (around line 45): retry the `--dump-dom` up to 3 times with a 3 s sleep between attempts before calling `fail`; keep both existing grep checks unchanged.
Acceptance:
- a slow first render no longer fails the run; a dashboard that never renders still fails with the same message
- `scripts/integration.sh` prints OK and `scripts/ci.sh` passes

### T238 — Alert view: usable at phone width (375 px)
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/alert/alert.css, web/src/alert/PatternList.css
- owner: ian-claude-standard-2
- claimed: 2026-10-17T11:32Z
- pr: #232
- rating: 4/5 clear, but the /alerts/<id> URL in the acceptance criteria doesn't exist (no router — alerts open via in-page state), so verifying required scripting a headless-Chrome click-through instead of a direct navigate

What: Nurses open alerts from a phone (push alert, SPEC §5 nice-to-have 3), but the alert screen has no responsive rules. Add a `@media (max-width: 480px)` block to `alert.css` and `PatternList.css` (same breakpoint as T235's `live/liveScreen.css`) so the header, error list, pattern cards, suggested checks and feedback buttons stack without horizontal scroll.
Interface: CSS only in the two files listed; no markup or class name changes. If the ghost replay figure (styled in `web/src/index.css`) still overflows, note it in the PR instead of editing index.css.
Acceptance:
- No horizontal scroll on `/alerts/<id>` at 375 px; feedback buttons wrap and stay ≥44 px tall tap targets.
- Desktop layout unchanged.
- `scripts/ci.sh` passes; PR body notes the viewport widths checked (e.g. Playwright screenshot at 375 and 1280).

### T239 — Resident detail: usable at phone width (375 px)
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/driftCard.css, web/src/resident/heatCalendar.css, web/src/resident/resident.css (new), web/src/resident/ResidentDetail.tsx
- owner: —
- claimed: —
- pr: #231
- rating: 5/5 clear
- note: merged as #231

What: The resident detail screen (baseline chart, slow-drift card, heat calendar, sessions, care records) has no responsive rules. Add `@media (max-width: 480px)` rules so it reads on a phone: chart and calendar scale to the card width (or scroll inside their own card, never the page), lists stack.
Interface: CSS in the listed files; `resident.css` is new and imported by ResidentDetail.tsx for any rules not owned by DriftCard/HeatCalendar. Don't move rules out of `web/src/index.css` (T234 owns that pattern for the overview); add overrides instead.
Acceptance:
- No page-level horizontal scroll on `/residents/mrs-k` at 375 px; desktop layout unchanged.
- Existing resident tests still pass; `scripts/ci.sh` passes; PR body notes the widths checked.

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

### T241 — Test: no user-facing web copy says "diagnose" or "has <condition>"
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/wording.test.ts (new)
- owner: —
- claimed: —
- pr: —

What: The wording rule (AGENTS.md: the product flags a change for review, lists patterns it is "consistent with", never "diagnoses") is only checked per component. Add one guard test that scans every non-test `web/src/**/*.ts(x)` file's string literals and JSX text for `diagnos` (case-insensitive) and fails with the file and line.
Interface: `web/src/wording.test.ts` using `import.meta.glob('./**/*.{ts,tsx}', { query: '?raw', import: 'default', eager: true })`, skipping `*.test.*` and `contracts.ts`. Strip `//` and `/* */` comments before matching (LiveSession.tsx and PatternList.tsx mention "never diagnoses" in comments, which is fine).
Acceptance:
- Test passes on current main; temporarily adding `'Diagnosed with X'` to any component makes it fail with that file named (say so in the PR body).
- `scripts/ci.sh` passes.

### T242 — Web: monitoring API client (GET /monitoring, PUT /rooms/{room}/monitoring)
- status: done
- class: light
- priority: 1
- kind: feature
- deps: —
- area: web/src/about/monitoringApi.ts, web/src/about/monitoringApi.test.ts
- owner: ian-claude-light-2
- claimed: 2026-10-17T11:39Z
- pr: #230
- rating: 5/5 clear

What: T149 (#226) added the pipeline endpoints behind the room pause switch, but the web has no client for them. Add a small typed client; no UI changes.
Interface: read `pipeline/src/routine_watch/api.py` (search `monitoring`) and `web/src/config.ts` (`apiUrl`), copy the fetch style of `web/src/resident/api.ts`. Export `fetchPausedRooms(): Promise<string[]>` (GET `${apiUrl}/monitoring`, returns `paused_rooms`) and `setRoomMonitoring(room: string, on: boolean): Promise<void>` (PUT `${apiUrl}/rooms/${encodeURIComponent(room)}/monitoring` with the JSON body the endpoint expects). Both throw on network error or non-ok response.
Acceptance:
- tests with a stubbed `fetch` cover: URL + method + body, parsed result, throws on `ok: false`, throws on network error
- `cd web && npm test` and `scripts/ci.sh` pass

### T243 — Resident detail: monitoring switch reads and writes the real pause state
- status: done
- class: standard
- priority: 1
- kind: feature
- deps: T242
- area: web/src/resident/ResidentDetail.tsx, web/src/resident/ResidentDetail.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T11:57Z
- pr: #235
- rating: 5/5 clear

What: `ResidentDetail` keeps the monitoring switch in local `useState(true)`, so pausing a room does nothing on the server (SPEC §12). Load the initial state from `fetchPausedRooms()` and call `setRoomMonitoring()` on toggle (T242).
Interface: consume `web/src/about/monitoringApi.ts`; `MonitoringToggle` props unchanged. Optimistic toggle; if the PUT fails, revert the switch and show a short inline message ("Couldn't change monitoring. Try again."). If the GET fails (API down / mock mode), keep today's local-only behaviour, no error shown.
Acceptance:
- tests: initial state reflects a paused room; toggle sends PUT; failed PUT reverts + shows message; GET failure falls back to "on"
- `cd web && npm test` and `scripts/ci.sh` pass

### T244 — Live screen: show "Monitoring paused" when /ws/live sends {"type":"paused"}
- status: done
- class: standard
- priority: 1
- kind: bug
- deps: —
- area: web/src/live/useLiveSession.ts, web/src/live/useLiveSession.test.ts, web/src/live/LiveScreen.tsx, web/src/live/LiveScreen.test.tsx
- owner: ian-claude
- claimed: 2026-10-17T11:39Z
- pr: #233
- rating: 4/5 clear on the interface and acceptance, but the area named LiveScreen.tsx/LiveScreen.test.tsx while the hook is consumed by LiveSession.tsx, which owns the skeleton/task map the acceptance asks about

What: since T149 (#226), `/ws/live` sends one `{"type": "paused", "room": "<room>"}` and closes if the demo resident's room is paused. `useLiveSession` counts that as data received, ignores the unknown type, and the live screen sits empty with no explanation. Handle it explicitly.
Interface: add a `paused` message to the hook's `LiveMessage` union (web-side type only; don't touch `contracts/`) and a `paused: { room: string } | null` field to its state; do not fall back to mock data when paused. `LiveScreen` renders the `EmptyState` from `web/src/ui/` with "Monitoring is paused for room <room>" and a hint that it can be turned back on from the resident's page.
Acceptance:
- hook test: a fake socket sending `paused` then closing yields `paused.room`, no mock fallback
- LiveScreen test: paused state shows the message, no skeleton/task map
- `cd web && npm test` and `scripts/ci.sh` pass

### T245 — Smoke: check GET /monitoring and a PUT round-trip
- status: todo
- class: light
- priority: 2
- kind: test
- deps: T192
- area: scripts/smoke.sh
- owner: —
- claimed: —
- pr: —

What: `scripts/smoke.sh` doesn't exercise the monitoring endpoints added in T149 (#226). Add checks so the tester catches a broken pause switch.
Interface: read `scripts/smoke.sh` (copy the `curl "${CURL_OPTS[@]}"` + `pass`/`fail` pattern) and `pipeline/src/routine_watch/api.py` (search `monitoring`). Before the final `/demo/reset` block: GET `/monitoring` returns JSON with `paused_rooms`; PUT pause on the demo resident's room, GET shows it paused, PUT resume, GET shows it gone; PUT on an unknown room returns 404. Always resume the room even if a check fails.
Acceptance:
- `scripts/dev.sh up && scripts/smoke.sh` passes with the new checks; `scripts/dev.sh down`
- `bash -n scripts/smoke.sh` and `scripts/ci.sh` pass

### T246 — Unit overview: "Monitoring paused" chip on residents whose room is paused
- status: todo
- class: light
- priority: 2
- kind: feature
- deps: T242
- area: web/src/overview/UnitOverview.tsx, web/src/overview/UnitOverview.test.tsx, web/src/overview/overview.css
- owner: —
- claimed: —
- pr: —

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
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_live_flag_consistency.py
- owner: —
- claimed: —
- pr: —

What: Guard T236 across all recordings: after a live replay of each scenario in `tests/scenarios/`, `session_end.flag` must equal that resident's flagged state from `/residents`, and `alert_id` must be `None` or an id that `/alerts/{id}` returns 200 for.
Interface: read `pipeline/tests/test_live.py` (how it drives `session_messages` / `/ws/live` with the FastAPI `TestClient`) and `pipeline/tests/test_api_demo_reset.py` (calling `/demo/reset` between cases). New file only; parametrize over scenario dirs; reset state between cases.
Acceptance:
- one parametrized test per scenario; fakes only, no real API calls
- `cd pipeline && python -m pytest tests/test_live_flag_consistency.py` and `scripts/ci.sh` pass

### T249 — Review: pausing a room mid-session doesn't stop the live session
- status: done
- class: standard
- priority: 1
- kind: bug
- source: reviewer
- deps: —
- area: pipeline/src/routine_watch/api.py, pipeline/tests/test_api_monitoring.py
- owner: ian-claude-standard-2
- claimed: 2026-10-17T11:52Z
- pr: #234
- rating: 5/5 clear

What: `/ws/live` checks `get_monitoring_store().is_on(room)` only once before the session starts. If a nurse pauses the room while a session is streaming, frames keep going out and the finished session is still recorded into the resident's history (and can flag them), although the UI says "No camera data is processed while paused" (SPEC §12).
Interface: in the `async for message in session_messages(...)` loop in `api.py`, re-check the resident's room each message; if paused, send `{"type": "paused", "room": room}`, close normally and stop iterating (closing the generator early means `session_messages` never records the session, same as a dashboard disconnect). Factor the check into one helper used at start and in the loop.
Acceptance:
- test: start `/ws/live`, `PUT /rooms/{room}/monitoring {"on": false}` after the first message, assert a `paused` message arrives, no `session_end`, and `/residents/{id}` session count is unchanged
- `scripts/ci.sh` passes

### T250 — Review: /ws/live message protocol has no contract
- status: done
- class: heavy
- priority: 2
- kind: improvement
- source: reviewer
- deps: T244
- area: contracts/live_message.schema.json, contracts/README.md, pipeline/tests/test_live_contract.py
- owner: ian-claude
- claimed: 2026-10-17T11:53Z
- pr: #240
- rating: 4/5 the area left out contracts.py (the generated-schema source) and test_contracts.py, whose raw-frame guard rejects an envelope with a 'frame' property and an open step_state map

What: The live socket's messages (`session_start`, `frame`, `step`, `step_state`, `error`, `session_end`, and now `paused`) cross the pipeline/web boundary but are defined only in `live.py`'s docstring and hand-mirrored in `web/src/live/useLiveSession.ts`; `paused` was just added on one side only. Add a JSON Schema (`oneOf` on `type`) to `contracts/`.
Interface: read `pipeline/src/routine_watch/live.py` (module docstring + `as_json`), `api.py` `live_session`, and `web/src/live/useLiveSession.ts`. Schema only plus a test; don't change message shapes.
Acceptance:
- pytest replays one scenario through `/ws/live` (fakes only) and validates every message, plus a `paused` message, against the schema
- `contracts/README.md` lists it; `scripts/ci.sh` passes

### T251 — Shift handoff payload lists rooms whose monitoring is paused
- status: done
- class: standard
- priority: 2
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/handoff.py, pipeline/tests/test_handoff.py
- owner: ian-claude-standard-2
- claimed: 2026-10-17T12:03Z
- pr: #238
- rating: 5/5 clear

What: A nurse taking over a shift must know which rooms aren't being watched; a paused room silently produces no flags, so today the handoff can read "all quiet" for a resident nobody was monitoring (SPEC §12).
Interface: `build_handoff(...)` adds `"paused": [{"room": str, "resident_id": str, "name": str}]` to its result, read from `get_monitoring_store().paused_rooms()` (`monitoring.py`) and the room→resident config the API already uses for `/ws/live`; empty list when nothing is paused. Each resident row whose room is paused gets `"monitoring_paused": true` (else false). Don't change `api.py` (the endpoint returns `build_handoff` as-is) or anything in `web/`.
Acceptance:
- Tests in `pipeline/tests/test_handoff.py`: nothing paused → `paused == []`, all rows false; pause one room → that resident listed once, its row true; resume → back to empty. Reset the monitoring store between tests.
- Summary/flag counts unchanged by pausing.
- `scripts/ci.sh` passes.

### T252 — Web: lazy-load the secondary screens to shrink the first-load bundle
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/App.tsx, web/src/App.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T12:04Z
- pr: #237
- rating: 5/5 clear

What: The demo opens on the unit overview, but `App.tsx` statically imports every screen (pattern library, shift handoff, tour, live screen, alert view). Load the screens not shown on first paint with `React.lazy` + `Suspense` so the overview appears faster on a phone.
Interface: In `App.tsx` only, `lazy(() => import(...))` for `PatternLibrary`, `Handoff` and `Tour` (named exports: map to `{ default: m.X }`); wrap each in `<Suspense fallback={...}>` using an existing `web/src/ui/` loading/empty component. Keep the overview, resident detail, live and alert screens static (demo path). No behaviour or copy changes.
Acceptance:
- Existing `App.test.tsx` tests pass (use `findBy*` where a lazy screen now resolves async); add one test that opening "Shift handoff" still renders it.
- PR body gives the main JS chunk size from `cd web && npm run build` before and after.
- `scripts/ci.sh` passes.

### T253 — Shift handoff screen: show the rooms whose monitoring is paused
- status: todo
- class: light
- priority: 2
- kind: feature
- deps: T251
- area: web/src/handoff/types.ts, web/src/handoff/mockHandoff.ts, web/src/handoff/Handoff.tsx, web/src/handoff/Handoff.test.tsx
- owner: —
- claimed: —
- pr: —

What: Show T251's new `paused` list on the handoff screen so the incoming nurse sees which rooms weren't watched.
Interface: Read `web/src/handoff/types.ts`, `Handoff.tsx`, `mockHandoff.ts` and T251's docstring in `pipeline/src/routine_watch/handoff.py`. Add `paused: { room: string; resident_id: string; name: string }[]` to the `Handoff` type (treat missing as `[]` for older APIs) and `monitoring_paused?: boolean` to `HandoffResident`. When non-empty, render one line above the rows: "Monitoring paused: <name> (room <room>), ..." and a "Monitoring paused" chip on those residents' rows. Include the line in `handoffText`. Mock gets `paused: []`.
Acceptance:
- Tests: no line when `paused` is empty or missing; line + chip when one room is paused; `handoffText` includes it.
- `scripts/ci.sh` passes.

### T254 — Demo residents carry a consent record (who opted in, when)
- status: done
- class: standard
- priority: 2
- kind: feature
- source: proposed
- deps: —
- area: pipeline/src/routine_watch/demo.py, pipeline/tests/test_demo_consent.py
- owner: ian-claude-standard
- claimed: 2026-10-17T12:10Z
- pr: #239
- rating: 5/5 clear

What: SPEC §12 says the resident or their substitute decision-maker opts in per room, but nothing shows that consent exists. Add a seeded consent record per demo resident so judges see consent is part of the design (Responsible design / Usefulness).
Interface: In `demo.py`, add to each `_RESIDENTS` entry and to every `demo_residents()` dict a `consent: {"given_by": str, "on": "YYYY-MM-DD"}` field, e.g. `{"given_by": "Resident", ...}` or `{"given_by": "Substitute decision-maker (daughter)", ...}`; dates before the 14-day history starts, deterministic. `GET /residents` and `/residents/{id}` already return these dicts, so no `api.py` change.
Acceptance:
- New `pipeline/tests/test_demo_consent.py`: every demo resident has `consent.given_by` (non-empty) and `consent.on` (ISO date before its first session); `GET /residents/mrs-k` includes `consent`.
- Existing demo/stability tests unchanged; `scripts/ci.sh` passes.

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

What: Show T254's consent record under the monitoring switch: "Consent: Substitute decision-maker (daughter), 2026-09-28". Small grey text, nothing when the field is missing (older API / mock without it).
Interface: Read `web/src/overview/types.ts` (resident type), `web/src/resident/ResidentDetail.tsx` (header with `MonitoringToggle`), and `pipeline/src/routine_watch/demo.py` (T254's `consent: {given_by, on}`). Add optional `consent?: { given_by: string; on: string }` to the resident type; give the three mock residents in `web/src/mock/residents.ts` a consent record.
Acceptance:
- Tests in `ResidentDetail.test.tsx`: consent line renders with given_by and date; no line when `consent` is absent.
- `scripts/ci.sh` passes.

### T256 — Refactor: move monitoring routes and /ws/live out of api.py
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: pipeline/src/routine_watch/api.py, pipeline/src/routine_watch/api_live.py, docs/CODEMAP.md
- owner: ian-claude-standard-2
- claimed: 2026-10-17T12:13Z
- pr: #241
- rating: 5/5 clear

What: `api.py` is 450 lines mixing residents, alerts, feedback, replay, monitoring and the live socket. Move `GET /monitoring`, `PUT /rooms/{room}/monitoring`, `_room_for`, `_pause_message` and `/ws/live` into a new `api_live.py` (FastAPI `APIRouter`) included by `api.py`. Pure move: no behaviour or URL change.
Interface: `api_live.router` included with `app.include_router(...)`; keep any names tests import from `routine_watch.api` re-exported there (grep `pipeline/tests` for `from routine_watch.api import`). Add a CODEMAP note.
Acceptance:
- No test file changes needed except imports; all of `pipeline/tests/test_api_monitoring.py`, `test_live*.py` pass unchanged.
- `api.py` shrinks by ≥80 lines; `scripts/ci.sh` and `scripts/e2e.sh` pass.

### T257 — Contracts: JSON Schemas for /residents and /handoff payloads
- status: claimed
- class: heavy
- priority: 2
- kind: improvement
- source: reviewer
- deps: T250, T251
- area: contracts/resident.schema.json, contracts/handoff.schema.json, contracts/README.md, pipeline/tests/test_api_payload_contracts.py
- owner: ian-claude
- claimed: 2026-10-17T12:18Z
- pr: —

What: REVIEW.md noted the resident and handoff payloads have no `contracts/` schema and web types are hand-mirrored (`web/src/overview/types.ts`, `web/src/handoff/types.ts`), which is how fields drift. Add schemas describing today's shapes (incl. `top_pattern`, `monitoring_paused`/`paused` from T251).
Interface: Read `api.py` `list_residents`/`get_resident`/`shift_handoff`, `handoff.py`, `demo.py`, and the two web type files. Schemas only plus a test; don't change payload shapes. If a web type disagrees with the API, note it in the PR and file nothing else in this PR.
Acceptance:
- pytest validates `GET /residents`, `GET /residents/{id}` for every demo resident, and `GET /handoff` against the schemas (fakes only).
- `contracts/README.md` lists both; `scripts/ci.sh` passes.

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
- status: claimed
- class: standard
- priority: 2
- kind: test
- deps: —
- area: web/scripts/check-bundle.mjs, web/package.json, web/README.md
- owner: ian-claude-standard
- claimed: 2026-10-17T12:26Z
- pr: —

What: #237 lazy-loaded the handoff, pattern library and tour screens to shrink first paint. Lock that in: a small Node script that, after `vite build`, sums the gzipped size of the JS the entry `index.html` loads (not lazy chunks) and fails above a budget set ~10% over today's size.
Interface: `web/scripts/check-bundle.mjs` (Node built-ins only: `fs`, `zlib`, `path`), `npm run check:bundle` in `web/package.json` that runs it against `web/dist/`. Print the measured size and the budget. Document the budget and how to raise it in `web/README.md`. Don't edit `scripts/ci.sh` (note in the PR if it should be wired in).
Acceptance:
- `cd web && npm run build && npm run check:bundle` passes on main and prints sizes; temporarily importing `Handoff` eagerly in `App.tsx` makes it fail (describe this check in the PR, don't commit it).
- `scripts/ci.sh` passes.

### T261 — Review: tests can hit paid APIs if LIVE_API=1 is exported in the shell
- status: claimed
- class: light
- priority: 1
- kind: bug
- source: reviewer
- deps: —
- area: scripts/ci.sh, pipeline/tests/conftest.py
- owner: ian-claude-light-2
- claimed: 2026-10-17T12:25Z
- pr: —

What: `scripts/ci.sh` and pytest never force `LIVE_API` off (only e2e.sh/integration.sh do), and `.env.example` documents `LIVE_API`. An agent or teammate with `LIVE_API=1` exported who runs `scripts/ci.sh` makes real Claude/Gemini calls from unit tests (AGENTS.md: tests never make real calls).
Interface: in `scripts/ci.sh` add `export LIVE_API=0` right after the `cd` line. In `pipeline/tests/conftest.py` add an autouse fixture doing `monkeypatch.setenv("LIVE_API", "0")` so plain `pytest` is safe too; a test that checks the live path can still override it with its own monkeypatch.
Acceptance:
- `LIVE_API=1 bash scripts/ci.sh` passes and makes no network calls.
- `scripts/ci.sh` passes.

### T262 — Monitoring audit trail: who paused/resumed a room and when
- status: todo
- class: heavy
- priority: 2
- kind: feature
- source: proposed
- deps: T256
- area: pipeline/src/routine_watch/monitoring.py, pipeline/src/routine_watch/routes_monitoring.py, pipeline/tests/test_monitoring_audit.py, web/src/resident/, web/src/api/monitoring.ts
- owner: —
- claimed: —
- pr: —

What: Rationale: SPEC §12 privacy accountability; judges see that pausing a camera is logged. Record each pause/resume (room, on/off, by, at) in memory and show the last 5 on resident detail under the monitoring switch.
Interface: `MonitoringState.history(room) -> list[dict(on: bool, by: str, at: iso str)]`; PUT /rooms/{room}/monitoring accepts optional `by` (default "nurse"); GET /rooms/{room}/monitoring/history returns the list (newest first, max 20); `/demo/reset` clears it. Web: small "Recent changes" list under the switch, empty state "No changes this shift". Use the real file names after T256's refactor (adjust area paths in the PR if they differ).
Acceptance:
- pytest test covers pause → resume → history order and reset clearing it.
- web test renders the list and the empty state.
- `scripts/ci.sh` passes.

### T263 — Contracts: JSON Schema for GET /alerts/{id} and the feedback POST body
- status: todo
- class: heavy
- priority: 2
- kind: improvement
- deps: T257
- area: contracts/, pipeline/src/routine_watch/contracts.py, pipeline/tests/test_contracts.py, web/src/contracts.ts
- owner: —
- claimed: —
- pr: —

What: Same pattern as T250/T257: the alert detail response and the feedback request are hand-mirrored in web/src/contracts.ts; generate schemas from pydantic so drift fails CI.
Interface: `contracts/alert_detail.schema.json`, `contracts/feedback.schema.json` generated from contracts.py; a test validates real API responses (fakes only) against them and checks web/src/contracts.ts field names match.
Acceptance:
- schemas generated, README in contracts/ updated.
- test fails if a field is added on one side only.
- `scripts/ci.sh` passes.

### T264 — Test: consent record survives /demo/reset and shows in /handoff residents
- status: todo
- class: standard
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_demo_consent.py
- owner: —
- claimed: —
- pr: —

What: T254 added per-resident consent; nothing checks it survives `/demo/reset` or that every resident in GET /residents (not just mrs-k) carries it.
Interface: extend pipeline/tests/test_demo_consent.py using the FastAPI TestClient with fakes.
Acceptance:
- every resident from GET /residents has consent.given_by and consent.on, before and after POST /demo/reset.
- `scripts/ci.sh` passes.
