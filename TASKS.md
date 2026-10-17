# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: 8077353

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
- status: done
- class: light
- priority: 2
- kind: test
- source: reviewer
- deps: —
- area: tests/test_scenarios_readme.py, pipeline/tests/test_scenarios_readme.py
- owner: ian-claude-light-2
- claimed: 2026-10-17T14:01Z
- pr: #275
- rating: 5/5 clear

What: `tests/test_scenarios_readme.py` and `pipeline/tests/test_scenarios_readme.py` both check that every `tests/scenarios/*` folder has a README row, with slightly different rules (expected.yaml dirs vs all dirs). Two copies drift and both run in CI.
Interface: keep the pipeline/tests one (runs with the other scenario tests), fold in any check only the root one has, delete `tests/test_scenarios_readme.py`.
Acceptance:
- one README-coverage test remains; adding a scenario folder without a README row still fails it.
- `scripts/ci.sh` passes.

### T273 — CI: run the first-load bundle budget check after the web build
- status: claimed
- class: light
- priority: 2
- kind: test
- deps: —
- area: scripts/ci.sh
- owner: ian-claude
- claimed: 2026-10-17T14:12Z
- pr: —

What: T260 (#251) added `npm run check:bundle` in web/ but nothing runs it, so the budget never fails a PR. Wire it into CI right after the build.
Interface: in `scripts/ci.sh`, the node loop line `(cd "$d" && npm ci ... && npm run build --if-present)`: append `&& npm run check:bundle --if-present` so it only runs for packages that define it. Read only `scripts/ci.sh` and `web/package.json`. Touch nothing else.
Acceptance:
- `scripts/ci.sh` passes and its output includes the "First-load JS (gzipped):" and "Budget:" lines from web/scripts/check-bundle.mjs.

### T274 — Refactor: smoke.sh JSON checks through one helper; demo room read from /residents
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: scripts/smoke.sh
- owner: ian-claude-standard
- claimed: 2026-10-17T13:15Z
- pr: #261
- rating: 5/5 clear

What: `scripts/smoke.sh` repeats the same `python3 -c 'import json, sys ... assert ...'` block for every check, and T245 hardcoded `demo_room="204"`. Add one `check_json <label> <body> <python-expr>` helper and use it everywhere; read the demo room from the first resident in `GET /residents` instead of hardcoding it.
Interface: `scripts/smoke.sh` only; same PASS/FAIL output lines and exit code.
Acceptance:
- Every existing check still runs and passes with `scripts/dev.sh up && scripts/smoke.sh; scripts/dev.sh down`.
- No `"204"` literal left in smoke.sh; script is shorter than before.
- `scripts/ci.sh` passes.

### T275 — Live screen: notice a pause/resume made while the panel is open
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/about/monitoringApi.ts, web/src/about/monitoringApi.test.ts, web/src/live/LiveScreen.tsx, web/src/live/LiveScreen.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T13:31Z
- pr: #264
- note: released by ian-claude-standard-2: run ended without progress; partial work on branch task/T275-wip-1328: start from it (git switch task/T275-wip-1328 && git merge origin/main)
- rating: 4/5 area listed stale files (LiveScreen.tsx) instead of where the paused UI actually lives (LiveSession.tsx); otherwise clear and the acceptance criteria matched the released WIP implementation exactly

What: Tester (TESTREPORT @1d6ee98) saw that toggling monitoring doesn't update an already-open live panel until remount or "Check again". Make the live panel react immediately.
Interface: `setRoomMonitoring` dispatches `window.dispatchEvent(new CustomEvent('monitoring-changed', {detail: {room, paused}}))` after a successful PUT; `LiveScreen` listens for it and, for its own room, shows the paused message or re-checks (same path as "Check again"). Remove the listener on unmount.
Acceptance:
- Test in LiveScreen.test.tsx: open panel for room 204, dispatch the event with paused=true → paused message shows; paused=false → panel re-checks. Event for another room changes nothing.
- monitoringApi.test.ts: event fires only on a successful PUT.
- `scripts/ci.sh` passes.

### T276 — Unit overview: "Paused" filter
- status: done
- class: standard
- priority: 3
- kind: feature
- deps: —
- area: web/src/overview/UnitOverview.tsx, web/src/overview/UnitOverview.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T13:23Z
- pr: #262
- rating: 5/5 clear

What: T246 added a "Monitoring paused" chip; add a "Paused (N)" button to the existing filter group so a nurse can list paused rooms in one tap.
Interface: extend `UnitFilter` with `'paused'`; `applyFilter` uses the `pausedRooms` state already fetched via `fetchPausedRooms`. Hide the button (or show 0) when the fetch failed; never break the list.
Acceptance:
- Test: with room 204 paused, clicking "Paused" shows only that resident and the count reads 1; with fetch failure the other filters still work.
- `scripts/ci.sh` passes.

### T277 — Bug: copied shift handoff says "Room unavailable" for every resident
- status: done
- class: heavy
- priority: 1
- kind: bug
- deps: —
- area: contracts/handoff.schema.json, contracts/examples/, pipeline/src/routine_watch/handoff.py, pipeline/tests/test_handoff.py, web/src/handoff/types.ts, web/src/handoff/Handoff.tsx, web/src/handoff/Handoff.test.tsx, web/src/handoff/mockHandoff.ts
- owner: ian-claude
- claimed: 2026-10-17T13:21Z
- pr: #263
- rating: 5/5 clear - the interface section named every file and the exact copy format, nothing to guess

What: `handoffText()` in `web/src/handoff/Handoff.tsx` hard-codes `Room unavailable` in every resident line of the "Copy summary" text (since T151), because `GET /handoff` rows have no `room`. A nurse pasting the handoff gets no room numbers. Found in orchestrator review of #259.
Interface: add required `room: string` to each `residents[]` row in `contracts/handoff.schema.json` (and examples), emit it from `pipeline/src/routine_watch/handoff.py` (`resident["room"]`), add `room: string` to `HandoffResident` in `web/src/handoff/types.ts` and the mock; copy line becomes `<name>, Room <room>: ...`. Show the room on the on-screen row too if it isn't already.
Acceptance:
- No `Room unavailable` string left in `web/src/`.
- Pipeline test asserts every `/handoff` row has the resident's room and validates against the schema; web test asserts copied text contains `Room <room>:`.
- `scripts/ci.sh` passes.

### T278 — Refactor: move resident, drift, replay and pattern routes out of api.py
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: pipeline/src/routine_watch/api.py, pipeline/src/routine_watch/api_residents.py, docs/CODEMAP.md
- owner: ian-claude-standard
- claimed: 2026-10-17T13:38Z
- pr: #265
- rating: 5/5 clear

What: Same pattern as T265 (api_alerts.py) and T256 (api_live.py): api.py still holds GET /residents, /residents/{id}, /residents/{id}/drift, /patterns, /sessions/{id}/replay and /residents/{id}/normal_replay. Move them into an `APIRouter` in a new `api_residents.py`, leaving api.py with app setup, /health, /demo/reset, /handoff and shared state.
Interface: `api_residents.router` included by `api.app`; route paths, response bodies and status codes unchanged. Follow how `api_alerts.py` reaches shared state (`from . import api` inside handlers) so /demo/reset stays visible.
Acceptance:
- No route behaviour changes: existing `pipeline/tests/test_api*.py` pass unmodified (imports may change only if a test imports a moved helper).
- api.py shorter by the moved routes; docs/CODEMAP.md note lists api_residents.py.
- `scripts/ci.sh` passes.

### T279 — Smoke: validate live API bodies against the contracts/ JSON Schemas
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: scripts/smoke.sh
- owner: ian-claude-standard-2
- claimed: 2026-10-17T13:43Z
- pr: #268
- rating: 5/5 clear

What: smoke.sh checks a few fields of each body by hand; the running stack can still drift from the published schemas. Add schema checks for the bodies it already fetches so the tester catches contract drift against a real stack, not just in unit tests.
Interface: reuse the `check_json` helper (T274) or add a `check_schema <label> <body> <schema file>` helper using `jsonschema` from the pipeline venv. Validate GET /residents rows (contracts/resident_summary.schema.json), GET /residents/mrs-k (resident.schema.json), GET /handoff (handoff.schema.json) and GET /alerts/<first id> (alert_detail.schema.json). If `jsonschema` is not importable, print SKIP for these checks rather than FAIL.
Acceptance:
- `scripts/dev.sh up && scripts/smoke.sh && scripts/dev.sh down` prints PASS for each new schema check (paste the output in the PR).
- Corrupting one field locally makes the matching check FAIL (describe how you checked it in the PR; don't commit the corruption).
- `scripts/ci.sh` passes.

### T280 — Contracts: JSON Schema for drift, replay and pattern-library payloads
- status: done
- class: heavy
- priority: 2
- kind: improvement
- deps: T269
- area: contracts/, pipeline/src/routine_watch/contracts.py, pipeline/tests/test_contracts.py, pipeline/tests/test_api_payload_contracts.py, web/src/contracts.ts
- owner: ian-claude
- claimed: 2026-10-17T13:54Z
- pr: #273
- rating: 5/5 clear - the T250/T257/T263/T269 precedent and the named web files made the shape obvious; only non-obvious bit was that the raw-frame guard in test_contracts.py had to learn about list-of-$ref and number-map properties

What: Same pattern as T250/T257/T263: GET /residents/{id}/drift, GET /sessions/{id}/replay, GET /residents/{id}/normal_replay and GET /patterns cross the pipeline/web boundary with hand-written types (`web/src/resident/api.ts` ResidentDrift, `web/src/patterns/types.ts`, the evidence replay types). Add contract models, generate schemas, and pin the routes to them.
Interface: new models in contracts.py added to `PAYLOADS`; generated `contracts/*.schema.json` + examples; contracts/README.md lists them. Don't rewrite the web consumers in this task (note follow-ups in the PR).
Acceptance:
- Schemas generated, README in contracts/ updated.
- `test_api_payload_contracts.py` validates each route's real response against its schema, and a test fails if a field is added on one side only.
- `scripts/ci.sh` passes.

### T281 — Shift handoff: paused rooms say who paused them and since when
- status: done
- class: standard
- priority: 2
- kind: feature
- deps: —
- area: web/src/handoff/Handoff.tsx, web/src/handoff/Handoff.test.tsx, web/src/handoff/handoff.css
- source: proposed
- owner: ian-claude-standard
- claimed: 2026-10-17T13:46Z
- pr: #274
- rating: 5/5 clear

What: Rationale: an incoming nurse reading "Monitoring paused: Mrs. K (room 204)" can't tell if that was a deliberate 5-minute pause or one forgotten since yesterday (SPEC §12). For each paused room on the handoff screen, show the latest pause entry from the audit trail ("paused by nurse at 13:40") on screen and in the copied text.
Interface: consume `fetchMonitoringHistory(room)` from `web/src/about/monitoringApi.ts` (read only; don't edit it) for each room in `Handoff.paused`; use the newest entry with `on: false`. If the history call fails or is empty, keep today's line unchanged (no error banner).
Acceptance:
- Screen and "Copy summary" text read like `Monitoring paused: Mrs. K (room 204), paused by nurse at 13:40`; time formatted as local HH:MM.
- History fetch failure → same output as today; no paused rooms → no history calls.
- Tests in Handoff.test.tsx cover: entry shown, fetch failure, no paused rooms; copied text still has no "diagnos".
- `scripts/ci.sh` passes.

### T282 — Integration: pausing a room makes /ws/live send "paused", resuming lets it run
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: scripts/integration.sh
- owner: ian-claude-standard-2
- claimed: 2026-10-17T13:56Z
- pr: #272
- rating: 5/5 clear

What: The pause flow (T244/T249/T266/T275) is covered by unit tests and an in-process API test, but not against the running stack. Extend scripts/integration.sh's existing websockets block to check it end to end.
Interface: against the stack integration.sh already starts: `PUT /rooms/204/monitoring` with `{"on": false}` → connect `/ws/live?scenario=tea_skip_teabag_pour_twice&speed=20` → first message has `"type": "paused"`; then `PUT ... {"on": true}` → a fresh connection gets a normal frame/step message. Always resume in a `trap`/finally so the stack is left unpaused; read the demo room from `GET /residents` (as smoke.sh does since T274) rather than hard-coding 204 if practical.
Acceptance:
- integration.sh fails with a clear message if the paused message is missing or the resumed session doesn't stream.
- Room is resumed even when a check fails.
- `scripts/integration.sh` passes locally on main (paste its last line in the PR); `scripts/ci.sh` passes.

### T283 — Resident detail: "What nurses said" — past feedback answers and the pattern ranking they changed
- status: todo
- class: heavy
- priority: 2
- kind: feature
- deps: T278
- area: pipeline/src/routine_watch/feedback.py, pipeline/src/routine_watch/api_residents.py, pipeline/tests/test_feedback_history.py, web/src/resident/FeedbackHistory.tsx, web/src/resident/FeedbackHistory.test.tsx, web/src/resident/feedbackHistory.css, web/src/resident/ResidentDetail.tsx, web/src/resident/api.ts, web/src/resident/types.ts
- source: proposed
- owner: —
- claimed: —
- pr: —

What: Rationale: the feedback loop (T130, Nice-to-have 8) re-weights patterns silently; judges and nurses can't see the AI learning. Expose a resident's recorded answers and current pattern weights and show them as a small card on the resident detail screen.
Interface: `FeedbackStore.history(resident_id) -> list[{alert_id, verdict, cause, at}]` (newest first) plus existing `pattern_weights()`; route `GET /residents/{id}/feedback` → `{"answers": [...], "pattern_weights": {pattern_id: float}}` (404 for unknown resident) in the residents routes module from T278. Web: `fetchFeedbackHistory(id)` in resident/api.ts, `<FeedbackHistory>` card under the session list: "Confirmed · consistent with <pattern name> · 13:40" rows and "Ranking now favours: <pattern>" when weights exist; empty state "No nurse answers yet". Don't add a contracts/ schema here (contracts/ is busy with T269/T280); note it in the PR for a follow-up.
Acceptance:
- pytest: answers recorded via the feedback POST appear newest-first; `/demo/reset` empties them; unknown resident → 404.
- Vitest: rows, empty state, fetch error state ("Couldn't load feedback"); copy uses "consistent with", never "diagnos".
- `scripts/ci.sh` passes.

### T284 — Review: move shared API state out of api.py to end the `from . import api` cycle
- status: in-review
- class: standard
- priority: 2
- kind: improvement
- deps: T278
- area: pipeline/src/routine_watch/api.py, pipeline/src/routine_watch/api_state.py, pipeline/src/routine_watch/api_residents.py, pipeline/src/routine_watch/api_alerts.py, pipeline/src/routine_watch/api_live.py, docs/CODEMAP.md
- source: reviewer
- owner: ian-claude-standard-2
- claimed: 2026-10-17T14:08Z
- pr: #277
- rating: 5/5 clear

What: After T278, `api_residents.py`, `api_alerts.py` (and `api_live.py`) reach back into `api.py` with function-level `from . import api` to get `_tuned`, `_SUMMARY_FIELDS`, `_feedback_store`, `_flagged_residents`. That's a circular import hidden inside every handler; each new router copies the pattern. Move that shared state/helpers into a new `api_state.py` (no FastAPI app import), have `api.py` and all routers import from it at module top, and keep test resets working by mutating the store in place (e.g. `api_state.reset()`), not rebinding a module global.
Acceptance:
- No `from . import api` left in `pipeline/src/routine_watch/api_*.py` (`grep` it in the PR).
- `/demo/reset` and existing test resets still clear feedback across all routes (existing pytest passes unchanged).
- CODEMAP note for `api_state.py`; `scripts/ci.sh` passes.

### T285 — Docs: DEMO.md walks through pausing a room, the consent line and the audit trail
- status: in-review
- class: light
- priority: 2
- kind: docs
- deps: —
- area: docs/DEMO.md
- owner: ian-claude-light-2
- claimed: 2026-10-17T14:16Z
- pr: #276
- rating: 5/5 clear

What: DEMO.md never mentions the monitoring switch, so presenters skip the privacy story judges ask about. Add one short demo step after the Mrs. K resident detail.
Interface: Read `docs/DEMO.md`, `web/src/resident/ResidentDetail.tsx` and `web/src/about/MonitoringToggle.tsx` for the exact on-screen copy. Step: open Mrs. K → point at the "Consent: ..." line → flip the switch to Paused ("No camera data is processed while paused", "Recent changes: Paused by nurse") → show the unit overview "Monitoring paused" chip and the shift handoff naming the paused room → resume (or `/demo/reset`).
Acceptance:
  * One new numbered step (≤10 lines) quoting the real UI copy; no "diagnose" wording
  * `scripts/ci.sh` passes

### T286 — Privacy panel: say pauses are logged and where consent is recorded
- status: claimed
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/about/PrivacyPanel.tsx, web/src/about/PrivacyPanel.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T14:23Z
- pr: —

What: The privacy panel's opt-in bullet predates the consent record (T255) and the audit trail (T262). Make it concrete in nurse-readable words.
Interface: In `web/src/about/PrivacyPanel.tsx`, replace only the last bullet with two: "Residents or their decision-maker opt in; who consented and when is shown on each resident's page." and "Monitoring can be paused per room; every pause and resume is logged with who and when."
Acceptance:
  * `PrivacyPanel.test.tsx` asserts both bullets render
  * `cd web && npm test -- PrivacyPanel` and `scripts/ci.sh` pass

### T287 — Test: alert feedback works keyboard-only
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/alert/FeedbackButtons.test.tsx
- owner: —
- claimed: —
- pr: —

What: Nurses on a shared workstation may use only the keyboard; prove the feedback flow (verdict, then cause) needs no mouse.
Interface: Read `web/src/alert/FeedbackButtons.tsx` and its test. With `@testing-library/user-event`: Tab to "Confirmed", press Enter, check `aria-pressed="true"` and the polite status text; Tab into the cause group, press Space on a cause, check its `aria-pressed`. Test-only: if a real keyboard bug shows up, describe it in the PR body instead of fixing it.
Acceptance:
  * New test(s) in `FeedbackButtons.test.tsx` using only keyboard events
  * `cd web && npm test -- FeedbackButtons` and `scripts/ci.sh` pass

### T288 — Smoke: validate /monitoring, room history and the first /ws/live message against contracts/
- status: claimed
- class: standard
- priority: 2
- kind: test
- deps: —
- area: scripts/smoke.sh
- owner: ian-claude-standard
- claimed: 2026-10-17T14:21Z
- pr: —

What: T279 schema-checks four bodies in smoke.sh; the monitoring and live endpoints (pipeline/src/routine_watch/api_live.py) still get spot checks or none, so contract drift there is only caught by unit tests.
Interface: reuse `check_schema` in scripts/smoke.sh. Add: GET /monitoring vs contracts/monitoring.schema.json; GET /rooms/<demo_room>/monitoring/history vs contracts/room_monitoring_history.schema.json (SKIP if demo_room is empty); the first message from /ws/live?scenario=tea_skip_teabag_pour_twice&speed=20 vs contracts/live_message.schema.json (pipeline venv Python with a websocket client already in pipeline deps, 5 s timeout; SKIP if none importable). Read-only: no PUTs.
Acceptance:
- `scripts/dev.sh up && scripts/smoke.sh` prints PASS for the three new checks on a fresh stack; then `scripts/dev.sh down`.
- Breaking a field by hand in one schema makes the matching check FAIL (say so in the PR, don't commit it).
- `scripts/ci.sh` passes.

### T289 — Alert view: print-friendly layout
- status: todo
- class: standard
- priority: 3
- kind: improvement
- deps: —
- area: web/src/alert/alert.css, web/src/alert/AlertView.tsx, web/src/alert/AlertView.test.tsx
- owner: —
- claimed: —
- pr: —

What: nurses bring flagged alerts to care conferences on paper; printing the alert today includes nav, feedback buttons and the dark replay card. Add a `@media print` layout so the page shows resident, errors, "consistent with" patterns, rule-outs and suggested checks in black on white.
Interface: `@media print` rules in alert.css; hide feedback buttons and the replay player via a `no-print` class; wording unchanged. Optional "Print" button calling `window.print()`.
Acceptance:
- AlertView.test.tsx: elements that must not print carry `no-print`; the Print button (if added) calls `window.print`.
- PR notes a Chrome print-preview check of the Mrs. K alert: 1–2 pages, no dark backgrounds.
- `cd web && npm test && npm run build` and `scripts/ci.sh` pass.

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

### T291 — Web: drift, pattern-library and replay types generated from contracts.py
- status: todo
- class: heavy
- priority: 2
- kind: improvement
- deps: —
- area: pipeline/src/routine_watch/contracts.py, web/src/contracts.ts, web/src/resident/api.ts, web/src/patterns/types.ts, web/src/evidence/api.ts, pipeline/tests/test_contracts.py, contracts/
- owner: —
- claimed: —
- pr: —

What: Follow-up from T280 (PR #273): the web still mirrors `ResidentDrift`, `PatternLibraryEntry` and the replay payloads by hand, guarded only by field-name tests. Emit them into the generated `web/src/contracts.ts` and make the consumers import them, so a contract change breaks the web build instead of a string-match test.
Interface: `python -m routine_watch.contracts` also writes TS types for the drift/pattern/replay models in `PAYLOADS` (or promotes them to `CONTRACTS`); `web/src/resident/api.ts` drops its hand-written `ResidentDrift`; `web/src/patterns/types.ts` re-exports or is replaced by the generated type; `web/src/evidence/api.ts` reads `SessionReplay`/`NormalReplay` instead of an inline cast. Replace the now-redundant field-name tests in test_contracts.py (drift type, pattern entry, replay cast) with the generated-file-up-to-date check.
Acceptance:
- No hand-written duplicate of these three payload shapes left in web/src; `test_generated_files_are_up_to_date` covers the new TS output.
- No behaviour change: existing web tests pass with only import changes.
- `scripts/ci.sh` passes.
