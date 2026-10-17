# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: a13d35a

## Tasks

### T133 — tasks.py: stop reading fields at the task body
- status: done
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
- status: done
- class: heavy
- priority: 3
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/handoff.py, pipeline/src/routine_watch/api.py (add the route only), pipeline/tests/test_handoff.py, web/src/handoff/, web/src/App.tsx (one nav entry)
- owner: ian-claude
- claimed: 2026-10-17T07:47Z
- pr: #129
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
- status: claimed
- class: light
- priority: 3
- kind: feature
- deps: —
- area: web/src/about/MonitoringToggle.tsx (new), web/src/about/MonitoringToggle.test.tsx (new)
- source: proposed
- owner: max_API_light
- claimed: 2026-10-17T08:15Z
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
- status: done
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
- status: claimed
- class: heavy
- priority: 2
- kind: feature
- deps: —
- area: contracts/alert.schema.json, contracts/examples/, pipeline/src/routine_watch/contracts.py, pipeline/src/routine_watch/api.py, pipeline/tests/test_api_alerts.py, web/src/contracts.ts, web/src/alert/api.ts, web/src/alert/api.test.ts, web/src/alert/FeedbackButtons.tsx, web/src/alert/FeedbackButtons.test.tsx
- owner: ian-claude
- claimed: 2026-10-17T08:17Z
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
- status: done
- class: standard
- priority: 2
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/live.py, pipeline/tests/test_live_notify.py
- owner: ian-claude-standard
- claimed: 2026-10-17T08:04Z
- pr: #124
- rating: 5/5 clear

What: SPEC §5 Nice to have 3. `notify.py` (FakeNotifier default, SupabaseNotifier when LIVE_API=1) is built but nothing calls it. When a live session's end flips a resident to flagged, send that alert through `get_notifier()` exactly once.
Interface: in `live.py`, after the session's flag is computed, if the resident was not flagged before and is now, call `get_notifier().notify(<alert dict>)`; injectable notifier for tests. Never a real network call without LIVE_API=1.
Acceptance:
- Test with a fake notifier: playing `tea_skip_teabag_pour_twice` for mrs-k notifies once; playing it again while already flagged does not notify again; a clean `tea_normal` session never notifies.
- `scripts/ci.sh` passes.

### T132 — Web tests: AlertView and PatternList time out under default parallelism
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/alert/AlertView.test.tsx, web/src/alert/PatternList.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T08:05Z
- pr: —
- note: orch: closed as not reproducible (246/246 pass at default parallelism); E1 lets workers push past unrelated local test timeouts

What: On a slower machine `npm test` (default workers) timed out in these two files while `--maxWorkers=2` passed (seen on T071). Make them fast and deterministic without changing what they assert. Read only those two test files, their components, and `.tasks/LESSONS.md`.
Interface: test files only. Typical fixes: resolve mocked fetches immediately, prefer one `findBy*` then sync `getBy*` instead of many `waitFor`s, use fake timers where the component waits.
Acceptance:
- `cd web && npx vitest run src/alert --reporter=verbose` shows no single test over 1 s; `npm run lint && npm test && npm run build` passes twice with no flakes.
- Same test count and assertions as before (state the before/after durations in the PR).

### T134 — Unit tests for drift.daily_scores
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_drift.py
- owner: ian-claude-light-2
- claimed: 2026-10-17T08:07Z
- pr: #126
- rating: 5/5 clear

What: PR #117 (T125) moved `daily_scores` from `api.py` into `pipeline/src/routine_watch/drift.py`; it now feeds both the drift card and the demo "watch" status but has no direct tests. Read only `pipeline/src/routine_watch/drift.py` and `pipeline/tests/test_drift.py`.
Interface: new tests in `pipeline/tests/test_drift.py` only; no source changes.
Acceptance:
- Tests cover: several sessions on one day are averaged into one point; output is sorted by date even when input is not; empty input gives `[]`; timestamps with a `+00:00` offset parse.
- `scripts/ci.sh` passes.

### T135 — demo.py: pull the "worth watching" status out of demo_residents()
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: pipeline/src/routine_watch/demo.py, pipeline/tests/test_demo.py
- owner: max_API_light
- claimed: 2026-10-17T08:10Z
- pr: #128
- rating: 5/5 clear

What: `demo_residents()` grew an inline ~25-line block computing `watch` (early-history cutoff, score points, duration points). Move it into one helper `_watch(history, sessions, scores) -> bool` so the loop body reads as baseline → flag → watch → status. Behaviour must not change. Read only `pipeline/src/routine_watch/demo.py` and `pipeline/tests/test_demo.py`.
Interface: private helper in `demo.py`; `demo_residents()` output identical.
Acceptance:
- A test asserts each demo resident's `status` (snapshot of ids → status before the refactor) is unchanged.
- `demo_residents()` body is shorter by ≥15 lines; `scripts/ci.sh` passes.

### T136 — Test: demo_residents() is stable across repeated calls
- status: done
- class: light
- priority: 1
- kind: test
- deps: —
- area: pipeline/tests/test_demo_stability.py
- owner: ian-claude-light-2
- claimed: 2026-10-17T08:02Z
- pr: #122
- rating: 5/5 clear

What: The tester saw the demo alert grow on every page load (T121). Guard the demo data source against that class of bug: calling `demo_residents()` and `build_alerts(demo_residents())` repeatedly with no live sessions recorded must return identical results. Read only `pipeline/src/routine_watch/demo.py`, `pipeline/src/routine_watch/alerts.py`, `pipeline/tests/conftest.py`.
Interface: new file `pipeline/tests/test_demo_stability.py`; uses the existing session-log reset fixture from `conftest.py`.
Acceptance:
- Three consecutive calls give equal resident lists (status, scores, session count) and equal alert lists (ids, error counts, summary text).
- If it fails on current main because T121 is unmerged, mark that test `xfail(strict=True, reason="T121")` and say so in the PR.
- `scripts/ci.sh` passes.

### T137 — StatusChip: say what "Watch" means on hover and for screen readers
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/ui/StatusChip.tsx, web/src/ui/StatusChip.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T08:11Z
- pr: #127
- rating: 5/5 clear

What: Now that demo residents reach "watch" (T125), a nurse needs to know in 10 s what each chip means. Add a short `title` + `aria-label` per status: flagged = "Change flagged for review", watch = "Worth watching: trending away from their usual routine", normal = "Within their usual range". Read only `web/src/ui/StatusChip.tsx`, its test and `web/src/ui/README.md`.
Interface: `StatusChip` props unchanged.
Acceptance:
- Test asserts each status renders its label text and accessible name; no wording says "diagnos".
- `cd web && npm run lint && npm test && npm run build` passes.

### T138 — Review: AlertContext is never rendered, unstyled, and copies ContextTimeline
- status: done
- class: standard
- priority: 1
- kind: improvement
- source: reviewer
- deps: —
- area: web/src/alert/AlertContext.tsx, web/src/alert/AlertView.tsx, web/src/alert/alert.css, web/src/resident/ContextTimeline.tsx, web/src/resident/format.ts, web/src/alert/AlertView.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T08:10Z
- pr: #130
- rating: 5/5 clear

What: T112 added `AlertContext` but nothing imports it, so the alert screen still shows no care-record context (SPEC §5 bonus 5), and its `alert-context*` classes have no CSS. Its `describe()`/`time()` are verbatim copies of `ContextTimeline.tsx`. Fix: move `describe` and `time` into `web/src/resident/format.ts` (e.g. `describeCareRecord`, `recordTime`) and use them in both components; in `AlertView` render a `<Card><SectionHeader title="Recent care records" /><AlertContext records=… alertTs={alert.ts} /></Card>` fed from the resident detail's `care_records` (existing `web/src/resident/api.ts` fetch, mock fallback), hidden while loading; add `.alert-context*` styles in `alert.css` using `web/src/ui/` tokens only (no hard-coded colours).
Interface: `AlertContext` props unchanged.
Acceptance:
- AlertView test asserts a care record from the mock resident appears on the alert screen.
- No duplicated `describe` between the two components.
- `cd web && npm run lint && npm test && npm run build` passes.

### T139 — Docs: scenario README lists only 13 of 20 scenarios
- status: in-review
- class: light
- priority: 2
- kind: docs
- deps: —
- area: tests/scenarios/README.md
- owner: ian-claude-light-2
- claimed: 2026-10-17T08:14Z
- pr: #131
- rating: 5/5 clear

What: `tests/scenarios/README.md` has no row for meds_pill_before_water, tea_bad_sessions_far_apart, tea_kettle_twice, tea_milk_sugar, tea_self_corrected, tea_teabag_three_times (check for others); add one row each in the existing table format.
Interface: Read only `tests/scenarios/README.md` and each missing scenario's `expected.yaml` (its header comment says what it shows).
Acceptance:
- Every directory under `tests/scenarios/` has exactly one row; descriptions are one line, plain words, and say whether it flags.
- `scripts/ci.sh` passes.

### T140 — Test: every scenario directory is listed in the scenario README
- status: todo
- class: light
- priority: 3
- kind: test
- deps: T139
- area: tests/test_scenarios_readme.py
- owner: —
- claimed: —
- pr: —

What: The scenario README keeps falling behind new scenarios (T065, T139). Add a pytest that fails when a scenario directory has no row in the README, so CI catches it.
Interface: New file `tests/test_scenarios_readme.py`: list dirs in `tests/scenarios/` that contain `expected.yaml`; assert each name appears in `tests/scenarios/README.md`. Read only `tests/scenarios/README.md` and `tests/test_tasks_py.py` (for how root tests are written and run).
Acceptance:
- Passes on main after T139; deleting a row makes it fail with the missing scenario's name in the message.
- `scripts/ci.sh` passes and runs the new test (if it doesn't, say so in the PR; don't edit ci.sh).

### T141 — Pattern scenario: executive pattern (perseveration with steps still in order)
- status: in-review
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
- status: claimed
- class: standard
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/pattern_evening_worsening/
- owner: ian-claude-standard-2
- claimed: 2026-10-17T08:17Z
- pr: —

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
- deps: —
- area: tests/scenarios/pattern_motor_slowing/
- owner: —
- claimed: —
- pr: —

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
- status: in-review
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
- status: todo
- class: light
- priority: 3
- kind: docs
- deps: —
- area: docs/CODEMAP.md
- owner: —
- claimed: —
- pr: —

What: T131 made a live session send one push alert when it flips a resident to flagged (`live.py` `_resident_flagged`, `notify.get_notifier`), and T121 made `alerts.py` invent plausible step/time placeholders from error counts (`_task_errors`, `_distinct_clauses`). Neither is in docs/CODEMAP.md's notes.
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
