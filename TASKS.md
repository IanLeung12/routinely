# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: 085dc7c

## Tasks

### T133 — tasks.py: stop reading fields at the task body
- status: in-review
- class: light
- priority: 1
- kind: improvement
- deps: —
- area: scripts/tasks.py, tests/test_tasks_py.py (new or existing)
- source: retro
- owner: max_API_light
- claimed: 2026-10-17T07:55Z
- pr: #118
- rating: 5/5 clear

What: `parse()` treats every `- word: value` line in a task as a field, including acceptance bullets. On T071 an acceptance bullet `- mockLiveStream: emits ...` became a field, so `set note=...` inserted the note in the middle of the acceptance list. An acceptance bullet starting `- status:` would hijack the status. Fields are only the bullet block right after the `### T…` heading; stop collecting fields at the first blank line.
Acceptance:
- A task whose body has `- foo: bar` / `- status: x` bullets: `show` reports the header status, and `set note=...` inserts the note right after the header field block.
- Existing board parses identically for header fields (run `python3 scripts/tasks.py list` before/after).
- `scripts/ci.sh` passes.

### T062 — Nurse shift handoff summary (separate screen)
- status: claimed
- class: heavy
- priority: 3
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/handoff.py, pipeline/src/routine_watch/api.py (add the route only), pipeline/tests/test_handoff.py, web/src/handoff/, web/src/App.tsx (one nav entry)
- owner: ian-claude
- claimed: 2026-10-17T07:47Z
- pr: —
- source: proposed

What: Rationale: a nurse starting a shift wants one view of "who changed in the last 12 h" (Usefulness/Clarity, Use-of-AI hook). `GET /handoff?hours=12` lists residents with flags, pending-review alerts and drift trends in that window, plus a short plain-language summary from the existing `Explainer` interface (fake by default, no real call without `LIVE_API=1`). Wording: "flagged for review", never "diagnosed".
Interface: `handoff.build_handoff(now, hours) -> {"window_hours": int, "residents": [{"resident_id", "name", "flags": int, "pending_review": int, "trending": bool}], "summary": str}`; web screen `web/src/handoff/Handoff.tsx` reachable from one button in `App.tsx`, off the main demo path.
Acceptance:
- pytest: Mrs. K appears with her flag in the demo window; stable resident has 0 flags; summary comes from the fake explainer and contains no "diagnos".
- Web test renders the list and summary from mock data.
- `scripts/ci.sh` passes.

### T068 — Show the demo-data banner in the app
- status: todo
- class: light
- priority: 3
- kind: feature
- deps: T052, T063
- area: web/src/App.tsx, web/src/App.test.tsx
- owner: —
- claimed: —
- pr: —

What: Render the `DemoBanner` component from T052 (`web/src/ui/DemoBanner.tsx`) once, at the top of `App.tsx` above the header, on every screen.
Interface: read only `App.tsx`, `App.test.tsx`, `ui/DemoBanner.tsx`.
Acceptance:
- App test: banner visible on overview and after opening a resident.
- `scripts/ci.sh` passes.

### T071 — Tests for useLiveSession and mockLiveStream
- status: in-review
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/live/useLiveSession.test.ts, web/src/live/mockLiveStream.test.ts
- owner: ian-claude-light-2
- claimed: 2026-10-17T07:55Z
- pr: #116

What: The live screen's state hook and mock stream are untested. Read only `web/src/live/useLiveSession.ts`, `web/src/live/mockLiveStream.ts`, `web/src/live/LiveSession.test.tsx` (how it fakes the socket) and `.tasks/LESSONS.md` (pending effects after teardown break CI).
Interface: new test files only; use `vi.useFakeTimers()` and a fake WebSocket; no real network.
Acceptance:
- mockLiveStream: emits messages in order, ends with a session-ended message, and the returned stop function stops further messages.
- note: Earlier attempt left tests on an unpushed local branch; full web suite timed out locally in AlertView/PatternList (T132 tracks that). Write the tests, push and let GitHub CI decide.
- rating: 5/5 clear
- useLiveSession (renderHook): step states update from messages, the end message sets the ended state, and the socket closes on unmount.
- `cd web && npm run lint && npm test && npm run build` passes, run twice with no flakes.

### T089 — Unit overview shows the top pattern for flagged/watch residents
- status: todo
- class: standard
- priority: 2
- kind: feature
- deps: T084
- area: pipeline/src/routine_watch/demo.py, pipeline/src/routine_watch/api.py, pipeline/tests/test_api_residents.py, web/src/overview/, web/src/mock/residents.ts
- owner: —
- claimed: —
- pr: —

What: SPEC §9 screen 1 and demo step 6 ("Mr. D on watch, slow drift"): each flagged or watch resident row shows its top pattern name next to the status chip.
Interface: `GET /residents` items gain `top_pattern: {pattern_id, name, urgency} | null` from T084's scorer; `web/src/overview/types.ts` `ResidentSummary.top_pattern`; `UnitOverview` renders it as text (not colour alone); normal residents show nothing.
Acceptance:
- pytest: Mrs. K's `top_pattern.pattern_id == "sudden_change"`, drift resident's is `slow_drift`, normal residents `null`.
- Vitest: row shows pattern text for flagged resident, none for normal.
- `scripts/ci.sh` passes.

### T103 — Room monitoring pause toggle (component only)
- status: todo
- class: light
- priority: 3
- kind: feature
- deps: —
- area: web/src/about/MonitoringToggle.tsx (new), web/src/about/MonitoringToggle.test.tsx (new)
- source: proposed
- owner: —
- claimed: —
- pr: —

What: Responsible design made visible for judges (SPEC §12: "per room and can be turned off"): a per-room monitoring on/paused switch. Component only; wiring and API are later tasks. Read only `web/src/about/PrivacyPanel.tsx` (style) and `web/src/ui/Button.tsx`.
Interface: `export function MonitoringToggle({ room, on, onChange }: { room: string; on: boolean; onChange: (on: boolean) => void })` renders `<button role="switch" aria-checked={on}>` labelled "Monitoring in room {room}" with visible text "On" / "Paused", plus when paused a note "No camera data is processed while paused." CSS vars only.
Acceptance:
- Vitest: role switch with correct `aria-checked`; click calls `onChange(!on)`; paused note shows only when off.
- `cd web && npm run lint && npm test && npm run build` passes.

### T106 — Evidence replay: stop fetching the alert twice
- status: todo
- class: light
- priority: 3
- kind: improvement
- deps: —
- area: web/src/evidence/api.ts, web/src/evidence/api.test.ts, web/src/alert/AlertView.tsx
- owner: —
- claimed: —
- pr: —

What: Since T080 (#84), `AlertView` loads the alert with `fetchAlert`, then `fetchReplay(alertId)` calls `fetchAlert` again for the same alert. Change `fetchReplay` to take the already-loaded `Alert` so the screen makes one alert request.
Interface: `fetchReplay(alert: Alert): Promise<EvidenceReplay | null>` in `web/src/evidence/api.ts`; in `AlertView.tsx`, run the replay effect once the alert has loaded (keyed on alert id). Read only these three files plus `web/src/alert/AlertView.test.tsx`.
Acceptance:
- `api.test.ts` updated to pass an `Alert`; no `fetchAlert` call inside `evidence/api.ts`.
- AlertView still shows Loading / Empty / replay states as before (existing tests pass unchanged in behaviour).
- `cd web && npm test` and `scripts/ci.sh` pass.

### T107 — Review: evidence ghost layer replays the same frames as "today"
- status: done
- class: standard
- priority: 0
- kind: bug
- source: reviewer
- deps: —
- area: pipeline/src/routine_watch/evidence.py, pipeline/tests/test_evidence.py, tests/scenarios/tea_normal/frames.jsonl
- owner: ian-claude-standard-2
- claimed: 2026-10-17T07:02Z
- pr: #93

What: `evidence.py` sets both `_ALERT_SCENARIO` and `_NORMAL_SCENARIO` to `tea_no_kettle`, so `GET /residents/{id}/normal_replay` returns exactly the frames of `GET /sessions/{id}/replay` (only `session_id` differs). On the alert screen the ghost overlay sits perfectly on top of today's skeleton, so demo step 5 ("compare against her normal routine") shows no difference.
Fix: add a frame-level `tests/scenarios/tea_normal/frames.jsonl` (same capture format and timing as `tea_no_kettle/frames.jsonl`, but with the fill-kettle and boil contacts, so the recogniser reads all tea steps; check `tea_normal/expected.yaml` still passes via `scripts/e2e.sh`) and point `_NORMAL_SCENARIO` at `tea_normal`.
Acceptance:
- New test in `test_evidence.py`: for the same window, `normal_replay_frames` and `replay_frames` return different landmark/object data.
- `scripts/ci.sh` passes (including e2e on `tea_normal`).

### T108 — Review: smoke.sh skips the evidence replay routes and isn't syntax-checked in CI
- status: done
- class: light
- priority: 1
- kind: test
- source: reviewer
- deps: —
- area: scripts/smoke.sh, scripts/ci.sh
- owner: ian-claude-light-2
- claimed: 2026-10-17T07:01Z
- pr: #88

What: T037/T080 added `GET /sessions/{session_id}/replay` and `GET /residents/{resident_id}/normal_replay` (`pipeline/src/routine_watch/api.py`), which the alert screen's evidence card depends on, but `scripts/smoke.sh` only checks health/residents/alerts, so a broken replay route passes the demo-day checklist. `scripts/ci.sh` also runs `bash -n` on other scripts but not `smoke.sh`.
Fix: in `smoke.sh`, after fetching the first alert, read its `errors[0].session_id`, `t_start`, `t_end` and `resident_id` (same inline python3 JSON parsing the script already uses) and check both replay routes return a non-empty `frames` list; add `bash -n scripts/smoke.sh` to the "repo tooling" block of `ci.sh`. Read only these two files plus the two route handlers in `api.py`.
Acceptance:
- PASS/FAIL lines for both new checks; FAIL (non-zero exit) on 404 or empty frames.
- `scripts/ci.sh` passes.

### T109 — Resident detail: not-found, API-down and no-sessions states
- status: todo
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/ResidentDetail.tsx, web/src/resident/ResidentDetail.test.tsx
- owner: —
- claimed: —
- pr: —
- note: WIP from a session that ended early is on branch task/T109-wip (ResidentDetail.tsx + test): start from it: git switch task/T109-wip && git merge origin/main

What: The resident screen must stay legible when things go wrong: an unknown resident id, the API being unreachable, or a resident with no sessions yet. A nurse should understand each state in 10 s.
Interface: `ResidentDetail` only; reuse the existing `web/src/resident/api.ts` fetch (do not change it) and existing CSS classes/design tokens.
Acceptance:
- 404 → "Resident not found" with a link back to the unit overview.
- network/5xx error → short plain message + a "Try again" button that refetches.
- zero sessions → empty-state copy instead of blank charts (no crash in BaselineChart/HeatCalendar).
- Tests for all three states in ResidentDetail.test.tsx; `scripts/ci.sh` passes.

### T110 — Live task map: step state not conveyed by colour alone
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/live/TaskMap.tsx, web/src/live/TaskMap.test.tsx, web/src/live/TaskMapLegend.tsx, web/src/live/TaskMapLegend.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T07:14Z
- pr: #96

What: The red/amber flashes in the live task map (demo beat 3) are colour-only. Add a text/icon cue and an accessible name per step so the state reads for colour-blind judges and screen readers.
Interface: each `role="listitem"` step gets an accessible name like "Add teabag — missed" / "Pour water — repeated" / "Boil kettle — done"; a visible icon or short label per non-pending state; legend uses the same icons.
Acceptance:
- Tests query steps by accessible name for each state (pending, active, done, omission, repeat/sequence).
- No behaviour change to state transitions; existing tests still pass.
- `scripts/ci.sh` passes.

### T111 — Demo residents: evening-only worsening and motor slowing
- status: done
- class: standard
- priority: 1
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/demo.py, pipeline/tests/test_demo.py
- owner: ian-claude-standard-2
- claimed: 2026-10-17T07:23Z
- pr: #98

What: SPEC §8 wants 5–6 demo residents, one per pattern. The generators for `"evening"` (T086) and `"motor"` (T087) exist but no demo resident uses them. Add two residents to the demo config with pinned seeds.
Interface: two new entries in the resident config list in `demo.py` (`scenario: "evening"` and `scenario: "motor"`, new ids/names/rooms); no API or contract change.
Acceptance:
- pytest in `test_demo.py`: both new residents appear in `demo_residents()`, deterministic across calls; the evening resident's evening (≥16:00) sessions in the last 7 days average ≥3× the errors of its morning ones; the existing four residents keep their current status (the T091 status test still passes unchanged).
- `scripts/ci.sh` and `scripts/e2e.sh` pass.

### T112 — AlertContext: care-record context next to the alert (component only)
- status: done
- class: light
- priority: 2
- kind: feature
- deps: —
- area: web/src/alert/AlertContext.tsx (new), web/src/alert/AlertContext.test.tsx (new)
- owner: ian-claude-light-2
- claimed: 2026-10-17T07:47Z
- pr: #111

What: SPEC §5 Nice to have 5: show care-record context (new meds, temperature, fluids) beside an alert. Build a small component that shows only the records from the 72 h before the alert time, newest first; not wired into AlertView yet.
Interface: `AlertContext({ records: CareRecord[], alertTs: string, windowHours?: number })`. Read only `web/src/resident/types.ts` (CareRecord), `web/src/resident/ContextTimeline.tsx` (copy its formatting; reuse its helpers if exported) and `web/src/ui/EmptyState.tsx`. Empty window → EmptyState "No care-record changes in the last 3 days".
Acceptance:
- vitest: filters to the window, orders newest first, med_change rows are labelled as medication, empty state shown when nothing is in the window.
- `scripts/ci.sh` passes.

### T113 — Pattern scenarios: one replayable scenario per pattern
- status: done
- class: standard
- priority: 1
- kind: test
- deps: T084
- area: tests/scenarios/pattern_*/, tests/scenarios/README.md, pipeline/src/routine_watch/replay.py (expected top-pattern check only), pipeline/tests/test_replay.py
- owner: ian-claude-standard-2
- claimed: 2026-10-17T07:39Z
- pr: #112

What: SPEC §8: at least one scenario per MVP pattern (sudden change, slow drift) with the expected top pattern in `expected.yaml`, plus "no clear pattern" for a flag that matches none.
Interface: optional `top_pattern: <pattern id> | none` key in `expected.yaml`; `scripts/e2e.sh` fails when the scorer's top pattern differs. Scenarios without the key are unaffected.
Acceptance:
- ≥3 new scenarios (`pattern_sudden_change`, `pattern_slow_drift`, `pattern_none`), each with history context in the same format existing flagging scenarios use.
- pytest covers the new key (match, mismatch, absent); `scripts/e2e.sh` passes; README table updated.

### T114 — api.py: one resident lookup helper instead of copy-pasted loops
- status: todo
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: pipeline/src/routine_watch/api.py, pipeline/tests/test_api_residents.py
- owner: —
- claimed: —
- pr: —

What: `get_resident`, `resident_drift` and the replay routes each loop over `demo_residents()` and raise the same 404. Extract `_resident_or_404(resident_id) -> dict` and use it everywhere. No behaviour change.
Interface: private helper in `api.py`; routes and responses unchanged. Read only `api.py` and `pipeline/tests/test_api*.py`.
Acceptance:
- No remaining `for resident in demo_residents()` loops in route bodies.
- New test: every resident-scoped route returns 404 with `{"detail": "resident not found"}` for an unknown id.
- `scripts/ci.sh` passes.

### T115 — Docs: CODEMAP notes for drift endpoint, evidence sources, smoke.sh, feedback causes
- status: claimed
- class: light
- priority: 2
- kind: docs
- deps: —
- area: docs/CODEMAP.md
- owner: ian-claude-light-2
- claimed: 2026-10-17T07:58Z
- pr: —

What: Recent merges (T050 drift endpoint, T107 evidence replays `tea_no_kettle` with a `tea_normal` ghost, T098/T108 `scripts/smoke.sh`, T100 feedback causes) aren't in the CODEMAP notes. Add 1–3 lines each.
Interface: notes only; read the module docstrings of `pipeline/src/routine_watch/{api,evidence,feedback,drift}.py` and the header of `scripts/smoke.sh`. Run `python3 scripts/codemap.py` to regenerate the file list.
Acceptance:
- Each of the four is described where a newcomer would look; no stale claims (e.g. "evidence replays one scenario").
- `scripts/ci.sh` passes.

### T116 — Scenario: pill taken before the water is poured is a sequence error
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/meds_pill_before_water/
- owner: —
- claimed: —
- pr: —

What: The second task has only a normal and an omission scenario. Add a step-level scenario where the pill is taken before the glass is filled, producing exactly one sequence error.
Interface: `steps.jsonl` + `expected.yaml` in the same format as `tests/scenarios/meds_skip_water/`. Read only `pipeline/src/routine_watch/tasks/meds.yaml`, `tests/scenarios/meds_skip_water/*` and `tests/scenarios/tea_sequence_error/*`.
Acceptance:
- `scripts/e2e.sh` passes with the new scenario listed; the error list is exactly one sequence error on the correct step.
- Note in the PR that `tests/scenarios/README.md` needs a row (outside area; the orchestrator will batch README rows).

### T117 — Web mock residents include the evening and motor residents
- status: todo
- class: light
- priority: 2
- kind: feature
- deps: T111
- area: web/src/mock/residents.ts, web/src/mock/residentDetail.ts
- owner: —
- claimed: —
- pr: —

What: The offline web fallback should show the same residents as the API after T111. Add the two new residents (same ids, names, rooms, status) to the web mocks.
Interface: mirror the ids/names from `pipeline/src/routine_watch/demo.py`; keep the existing mock shape.
Acceptance:
- vitest: mock list ids equal the API demo ids (hard-coded list in the test, with a comment pointing at demo.py).
- `scripts/ci.sh` passes.

### T118 — Pattern library page: what each pattern looks for and its source
- status: todo
- class: standard
- priority: 3
- kind: feature
- deps: T084
- area: pipeline/src/routine_watch/api.py (add the route only), pipeline/tests/test_api_patterns.py (new), web/src/patterns/ (new), web/src/App.tsx (one nav entry)
- owner: —
- claimed: —
- pr: —
- source: proposed

What: Rationale: judges (Clarity, responsible design §12) can see every pattern's signals, rule-out checks and source citation, showing it is a cited rules library, not an LLM guess. Read-only screen, separate from the demo path.
Interface: `GET /patterns` → the library as JSON (id, name, signals, time profile, checks, urgency, source); `web/src/patterns/PatternLibrary.tsx` lists them with "consistent with" wording.
Acceptance:
- pytest: route returns every library entry with a non-empty source; vitest: renders each pattern, urgent one visually distinct, no "diagnos" text.
- `scripts/ci.sh` passes.

### T119 — Bug: API sends no CORS headers, so the dashboard silently shows mock data
- status: done
- class: light
- priority: 0
- kind: bug
- deps: —
- area: pipeline/src/routine_watch/api.py (middleware only), pipeline/tests/test_api_cors.py (new)
- owner: ian-claude-standard-2
- claimed: 2026-10-17T07:29Z
- pr: #101
- source: tester

What: With `scripts/dev.sh up` (dashboard :5173, API :8000), every `fetch` from the dashboard to the API fails in the browser with `TypeError: NetworkError` because API responses have no `access-control-allow-origin` header. The web clients catch that and fall back to `web/src/mock/*`, so overview, Mrs. K detail and the alert screen show mock data (e.g. Mr. Chen "watch" vs API "normal"; alert threshold 1.2 vs API 4.09), and "Confirmed" only updates the local mock, so the threshold never visibly changes (SPEC §10 last step). The WebSocket works (not subject to CORS), so the live session is real while everything else is fake.
Repro: `scripts/dev.sh up`; `curl -si -H "Origin: http://localhost:5173" localhost:8000/residents | head -5` → no `access-control-allow-origin`. In the browser on :5173: `fetch('http://localhost:8000/alerts/alert-mrs-k')` → NetworkError while api.log shows 200.
Expected: API answers with CORS headers for the dashboard origin; dashboard shows API data; "Confirmed" lowers the shown threshold (the API already does: 4.09 → 3.88).
Interface: FastAPI `CORSMiddleware`; allowed origins from env `CORS_ORIGINS` (comma-separated, default `http://localhost:5173`); note in the PR that `.env.example` needs the var if outside area.
Acceptance:
- pytest: a GET with `Origin: http://localhost:5173` returns `access-control-allow-origin`; a preflight OPTIONS for `POST /alerts/{id}/feedback` succeeds.
- `scripts/ci.sh` passes.

### T120 — Bug: live task map overflows; the red/amber steps are hidden off to the right
- status: done
- class: light
- priority: 0
- kind: bug
- deps: —
- area: web/src/live/TaskMap.tsx, web/src/live/*.css
- owner: ian-claude
- claimed: 2026-10-17T07:30Z
- pr: #107
- source: tester

What: In a 1920×984 window the task map card is 406 px wide but its content is 1502 px (`overflow-x: auto`), so only "Fill the kettle", "Boil the kettle" and half of "Get a cup" are visible. The steps that turn red/amber in the demo scenario (`tea_skip_teabag_pour_twice`: teabag missed, pour repeated) are off-screen, so "errors flash" (SPEC §10 step 3) can't be seen without scrolling.
Repro: `scripts/dev.sh up`, open http://localhost:5173, wait for the live session to finish, look at the Task map card.
Expected: all 9 tea steps visible in the card at 1920 px without scrolling (wrap into rows or a vertical list), error colours visible.
Acceptance:
- vitest: steps render in a wrapping/vertical layout; existing TaskMap tests still pass.
- `scripts/ci.sh` passes.

### T121 — Bug: demo alert lists placeholder errors ("skipped the task at 0:00" ×4) and grows on every page load
- status: claimed
- class: standard
- priority: 1
- kind: bug
- deps: —
- area: pipeline/src/routine_watch/alerts.py, pipeline/tests/test_alerts*.py
- owner: ian-claude-standard-2
- claimed: 2026-10-17T07:53Z
- pr: —
- source: tester

What: `GET /alerts/alert-mrs-k` builds errors via `_task_errors` with `step_id=None` and fake times 0:00/0:10 in every session, so the summary reads "Flagged for review: 8 errors this session (skipped the task at 0:00, repeated the task at 0:10, skipped the task at 0:00, ...)", and says "this session" while counting across 3–4 sessions. Each dashboard load runs the live session (T081), which appends another `mrs-k-NN` session, so the alert keeps growing during a demo. Currently hidden only because the dashboard is on mock data (T119).
Repro: `scripts/dev.sh up`; load http://localhost:5173 twice; `curl -s localhost:8000/alerts/alert-mrs-k | python3 -m json.tool`.
Expected: alert errors name real steps with plausible timestamps, the summary counts correctly with no repeated clauses, and reloading the page doesn't keep adding sessions to the alert.
Acceptance:
- pytest: demo alert errors all have a non-null `step_id`; summary has no duplicate clauses; running the live session twice leaves at most one live session on the alert.
- `scripts/ci.sh` passes.

### T122 — Bug: live skeleton view stays "Waiting for camera" for the whole demo replay
- status: done
- class: light
- priority: 1
- kind: bug
- deps: —
- area: tests/scenarios/tea_skip_teabag_pour_twice/ (add frames.jsonl)
- owner: ian-claude-light-2
- claimed: 2026-10-17T07:30Z
- pr: #102
- source: tester

What: The dashboard's live session uses scenario `tea_skip_teabag_pour_twice`, which has only `steps.jsonl` (no `frames.jsonl`), so `/ws/live` sends 0 `frame` messages (probe: session_start 1, step 7, step_state 8, error 2, frame 0) and the skeleton panel next to the task map stays empty. SPEC §10 step 3 shows the skeleton next to the task map.
Repro: `scripts/dev.sh up`, open http://localhost:5173, watch the "Skeleton view" card for the whole session.
Expected: a synthetic skeleton/object-box `frames.jsonl` aligned with the step timestamps so the skeleton animates (no raw video). Note in the PR that `tests/scenarios/README.md` needs updating.
Acceptance:
- `scripts/e2e.sh` still passes; a check that `/ws/live?scenario=tea_skip_teabag_pour_twice` emits at least one `frame` message.
- `scripts/ci.sh` passes.

### T123 — Bug: smoke.sh always fails the evidence replay check (alert body is overwritten)
- status: done
- class: light
- priority: 1
- kind: bug
- deps: —
- area: scripts/smoke.sh
- owner: max_API_light
- claimed: 2026-10-17T07:35Z
- pr: #104
- source: tester
- note: Smoke passes against dev stack; GitHub CI passed. Local CI had Windows file lock then unrelated web timeouts; auto-merge enabled.

What: `scripts/smoke.sh` stores the alert JSON in `body` (~line 83), then the dashboard check (~line 92) reuses `body` for the HTML, so the replay block parses HTML and reports "no alert error to derive session/resident/time window from". The routes themselves work (`/sessions/mrs-k-20/replay?t_start=0&t_end=5` and `/residents/mrs-k/normal_replay` return frames).
Repro: `scripts/dev.sh up && scripts/smoke.sh` → `FAIL: GET /sessions/<id>/replay ...`, exit 1.
Expected: keep the alert body in its own variable; smoke passes against a fresh stack.
Acceptance:
- `scripts/smoke.sh` exits 0 against `scripts/dev.sh up`; `scripts/ci.sh` passes.

### T124 — Review: Mrs. K is already flagged before the live session, so demo beat 4 never happens
- status: done
- class: standard
- priority: 0
- kind: bug
- deps: —
- area: pipeline/src/routine_watch/demo.py, pipeline/src/routine_watch/synth/history.py (spike scenario only), pipeline/tests/test_demo.py, pipeline/tests/test_live_flag.py
- source: reviewer
- owner: ian-claude-standard
- claimed: 2026-10-17T07:37Z
- pr: #108

What: SPEC §10 beats 2–4: dashboard shows Mrs. K's normal weeks, then the live tea session is "the second qualifying session" that triggers her flag. Today `demo_residents()` with an empty `session_log` already has `mrs-k` status `flagged` (last scores `… 5.0, 5.0, 5.0`, threshold ≈4.1) and `/alerts` already lists `alert-mrs-k`, so the live session changes nothing visible.
Interface: change the spike seed/scenario so the seeded history has exactly **one** qualifying session (score > threshold) inside `FLAG_WINDOW_H` of `DEMO_NOW` and status `watch`; playing `tests/scenarios/tea_skip_teabag_pour_twice` live as `mrs-k` then makes her `flagged` with an alert. Keep `sudden_change` her top pattern once flagged.
Acceptance:
- pytest: empty log → `mrs-k` status `watch`, no `alert-mrs-k` in `build_alerts`; after one live `tea_skip_teabag_pour_twice` → `flagged`, alert present, `patterns[0].pattern_id == "sudden_change"`.
- `scripts/ci.sh` passes.

### T125 — Review: drift/evening/motor demo residents never leave "normal" (no "watch" for demo beat 6)
- status: in-review
- class: standard
- priority: 0
- kind: bug
- deps: —
- area: pipeline/src/routine_watch/demo.py, pipeline/tests/test_demo.py
- source: reviewer
- owner: ian-claude-standard
- claimed: 2026-10-17T07:48Z
- pr: #117

What: `_status` only returns `watch` when the latest score beats a threshold built from the resident's *whole* history, so a slow drift raises its own bar: `mr-chen` (drift, recent scores 8–9, threshold ≈10.1), `mr-nguyen` (evening) and `mrs-patel` (motor) all show `normal`. SPEC §10 beat 6 needs Mr. D/Chen on `watch` with the slow-drift pattern, and T089's acceptance assumes it.
Interface: in `demo.py`, build the baseline from the earliest sessions only (e.g. first 7 of `DEMO_DAYS`), and also return `watch` when `drift.drift(...)` over daily scores reports `trending` (same daily-mean helper as `api._daily_scores`; move it into `drift.py` rather than copying it). Normal residents must stay `normal`.
Acceptance:
- pytest: `mr-chen` status `watch`; `mrs-ahmed`, `mr-silva` stay `normal`; evening and motor residents are `watch` or `flagged` (pin which).
- `scripts/ci.sh` passes.

### T126 — Review: live-session tests leak into session_log; add a shared reset fixture
- status: done
- class: light
- priority: 1
- kind: test
- deps: —
- area: pipeline/tests/conftest.py (new), pipeline/tests/test_live_flag.py
- source: reviewer
- owner: max_API_light
- claimed: 2026-10-17T07:49Z
- pr: #114
- rating: 4/5 conftest.py already existed with a flagged-resident fixture; otherwise clear

What: `routine_watch.session_log` is process-global and `demo_residents()` reads it. Only `test_live_flag.py` resets it; `test_live.py` and `test_live_camera.py` play sessions via `session_messages` without resetting, so every later test (demo/alerts/api/patterns) sees an extra Mrs. K session and results depend on test order.
Interface: add `pipeline/tests/conftest.py` with an `autouse` fixture calling `session_log.reset()` before and after each test; drop the now-duplicate fixture in `test_live_flag.py`.
Acceptance:
- `cd pipeline && uv run pytest -q -p no:cacheprovider` passes, and passes with `tests/test_live.py` run before `tests/test_demo.py` in one invocation.
- `scripts/ci.sh` passes.

### T127 — Review: CORS_ORIGINS undocumented and ignores dev.sh's DASHBOARD_PORT
- status: done
- class: light
- priority: 1
- kind: bug
- deps: —
- area: .env.example, scripts/dev.sh
- owner: ian-claude-light-2
- claimed: 2026-10-17T07:38Z
- pr: #105

What: T119 (PR #101) added `CORS_ORIGINS` (default `http://localhost:5173`) to `pipeline/src/routine_watch/api.py`, but `.env.example` doesn't document it and `scripts/dev.sh` doesn't set it, so `DASHBOARD_PORT=5174 scripts/dev.sh up` makes the dashboard silently fall back to mock data again.
Interface: in `scripts/dev.sh`, next to the `VITE_API_URL` export, add `export CORS_ORIGINS=${CORS_ORIGINS:-$DASHBOARD_URL,http://127.0.0.1:${DASHBOARD_PORT}}`. In `.env.example` add `CORS_ORIGINS=http://localhost:5173` with a one-line comment (comma-separated dashboard origins the API accepts). Read only those two files and the `_CORS_ORIGINS` block in `api.py`.
Acceptance:
- `bash -n scripts/dev.sh` passes; `.env.example` lists `CORS_ORIGINS`.
- `scripts/ci.sh` passes.

### T128 — Bug: smoke.sh finds no alert since mrs-k is only flagged after her live session
- status: done
- class: light
- priority: 1
- kind: bug
- deps: —
- area: scripts/smoke.sh
- owner: ian-claude-light-2
- claimed: 2026-10-17T07:52Z
- pr: #115
- rating: 5/5 clear

What: Since T124 (#108) a fresh stack has no flagged resident until mrs-k's live session plays, so `GET /alerts` is empty and smoke.sh fails the alert and replay checks. Make smoke.sh play that session first, the same way the demo does. Read only `scripts/smoke.sh` and the `/ws/live` handler at the bottom of `pipeline/src/routine_watch/api.py`.
Interface: before the `/alerts` checks, open `ws://<api>/ws/live?scenario=tea_skip_teabag_pour_twice&speed=1000` with a short inline `python3 -c` using the `websockets` package (already a pipeline dependency; run it with the pipeline venv python if present, else `python3`) and read until the socket closes; report it as `PASS: live session played` / `FAIL: ...`. Keep "never POSTs feedback". Update the header comment.
Acceptance:
- Against `scripts/dev.sh up`, `scripts/smoke.sh` prints PASS for every check, including GET /alerts/<id> and both replay routes; run it twice in a row and it still passes.
- `bash -n scripts/smoke.sh` and `scripts/ci.sh` pass.

### T129 — Feedback "what was it?" cause reaches the API (contract + API + web)
- status: todo
- class: heavy
- priority: 2
- kind: feature
- deps: —
- area: contracts/alert.schema.json, contracts/examples/, pipeline/src/routine_watch/contracts.py, pipeline/src/routine_watch/api.py, pipeline/tests/test_api_alerts.py, web/src/contracts.ts, web/src/alert/api.ts, web/src/alert/api.test.ts, web/src/alert/FeedbackButtons.tsx, web/src/alert/FeedbackButtons.test.tsx
- owner: —
- claimed: —
- pr: —

What: SPEC §5 MVP 8. The "what was it?" picker (T090) and the per-resident cause store (T100) exist, but the contract and `POST /alerts/{id}/feedback` have no `cause`, so the nurse's answer is dropped. Wire it end to end.
Interface: optional `cause` (a pattern_id from `patterns_library`, or `"other"`, or null) on `AlertFeedback` in `contracts/alert.schema.json` + `contracts.py` + `web/src/contracts.ts`; `AlertFeedbackIn.cause` validated against known pattern ids (422 otherwise); API calls the FeedbackStore cause-recording method from T100; web `postFeedback` sends the picked cause. Update every consumer and the example alert.
Acceptance:
- API test: posting `{verdict: "confirmed", cause: "sudden_change"}` returns the alert with `feedback.cause == "sudden_change"` and the store has it for mrs-k; unknown cause → 422; omitting cause still works.
- Web test: picking a cause then confirming sends it in the request body.
- `scripts/ci.sh` passes.

### T130 — Pattern feedback loop: nurse causes re-weight that resident's pattern ranking
- status: todo
- class: heavy
- priority: 3
- kind: feature
- deps: T129
- area: pipeline/src/routine_watch/patterns.py, pipeline/src/routine_watch/alerts.py, pipeline/src/routine_watch/feedback.py, pipeline/tests/test_pattern_feedback.py
- owner: —
- claimed: —
- pr: —

What: SPEC §5 Nice to have 8. Causes a nurse confirmed for a resident nudge that pattern's weight up for her next alerts (and a false alarm on a top pattern nudges it down), bounded so one answer can't flip the ranking alone.
Interface: `FeedbackStore.pattern_weights(resident_id) -> dict[str, float]` (default 1.0, clamped e.g. 0.7–1.3); `score_patterns(..., weights=None)` multiplies confidence before the threshold/sort; `build_alerts` passes the resident's weights. Evidence line notes "weighted by N past nurse answers" when weight ≠ 1.
Acceptance:
- Tests: no feedback → identical ranking to today; two confirmed `slow_drift` causes raise its confidence for that resident only; weights stay within bounds after many answers.
- Wording stays "consistent with"; no "diagnose".
- `scripts/ci.sh` passes.

### T131 — Push alert fires once when a live session flags a resident
- status: todo
- class: standard
- priority: 2
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/live.py, pipeline/tests/test_live_notify.py
- owner: —
- claimed: —
- pr: —

What: SPEC §5 Nice to have 3. `notify.py` (FakeNotifier default, SupabaseNotifier when LIVE_API=1) is built but nothing calls it. When a live session's end flips a resident to flagged, send that alert through `get_notifier()` exactly once.
Interface: in `live.py`, after the session's flag is computed, if the resident was not flagged before and is now, call `get_notifier().notify(<alert dict>)`; injectable notifier for tests. Never a real network call without LIVE_API=1.
Acceptance:
- Test with a fake notifier: playing `tea_skip_teabag_pour_twice` for mrs-k notifies once; playing it again while already flagged does not notify again; a clean `tea_normal` session never notifies.
- `scripts/ci.sh` passes.

### T132 — Web tests: AlertView and PatternList time out under default parallelism
- status: todo
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/alert/AlertView.test.tsx, web/src/alert/PatternList.test.tsx
- owner: —
- claimed: —
- pr: —

What: On a slower machine `npm test` (default workers) timed out in these two files while `--maxWorkers=2` passed (seen on T071). Make them fast and deterministic without changing what they assert. Read only those two test files, their components, and `.tasks/LESSONS.md`.
Interface: test files only. Typical fixes: resolve mocked fetches immediately, prefer one `findBy*` then sync `getBy*` instead of many `waitFor`s, use fake timers where the component waits.
Acceptance:
- `cd web && npx vitest run src/alert --reporter=verbose` shows no single test over 1 s; `npm run lint && npm test && npm run build` passes twice with no flakes.
- Same test count and assertions as before (state the before/after durations in the PR).
