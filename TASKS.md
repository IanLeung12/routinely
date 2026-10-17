# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: 0b00d1e

## Tasks

### T089 — Unit overview shows the top pattern for flagged/watch residents
- status: claimed
- class: standard
- priority: 2
- kind: feature
- deps: T084
- area: pipeline/src/routine_watch/demo.py, pipeline/src/routine_watch/api.py, pipeline/tests/test_api_residents.py, web/src/overview/, web/src/mock/residents.ts
- owner: ian-claude-standard-2
- claimed: 2026-10-17T08:33Z
- pr: —

What: SPEC §9 screen 1 and demo step 6 ("Mr. D on watch, slow drift"): each flagged or watch resident row shows its top pattern name next to the status chip.
Interface: `GET /residents` items gain `top_pattern: {pattern_id, name, urgency} | null` from T084's scorer; `web/src/overview/types.ts` `ResidentSummary.top_pattern`; `UnitOverview` renders it as text (not colour alone); normal residents show nothing.
Acceptance:
- pytest: Mrs. K's `top_pattern.pattern_id == "sudden_change"`, drift resident's is `slow_drift`, normal residents `null`.
- Vitest: row shows pattern text for flagged resident, none for normal.
- `scripts/ci.sh` passes.

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

### T130 — Pattern feedback loop: nurse causes re-weight that resident's pattern ranking
- status: claimed
- class: heavy
- priority: 3
- kind: feature
- deps: T129
- area: pipeline/src/routine_watch/patterns.py, pipeline/src/routine_watch/alerts.py, pipeline/src/routine_watch/feedback.py, pipeline/tests/test_pattern_feedback.py
- owner: ian-claude
- claimed: 2026-10-17T08:32Z
- pr: —

What: SPEC §5 Nice to have 8. Causes a nurse confirmed for a resident nudge that pattern's weight up for her next alerts (and a false alarm on a top pattern nudges it down), bounded so one answer can't flip the ranking alone.
Interface: `FeedbackStore.pattern_weights(resident_id) -> dict[str, float]` (default 1.0, clamped e.g. 0.7–1.3); `score_patterns(..., weights=None)` multiplies confidence before the threshold/sort; `build_alerts` passes the resident's weights. Evidence line notes "weighted by N past nurse answers" when weight ≠ 1.
Acceptance:
- Tests: no feedback → identical ranking to today; two confirmed `slow_drift` causes raise its confidence for that resident only; weights stay within bounds after many answers.
- Wording stays "consistent with"; no "diagnose".
- `scripts/ci.sh` passes.

### T141 — Pattern scenario: executive pattern (perseveration with steps still in order)
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/pattern_executive/
- owner: ian-claude-standard
- claimed: 2026-10-17T08:10Z
- pr: #132
- rating: 5/5 clear

What: T113 added replayable scenarios for sudden_change and slow_drift only. Add one for SPEC §7.5's `executive_pattern` so e2e proves the library ranks it top when the resident repeats steps (perseveration) while the order stays intact.
Interface: `tests/scenarios/pattern_executive/{steps.jsonl,expected.yaml}` in the same format as `tests/scenarios/pattern_slow_drift/` (incl. `history:` and `top_pattern: executive_pattern`). Read the `executive_pattern` entry in `pipeline/src/routine_watch/patterns_library.py` for what it needs. Don't change pipeline code; if the scenario can't reach the pattern without code changes, set the task blocked with the reason.
Acceptance:
- `scripts/e2e.sh` passes with the new scenario included and `top_pattern: executive_pattern`.
- Header comment in expected.yaml explains the shape in 2-4 lines.

### T142 — Pattern scenario: evening-only worsening
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/pattern_evening_worsening/
- owner: ian-claude-standard-2
- claimed: 2026-10-17T08:17Z
- pr: #136
- rating: 5/5 clear

What: T113 added replayable scenarios for sudden_change and slow_drift only. Add one for SPEC §7.5's `evening_worsening` so e2e proves the library ranks it top when errors cluster in evening sessions while mornings stay clean.
Interface: `tests/scenarios/pattern_evening_worsening/{steps.jsonl,expected.yaml}` in the same format as `tests/scenarios/pattern_slow_drift/` (incl. `history:` and `top_pattern: evening_worsening`). Read the `evening_worsening` entry in `pipeline/src/routine_watch/patterns_library.py` (it requires `evening_concentrated`) and how `extract_features` in `patterns.py` derives that from `hours_ago`. Don't change pipeline code; if the scenario format can't express evening sessions, set the task blocked with the reason.
Acceptance:
- `scripts/e2e.sh` passes with the new scenario and `top_pattern: evening_worsening`.
- Header comment in expected.yaml explains the shape in 2-4 lines.

### T143 — Pattern scenario: motor slowing after a sedating medication
- status: todo
- class: standard
- priority: 2
- kind: test
- deps: T157
- area: tests/scenarios/pattern_motor_slowing/
- owner: —
- claimed: —
- pr: —
- note: orch: was blocked because replay.py never passes duration_s, so durations_up is unreachable in scenarios. T157 adds scenario durations; after it this is data-only (use the new duration fields).

What: Same as T142 for SPEC §7.5's `motor_slowing` pattern: slower steps and hesitation without new sequence errors.
Interface: `tests/scenarios/pattern_motor_slowing/{steps.jsonl,expected.yaml}` in the format of `tests/scenarios/pattern_slow_drift/`, `top_pattern: motor_slowing`. Read the `motor_slowing` entry in `pipeline/src/routine_watch/patterns_library.py` for its signals. Don't change pipeline code; if unreachable without code changes, set blocked with the reason.
Acceptance:
- `scripts/e2e.sh` passes with the new scenario and `top_pattern: motor_slowing`.
- Header comment in expected.yaml explains the shape in 2-4 lines.

### T144 — API: POST /demo/reset puts the demo back to its seeded history
- status: todo
- class: standard
- priority: 2
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/api.py, pipeline/tests/test_api_demo_reset.py (new), scripts/smoke.sh
- source: proposed
- owner: —
- claimed: —
- pr: —

What: Demo robustness (SPEC §10, §13): after a rehearsal, Mrs. K stays flagged from the live session, so the next run of demo beat 4 never happens unless the server restarts. One endpoint resets recorded live sessions and feedback so the demo can be rerun on stage in a second.
Interface: `POST /demo/reset` → `{"ok": true}`; calls `session_log.reset()` and the equivalent reset in `routine_watch.feedback` (add a `reset()` there only if missing, in this PR). Only enabled when `OFFLINE_MODE` or a new `DEMO_RESET=1` env is set, else 404; document `DEMO_RESET` in `.env.example`.
Acceptance:
- Test: record a live session for mrs-k (flagged), POST /demo/reset, `/residents` shows her back at her seeded status; with the env unset the route is 404.
- smoke.sh hits the route once; `scripts/ci.sh` passes.

### T145 — Live session "Flagged for review" banner links straight to the alert
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/live/LiveSession.tsx, web/src/live/LiveSession.test.tsx, web/src/App.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T08:17Z
- pr: #133
- rating: 5/5 clear

What: Demo beats 4→5 (SPEC §10): when the live session flags, the nurse should get to the evidence in one tap. The banner at `LiveSession.tsx` ~line 105 says "Flagged for review" but has no way to open the alert, even though `ended.alert_id` is there.
Interface: add optional prop `onOpenAlert?: (alertId: string) => void` to `LiveSessionProps`; when `ended.flag && ended.alert_id && onOpenAlert`, render a `<button>` "Open alert" inside the banner calling it. In `App.tsx` pass `onOpenAlert={setOpenAlert}`. Read only those two files and `useLiveSession.ts` (for the `ended` type).
Acceptance:
- LiveSession test: flagged session_end with alert_id shows the button and clicking calls onOpenAlert with the id; clear session shows no button.
- `cd web && npm test -- --run` passes.

### T146 — Docs: CODEMAP notes for live push alerts and placeholder alert errors
- status: done
- class: light
- priority: 3
- kind: docs
- deps: —
- area: docs/CODEMAP.md
- owner: ian-claude-light-2
- claimed: 2026-10-17T08:26Z
- pr: #138
- rating: 5/5 clear

What: T131 made a live session send one push alert when it flips a resident to flagged (`live.py` `_resident_flagged`, `notify.get_notifier`), and T121 made `alerts.py` invent plausible step/time placeholders from error counts (`_task_errors`, `_distinct_clauses`). Neither is in docs/CODEMAP.md's notes. Also add notes for T062's shift handoff (`handoff.py` `build_handoff`, `GET /handoff`, `web/src/handoff/`) and T103's `web/src/about/MonitoringToggle.tsx` (component only, not wired yet).
Interface: read `pipeline/src/routine_watch/live.py` (session_messages docstring, `_resident_flagged`), `notify.py` (`get_notifier`), `alerts.py` (`_task_errors`, `_distinct_clauses`) and add 2-4 lines of notes each under the existing pipeline section. Notes only; the file list is generated.
Acceptance:
- `python3 scripts/codemap.py --check` (if it exists) and `scripts/ci.sh` pass.

### T147 — Test: every shippable pattern has a replayable scenario
- status: todo
- class: light
- priority: 3
- kind: test
- deps: T141, T142, T143
- area: pipeline/tests/test_pattern_scenarios_cover_library.py (new)
- owner: —
- claimed: —
- pr: —

What: Guard SPEC §8 ("at least one replayable scenario per pattern") so a new pattern can't ship without one.
Interface: read `pipeline/src/routine_watch/patterns_library.py` (the list of patterns) and `tests/scenarios/*/expected.yaml`. Test collects every `top_pattern:` value from scenarios and asserts it covers every library `pattern_id` except `one_sided_change` (SPEC keeps it out of the demo).
Acceptance:
- `cd pipeline && python -m pytest tests/test_pattern_scenarios_cover_library.py` passes; `scripts/ci.sh` passes.

### T148 — monitoring.py: in-memory per-room monitoring on/paused store
- status: done
- class: light
- priority: 3
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/monitoring.py (new), pipeline/tests/test_monitoring.py (new)
- source: proposed
- owner: ian-claude-standard
- claimed: 2026-10-17T08:29Z
- pr: #143
- rating: 5/5 clear

What: Backend half of the per-room pause switch (SPEC §12 "monitoring can be turned off per room"; UI component landed in T103). Pure module, no API wiring yet. Read only `pipeline/src/routine_watch/feedback.py` (style of an in-memory store).
Interface: `class MonitoringStore` with `is_on(room: str) -> bool` (default True for unknown rooms), `set(room: str, on: bool) -> None`, `paused_rooms() -> list[str]` (sorted), `reset() -> None`. Module-level `get_monitoring_store() -> MonitoringStore` returning one shared instance.
Acceptance:
- tests cover default-on, pause then resume, sorted `paused_rooms()`, `reset()`.
- `cd pipeline && python -m pytest tests/test_monitoring.py` passes; `scripts/ci.sh` passes.

### T149 — API: GET /monitoring and PUT /rooms/{room}/monitoring
- status: todo
- class: standard
- priority: 3
- kind: feature
- deps: T148
- area: pipeline/src/routine_watch/api.py, pipeline/tests/test_api_monitoring.py (new)
- source: proposed
- owner: —
- claimed: —
- pr: —

What: Expose the T148 store so the dashboard's pause switch is real. While a room is paused, `/ws/live` for a scenario whose resident is in that room sends one `{"type": "paused", "room": ...}` message and closes instead of streaming frames (no camera data processed).
Interface: `GET /monitoring` → `{"paused_rooms": [...]}`; `PUT /rooms/{room}/monitoring` body `{"on": bool}` → `{"room": str, "on": bool}`; uses `monitoring.get_monitoring_store()`. Room→resident comes from `demo.demo_residents()`; unknown room → 404.
Acceptance:
- tests: default empty, pause/resume round trip, 404 for unknown room, paused live session gets the `paused` message and no frames (TestClient websocket); store reset between tests.
- `scripts/ci.sh` passes.

### T150 — Resident detail: show the room monitoring switch
- status: done
- class: light
- priority: 3
- kind: feature
- deps: —
- area: web/src/resident/ResidentDetail.tsx, web/src/resident/ResidentDetail.test.tsx
- source: proposed
- owner: ian-claude-light-2
- claimed: 2026-10-17T08:29Z
- pr: #142
- rating: 5/5 clear

What: Put T103's `MonitoringToggle` next to "Room {resident.room}" in the resident detail header so judges see the privacy control in the demo. Local `useState(true)` only for now (API wiring after T149). Read only `web/src/resident/ResidentDetail.tsx`, its test and `web/src/about/MonitoringToggle.tsx`.
Interface: `<MonitoringToggle room={resident.room} on={monitoring} onChange={setMonitoring} />`.
Acceptance:
- test: the switch "Monitoring in room <room>" renders On; clicking shows "Paused" and the "No camera data is processed while paused." note.
- `cd web && npx vitest run src/resident` passes; `scripts/ci.sh` passes.

### T151 — Shift handoff: "Copy summary" button for the shift report
- status: done
- class: light
- priority: 3
- kind: feature
- deps: —
- area: web/src/handoff/Handoff.tsx, web/src/handoff/Handoff.test.tsx
- source: proposed
- owner: max_API_light
- claimed: 2026-10-17T08:30Z
- pr: #144
- rating: 4/5 Room is requested but absent from Handoff data; otherwise clear

What: Nurses paste handoff notes into their shift report; one tap copies the handoff as plain text. Read only `web/src/handoff/Handoff.tsx`, `types.ts`, `mockHandoff.ts`, its test and `web/src/ui/Button.tsx`.
Interface: `export function handoffText(h: Handoff): string` (summary line, then one line per resident: name, room, flagged sessions, unreviewed alerts, trend) in `Handoff.tsx`; a secondary `Button` "Copy summary" calling `navigator.clipboard.writeText(handoffText(...))`, then showing "Copied" (role=status) for 2 s; if clipboard is unavailable show "Copy not available" instead of throwing.
Acceptance:
- tests: `handoffText(mockHandoff)` contains every resident name and the summary and no "diagnos"; clicking calls a mocked `navigator.clipboard.writeText` and shows "Copied"; missing clipboard shows the fallback.
- `cd web && npx vitest run src/handoff` passes; `scripts/ci.sh` passes.

### T152 — Shift handoff rows open the resident's alert
- status: todo
- class: standard
- priority: 3
- kind: feature
- deps: T151
- area: web/src/handoff/Handoff.tsx, web/src/handoff/Handoff.test.tsx, web/src/App.tsx, web/src/App.test.tsx
- source: proposed
- owner: —
- claimed: —
- pr: —

What: From the handoff, the incoming nurse should reach the evidence in one tap. Rows with an unreviewed alert get an "Open alert" button that goes to the alert screen. Check `pipeline/src/routine_watch/handoff.py` for whether rows carry alert ids; if not, use the first matching alert from `fetchAlerts()` by resident id (don't change the API here; note it in the PR).
Interface: `Handoff({ onBack, onOpenAlert }: { onBack: () => void; onOpenAlert?: (alertId: string) => void })`; App passes `id => { setOpenHandoff(false); setOpenAlert(id) }`.
Acceptance:
- tests: button only on rows with unreviewed alerts; clicking calls `onOpenAlert` with the right id; App test: handoff → Open alert shows the alert view.
- `cd web && npx vitest run` passes; `scripts/ci.sh` passes.

### T153 — Docs: demo runbook (docs/DEMO.md)
- status: done
- class: light
- priority: 2
- kind: docs
- deps: —
- area: docs/DEMO.md (new)
- owner: ian-claude-standard-2
- claimed: 2026-10-17T08:29Z
- pr: #141
- rating: 5/5 clear

What: A one-page runbook for whoever drives the 3-minute demo: setup, the click path for each beat, and the fallback. Read only SPEC.md §10, `scripts/dev.sh`, `scripts/smoke.sh`, `tests/scenarios/README.md` and `web/src/App.tsx`.
Interface: sections "Before you start" (exact commands, env such as OFFLINE_MODE), "Click path" (one bullet per SPEC §10 beat: which screen, which button, what the audience should see), "If something fails" (offline replay of `tea_skip_teabag_pour_twice`, no Wi-Fi, how to restart), "Reset between runs". Describe only what exists on main; say "flags a change for review", never "diagnoses".
Acceptance:
- every command in the file exists in `scripts/` or `web/package.json`; `scripts/ci.sh` passes.

### T154 — Bug: evidence replay is empty for the demo alert (no skeleton, no ghost)
- status: done
- class: standard
- priority: 0
- kind: bug
- deps: —
- area: pipeline/src/routine_watch/evidence.py, pipeline/tests/test_evidence.py
- source: tester
- owner: ian-claude-standard
- claimed: 2026-10-17T08:35Z
- pr: #147
- rating: 5/5 clear

What: The alert's evidence view shows "No replay available / No skeleton data" for every error. `GET /sessions/mrs-k-22/replay?t_start=51.1&t_end=56.1` and `GET /residents/mrs-k/normal_replay?...` both return `"frames": []`. Cause: `evidence.py` windows the stand-in scenarios `tea_no_kettle` (frames t=0–12 s) and `tea_normal` (t=0–28 s), but since T121 the alert's error windows sit at 33–107 s, so the clip is empty. `scripts/smoke.sh` fails the same 2 checks.
Interface: `replay_frames` / `normal_replay_frames` keep their signatures; they must return frames for any window inside a known session (e.g. map the requested window onto the stand-in recording, such as modulo its length or centred on it, and keep the returned `t` values in the requested window).
Repro: `OFFLINE_MODE=true scripts/dev.sh up && scripts/smoke.sh` → `FAIL: GET /sessions/mrs-k-22/replay: no frames in response` and the same for `normal_replay`; in the dashboard, play the live session → Open alert → click any error → Evidence is empty.
Acceptance:
- tests: windows past the stand-in length (e.g. t_start=102.1, t_end=107.1) return non-empty frames for both endpoints.
- `scripts/smoke.sh` against `scripts/dev.sh up` passes all checks; `scripts/ci.sh` passes.

### T155 — Bug: alert opened after the live session shows other errors than the live session made
- status: todo
- class: heavy
- priority: 0
- kind: bug
- deps: —
- area: pipeline/src/routine_watch/demo.py, pipeline/src/routine_watch/alerts.py, pipeline/src/routine_watch/session_log.py, pipeline/tests/
- source: tester
- owner: —
- claimed: —
- pr: —

What: On stage the live session (default demo scenario) flags "skipped Put the teabag in the cup · 1:10" and "repeated Pour the water · 1:30". Clicking "Open alert" then shows `alert-mrs-k` with errors "skipped fill kettle 0:51, repeated boil 1:42, skipped fill kettle 0:33, repeated boil 1:06" (sessions mrs-k-22, mrs-k-23): the recorded live session's score is merged into Mrs. K's history, but its actual errors are not; the alert's errors for that session are synthetic. The summary also says "4 errors this session" for errors spread over two sessions.
Interface: the session recorded by `routine_watch.live` (via `session_log`) must carry its real `ErrorEvent`s into the resident's newest session, so `build_alerts` lists them (with their real step ids and times) for that session; the summary should count errors per session or say "across 2 sessions".
Repro: `OFFLINE_MODE=true scripts/dev.sh up`, open http://localhost:5173, wait ~90 s for the live session to finish, click "Open alert"; compare the alert's Errors list with the live session's Errors list. Or `curl localhost:8000/alerts/alert-mrs-k` after the live session.
Acceptance:
- test: after playing the demo live scenario through the pipeline, `/alerts/alert-mrs-k` contains its omission of `add_teabag` and perseveration of `pour` with the live session's session_id.
- summary wording no longer says "this session" for multi-session errors; `scripts/ci.sh` and `scripts/e2e.sh` pass.

### T156 — Bug: overview and Alerts list don't update when the live session flags Mrs. K
- status: todo
- class: standard
- priority: 1
- kind: bug
- deps: —
- area: web/src/App.tsx, web/src/App.test.tsx, web/src/overview/UnitOverview.tsx, web/src/overview/UnitOverview.test.tsx
- source: tester
- owner: —
- claimed: —
- pr: —

What: After the live session ends with a flag (the "Open alert" button appears and `/alerts` now returns `alert-mrs-k`), the unit overview still shows Mrs. K as "Watch", the status line still says "4 on watch · 2 normal", and the Alerts list stays empty until a page reload. The demo beat "alert appears after the second bad session" only shows via the banner button.
Interface: when the live stream reports `session_end` (or a flag), App refetches `fetchAlerts()` and the overview refetches `fetchResidents()` (e.g. a `refreshKey` prop bumped by App).
Repro: `OFFLINE_MODE=true scripts/dev.sh up`, open http://localhost:5173, wait for the live session to finish with a flag; Mrs. K chip and Alerts list don't change.
Acceptance:
- test: a mocked live session ending with a flag triggers a second fetch of residents and alerts and the Flagged chip / alert row render.
- `cd web && npx vitest run` and `scripts/ci.sh` pass.

### T157 — replay.py: scenarios can give sessions a duration so motor_slowing is reachable
- status: todo
- class: standard
- priority: 1
- kind: test
- deps: —
- area: pipeline/src/routine_watch/replay.py, pipeline/tests/test_replay_durations.py (new)
- owner: —
- claimed: —
- pr: —

What: `motor_slowing` needs `durations_up`, but `HistorySession` has no duration and `top_pattern_of` never sets `duration_s` on the history or current-session dicts, so `duration_ratio` is always None in scenario replay (found by T143). Add an optional duration so a scenario can express "slower than usual".
Interface: `HistorySession.duration_s: float | None = Field(default=None, gt=0)`; `Expected.duration_s: float | None = None` for the replayed session (or derive it from the last step timestamp in steps.jsonl if simpler; document which). `top_pattern_of` passes `duration_s` into the session dicts `patterns.py` already reads (around patterns.py:695). Unset durations behave exactly as today.
Acceptance:
- New test: ~10 history sessions at 300 s plus a current session at 450 s with no new sequence errors → `duration_ratio` ≈ 1.5 and `durations_up` present; same inputs without durations → `duration_ratio is None`.
- Every existing scenario still passes: `scripts/e2e.sh` and `scripts/ci.sh` green.
- Docstrings of `HistorySession`/`Expected` say how to write a duration.

### T158 — Docs: CODEMAP note for the "what was it?" cause path
- status: done
- class: light
- priority: 2
- kind: docs
- deps: —
- area: docs/CODEMAP.md
- owner: max_API_light
- claimed: 2026-10-17T08:35Z
- pr: #145
- rating: 5/5 clear

What: T129 (PR #140) carried the optional feedback cause from the alert screen to the API, but CODEMAP has no note on it. Add 2-4 lines to the notes only (the file list is generated).
Interface: Read only `docs/CODEMAP.md`, `web/src/alert/FeedbackButtons.tsx` (top 30 lines) and `pipeline/src/routine_watch/api.py` lines 50-180. Describe: FeedbackButtons offers the alert's patterns + "other" once confirmed → `POST /alerts/{id}/feedback` with `cause` → validated against `KNOWN_CAUSES` (pattern ids + "other", else 422) → `FeedbackStore.record(..., cause=)`.
Acceptance:
- Note sits next to the existing alert/feedback notes; no other file changed.
- `scripts/ci.sh` passes.

### T159 — Resident detail: real empty states for sessions and heat calendar
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/SessionList.tsx, web/src/resident/SessionList.test.tsx, web/src/resident/HeatCalendar.tsx, web/src/resident/HeatCalendar.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T08:37Z
- pr: #146
- rating: 5/5 clear

What: `SessionList` renders a bare `<p className="muted">` when empty and `HeatCalendar` returns `null` (the section just vanishes). Use the shared `EmptyState` so a new resident's page explains itself.
Interface: Read only those four files plus `web/src/ui/EmptyState.tsx` and `web/src/ui/README.md`. SessionList empty → `<EmptyState message="No sessions recorded yet." />`. HeatCalendar empty → `<EmptyState message="No sessions yet, so nothing to show on the calendar." />`.
Acceptance:
- One test per component renders it with an empty list and finds the message.
- `cd web && npx vitest run src/resident` and `scripts/ci.sh` pass.

### T160 — Unit overview: empty state when the unit has no residents
- status: todo
- class: light
- priority: 3
- kind: improvement
- deps: —
- area: web/src/overview/UnitOverview.tsx, web/src/overview/UnitOverview.test.tsx
- owner: —
- claimed: —
- pr: —

What: `UnitOverview` handles loading but renders an empty list when the API returns no residents. Show `EmptyState` with "No residents on this unit yet." (same wording as `web/src/handoff/Handoff.tsx`).
Interface: Read only the two files above and `web/src/ui/EmptyState.tsx`.
Acceptance:
- Test: mocked fetch returns `[]` → message visible, no list rendered.
- `cd web && npx vitest run src/overview` and `scripts/ci.sh` pass.

### T161 — Live screen: choose the tea or the medication session
- status: todo
- class: standard
- priority: 2
- kind: feature
- deps: —
- area: web/src/live/LiveScreen.tsx (new), web/src/live/LiveScreen.test.tsx (new), web/src/App.tsx
- owner: —
- claimed: —
- pr: —

What: SPEC §5 Nice to have 4 (a second task) exists in the pipeline (`tests/scenarios/meds_*`) but App hard-codes `tea_skip_teabag_pour_twice`, so judges never see it generalise. Add a two-option switch above the live session.
Interface: `LiveScreen({ onOpenAlert })` renders a segmented control ("Making tea" → `tea_skip_teabag_pour_twice`, "Medication with water" → `meds_skip_water`, default tea) and `<LiveSession scenario=… key=… />`. App.tsx swaps its `<LiveSession …/>` for `<LiveScreen …/>`, nothing else. Use `web/src/ui/Button.tsx`; `aria-pressed` on the active option.
Acceptance:
- Test: default renders the tea scenario; clicking "Medication with water" switches the scenario (mock `LiveSession`).
- Demo path unchanged by default. `scripts/ci.sh` passes.

### T162 — Test: live websocket path finds the same errors and flag as scenario replay
- status: todo
- class: standard
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_live_matches_replay.py (new)
- owner: —
- claimed: —
- pr: —

What: The SPEC §10 fallback plays recorded scenarios through `live.session_messages`, while `scripts/e2e.sh` checks them through `replay.py`. Nothing asserts the two agree, so the demo could show different errors from what CI tested.
Interface: For each `tests/scenarios/*/` playable live, run `session_messages(scenario_path(name), speed=<very fast>)`, collect error messages and the final flag message, compare with `expected.yaml` (error type/step multiset, `flag`). Read only `pipeline/src/routine_watch/live.py` and `replay.py`. Scenarios that legitimately can't play live get an explicit skip with a reason.
Acceptance:
- Parametrised per scenario, < 20 s total, no network.
- A real mismatch → don't fix pipeline code here; xfail with a reason and list it in the PR so the orchestrator files a bug.
- `scripts/ci.sh` passes.

### T163 — Docs: web/src/ui/README.md lists every shared component
- status: claimed
- class: light
- priority: 3
- kind: docs
- deps: —
- area: web/src/ui/README.md
- owner: ian-claude-light-2
- claimed: 2026-10-17T08:41Z
- pr: —

What: The UI kit grew (DemoBanner, EmptyState, ErrorState, Loading, SectionHeader, StatusChip, errorTypes) and the README is where workers look before writing a new component. List each with one line on when to use it and its props.
Interface: Read only `web/src/ui/README.md` and the non-test `web/src/ui/*.tsx`/`*.ts` files.
Acceptance:
- Every non-test file in `web/src/ui/` appears in the README; no code changes.
- `scripts/ci.sh` passes.

### T164 — Guided demo tour behind ?tour=1
- status: todo
- class: standard
- priority: 3
- kind: feature
- source: proposed
- deps: —
- area: web/src/tour/ (new), web/src/App.tsx
- owner: —
- claimed: —
- pr: —

What: Rationale: judges skim; a 7-step tour following SPEC §10 (baseline → live → alert → why → not just delirium → privacy) makes Clarity obvious and doubles as a presenter cue card. Off unless the URL has `?tour=1`, so it can't touch the demo path.
Interface: `web/src/tour/Tour.tsx` renders a small fixed card (title, body, Back/Next/Close, "n of 7") from a `web/src/tour/steps.ts` array of `{ title, body }`; plain-language copy using "flags a change for review" / "consistent with", never "diagnose". App.tsx mounts `<Tour />` only when `new URLSearchParams(location.search).has('tour')`. No navigation automation.
Acceptance:
- Tests: hidden without the param; with it, Next/Back move through steps and Close hides it; copy contains no "diagnos".
- `scripts/ci.sh` passes.

### T165 — Test: pattern ids are safe feedback causes
- status: todo
- class: light
- priority: 3
- kind: test
- deps: —
- area: pipeline/tests/test_feedback_cause_ids.py (new)
- owner: —
- claimed: —
- pr: —

What: Since T129 a feedback `cause` is any pattern id or "other". Guard against a future pattern colliding with "other" or using an id the web can't round-trip.
Interface: Read only `pipeline/src/routine_watch/patterns_library.py` and `pipeline/src/routine_watch/api.py` lines 50-90. Assert ids in `BY_ID` are unique and match `^[a-z][a-z0-9_]*$`, none equals `api.OTHER_CAUSE`, and `api.KNOWN_CAUSES == set(BY_ID) | {"other"}`.
Acceptance:
- `cd pipeline && python -m pytest tests/test_feedback_cause_ids.py` and `scripts/ci.sh` pass.

### T166 — Review: handoff summary uses old "the task" placeholder errors and a unit-wide baseline
- status: todo
- class: standard
- priority: 1
- kind: bug
- source: reviewer
- deps: —
- area: pipeline/src/routine_watch/handoff.py, pipeline/src/routine_watch/alerts.py, pipeline/tests/test_handoff.py
- owner: —
- claimed: —
- pr: —

What: `handoff._explainer_errors` re-implements the placeholder-error synthesis that T121 replaced in `alerts._task_errors` (still `step_id="the task"`, t=0,10,20…), so the handoff sentence reads "… at the task, 0:00". `_summary` also compares the latest flagged session against `_unit_error_rate` (all residents mixed) instead of that resident's own baseline (SPEC §7: own history only), and doesn't say whose session it is.
Interface: In `handoff.py` drop `_UNKNOWN_STEP`/`_ERROR_SPACING_S`/`_explainer_errors`; build errors via `alerts._task_errors(session_id, session)` + `alerts._distinct_clauses` (make them public, e.g. `task_errors`/`distinct_clauses`, no other behaviour change). Baseline = that resident's own `baseline` (mean/days); prefix the context with the resident's name. Read only `handoff.py` and `alerts.py` lines 60-170.
Acceptance:
- test: handoff summary contains no "the task" and names a real step id; baseline numbers equal the flagged resident's own baseline.
- `scripts/ci.sh` passes.

### T167 — Review: nurse feedback tunes the threshold in /handoff and alert payload but not /residents status or /alerts
- status: todo
- class: standard
- priority: 1
- kind: bug
- source: reviewer
- deps: —
- area: pipeline/src/routine_watch/api.py, pipeline/tests/test_api_feedback.py
- owner: —
- claimed: —
- pr: —

What: `handoff.build_handoff` and `api._alert_payload` apply `_feedback_store.threshold(...)`, but `list_residents`/`get_resident` status and `list_alerts` use the raw `baseline.threshold` from `demo_residents()`. After a nurse taps "not concerning", handoff says 0 flags while the overview still shows Flagged, which contradicts itself on stage.
Interface: one helper in `api.py` (e.g. `_tuned(resident) -> dict`) that recomputes status against the feedback-tuned threshold, reusing `demo`'s flag rule rather than duplicating it (expose a small `demo.status_for(resident, threshold)` if needed); use it in the residents and alerts routes. Read only `api.py`, `demo.py` lines 50-80, `feedback.py`.
Acceptance:
- test: post `not_concerning` feedback until the tuned threshold exceeds the latest score → `/residents` status and `/handoff` flags agree.
- `scripts/ci.sh` passes.

### T168 — Review: live push alert text uses the raw resident id ("mrs-k")
- status: claimed
- class: light
- priority: 2
- kind: bug
- source: reviewer
- deps: —
- area: pipeline/src/routine_watch/live.py, pipeline/tests/test_live_notify.py
- owner: max_API_light
- claimed: 2026-10-17T08:40Z
- pr: —

What: The push sent in `live.session_messages` says "A session just flagged a change for mrs-k to review." A nurse sees the slug, not the name. Have `_resident_flagged` look the resident up once (one `demo_residents()` call) and use `resident["name"]` in the summary.
Interface: Read only `live.py` lines 250-290 and `tests/test_live_notify.py`. Keep `alert_id` = `f"alert-{resident_id}"` (matches `alerts.py`).
Acceptance:
- test asserts the summary contains the resident's display name and not the id.
- `scripts/ci.sh` passes.
