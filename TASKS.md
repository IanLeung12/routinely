# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: 1a3d1c7

## Tasks

### T037 — Skeleton replay API for evidence
- status: in-review
- class: standard
- priority: 2
- kind: feature
- deps: T029
- area: pipeline/src/routine_watch/evidence.py, pipeline/src/routine_watch/api.py (add the route only), pipeline/tests/test_evidence.py
- owner: ian-claude-standard-2
- claimed: 2026-10-17T05:54Z
- pr: #65

What: Back the alert's "open evidence" with skeleton frames, never video (SPEC §8). Demo sessions have no recorded frames, so map the flagged resident's latest session to the `tea_skip_teabag_pour_twice`-style frames scenario (or `tea_no_kettle` until it exists) and a normal session for the ghost layer.
Interface: `evidence.replay_frames(session_id, t_start, t_end, fps=10) -> list[CaptureFrame]` (downsampled, padded ±2 s, clipped to session); `GET /sessions/{session_id}/replay?t_start&t_end&fps` → `{session_id, frames}`, 404 unknown session; `GET /residents/{id}/normal_replay?t_start&t_end` → frames from a normal session for the ghost overlay.
Acceptance:
- Tests: frames within window, fps cap honoured, 404s, payload validates against `contracts/capture_frame.schema.json`, no image/bytes fields.
- `cd pipeline && uv run pytest tests/test_evidence.py -q` and `scripts/ci.sh` pass.

### T038 — Session store: in-memory default + Tiger Data (TimescaleDB)
- status: in-review
- class: standard
- priority: 2
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/store.py, pipeline/sql/schema.sql, pipeline/tests/test_store.py, pipeline/pyproject.toml, .env.example
- owner: ian-claude-standard-2
- claimed: 2026-10-17T06:01Z
- pr: #67

What: SPEC §6.3 and the Tiger Data prize: sessions, step events and errors stored as time series. In-memory is the default so tests/CI/demo need no DB; Timescale only when `DATABASE_URL` is set.
Interface: `class Store(Protocol)`: `add_session(Session)`, `add_events(list[StepEvent])`, `add_errors(list[TaskError])`, `sessions(resident_id, task_id, since: datetime) -> list[Session]`, `errors_for(session_id) -> list[TaskError]`. `MemoryStore`; `TimescaleStore(dsn)` using psycopg 3 (optional extra `db`); `schema.sql` creates `sessions`, `step_events`, `task_errors` with hypertables on the time column; `get_store()` picks by env. Not wired into the API yet.
Acceptance:
- MemoryStore tests for every method; TimescaleStore tests skipped unless `DATABASE_URL` set; `schema.sql` parses (basic check) and is idempotent (`IF NOT EXISTS`).
- `cd pipeline && uv run pytest tests/test_store.py -q` and `scripts/ci.sh` pass.

### T041 — Second task: taking medication with water
- status: done
- class: heavy
- priority: 3
- kind: feature
- deps: —
- area: contracts/, pipeline/src/routine_watch/contracts.py, web/src/contracts.ts (regenerated), pipeline/src/routine_watch/tasks/meds.yaml, pipeline/tests/test_meds_graph.py, tests/scenarios/meds_normal/, tests/scenarios/meds_skip_water/
- owner: —
- claimed: —
- pr: #59
- note: PR #59 rebased, CI green, auto-merge on

What: SPEC Nice-to-have 4: show the graph-based approach generalises. Add detector classes `pill_bottle`, `pill_organiser`, `glass`, `water_jug` (contracts change: regenerate schemas + TS via `uv run python -m routine_watch.contracts`), a `meds.yaml` graph (get glass → fill glass; open organiser → take pill → drink water; close organiser optional), and two step-level scenarios.
Interface: `load_task("meds")` works; existing tea graph and scenarios untouched.
Acceptance:
- Graph tests (deps, optional step, aliases); `meds_skip_water` yields an omission of `drink_water`; contracts check in CI passes.
- `scripts/e2e.sh` and `scripts/ci.sh` pass.

### T044 — Alert notifier behind an interface (push alert)
- status: in-review
- class: standard
- priority: 2
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/notify.py, pipeline/tests/test_notify.py, .env.example
- owner: ian-claude-standard
- claimed: 2026-10-17T06:03Z
- pr: #69

What: SPEC Nice-to-have 3 (push alert to a phone) and §10 step 4. A `Notifier` interface with a fake used by default and a Supabase implementation used only when `LIVE_API=1` and Supabase env vars are set. No route wiring in this task.
Interface: `class Notifier(Protocol): def send(self, alert: dict) -> None`; `FakeNotifier` (records sent alerts in `.sent`); `SupabaseNotifier(url, key)` inserting `{alert_id, resident_id, summary, created_at}` into table `alerts_feed` via the REST endpoint with plain HTTP (httpx or urllib, no new SDK); `get_notifier() -> Notifier` returns Supabase only when `LIVE_API=1` and `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` are set, else Fake. Network errors are logged and swallowed (never break the pipeline). Payload carries ids and summary text only, no frames. Document the table in the module docstring; any new env var goes in `.env.example`.
Acceptance:
- Tests: default env → FakeNotifier; LIVE_API=1 without keys → Fake; with keys → Supabase (HTTP mocked; assert URL, headers, body); network failure doesn't raise. No real calls.
- `cd pipeline && uv run pytest tests/test_notify.py -q` and `scripts/ci.sh` pass.

### T050 — Drift endpoint for a resident
- status: todo
- class: standard
- priority: 2
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/api.py (add the route only), pipeline/src/routine_watch/demo.py (expose daily scores only if needed), pipeline/tests/test_api_drift.py
- owner: —
- claimed: —
- pr: —

What: Back the drift card (T049) with data: `GET /residents/{resident_id}/drift` runs `routine_watch.drift.drift` over that resident's demo sessions, one point per day (mean score per date). The demo "slow drift" resident must come out `trending: true`, Mrs. K and the stable resident `false`.
Interface: response `{"resident_id": str, "slope_per_day": float, "days": int, "trending": bool}`; 404 for unknown resident, same style as `get_resident`.
Acceptance:
- pytest via FastAPI TestClient: 200 shape, 404, drift resident trending, stable resident not trending.
- `scripts/ci.sh` passes.

### T052 — Demo-data banner component
- status: done
- class: light
- priority: 3
- kind: feature
- deps: —
- area: web/src/ui/DemoBanner.tsx, web/src/ui/DemoBanner.test.tsx, web/src/ui/README.md (add one line)
- source: proposed
- owner: ian-claude-standard
- claimed: 2026-10-17T06:22Z
- pr: #52

What: Responsible design / Clarity for judges: a thin banner stating the dashboard runs on synthetic residents. Component only; wiring into `App.tsx` is a later task. Read only the files in `area` and `web/src/ui/Card.tsx` (style).
Interface: `export function DemoBanner({ onDismiss }: { onDismiss?: () => void })` renders `role="note"` with text "Demo mode: synthetic residents, no real patient data. Changes are flagged for review only." (do not use the word "diagnosis" in any form; tests/test_privacy.py rejects it) and, if `onDismiss` is given, a "Dismiss" button. CSS vars only.
Acceptance:
- Vitest: text present, role=note, dismiss button only when `onDismiss` given and calls it.
- note: fix CI on PR #52: orch changed the required text to avoid "diagnosis" (test_privacy.py). Update the component and test on branch task/T052-demo-banner, then set auto-merge.
- `cd web && npm run lint && npm test && npm run build` passes.

### T059 — Show the drift card on the resident detail screen
- status: done
- class: light
- priority: 2
- kind: feature
- deps: —
- area: web/src/resident/ResidentDetail.tsx, web/src/resident/ResidentDetail.test.tsx, web/src/resident/api.ts, web/src/mock/residentDetail.ts
- owner: max-codex-light-2
- claimed: 2026-10-17T05:35Z
- pr: #49

What: `DriftCard` (T049) is built but rendered nowhere. Show it on the resident detail screen, fed by a new `fetchDrift(residentId)` that calls `GET /residents/{id}/drift` and falls back to mock data like `fetchResident` does (the endpoint lands in T050).
Interface: read `web/src/resident/DriftCard.tsx`, `web/src/resident/api.ts`, `web/src/resident/ResidentDetail.tsx`, `web/src/mock/residentDetail.ts`. Add `fetchDrift(residentId): Promise<{resident_id: string; slope_per_day: number; days: number; trending: boolean} | null>` in `api.ts`; render `<DriftCard slopePerDay days trending />` under the baseline chart; render nothing if `null`.
Acceptance:
- Test: the mock slow-drift resident shows the trending card; a resident with no drift data shows no card.
- `scripts/ci.sh` passes.

### T060 — Tests for resident date/format helpers
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/resident/format.test.ts, web/src/resident/days.test.ts
- owner: max-codex-light-1
- claimed: 2026-10-17T05:35Z
- pr: #50

What: `web/src/resident/format.ts` and `days.ts` drive every date and score on the resident screen but have no direct tests. Add them; no source changes (if you find a bug, add a skipped test with a comment and note it in the PR).
Interface: read only `web/src/resident/format.ts`, `web/src/resident/days.ts`, `web/src/resident/types.ts`. Cover `utcDate`, `formatDay`, `formatDayTime`, `formatDuration`, `formatScore`, `formatErrors`, `dailyScores` (incl. empty input, missing days → `null`, UTC day boundaries, invalid timestamps).
Acceptance:
- ≥1 test per exported function, edge cases above covered.
- `scripts/ci.sh` passes.

### T061 — Live session screen accessibility pass
- status: todo
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/live/LiveSession.tsx, web/src/live/LiveSession.test.tsx, web/src/live/SkeletonView.tsx, web/src/live/SkeletonView.test.tsx
- owner: —
- claimed: —
- pr: —

What: The live screen updates continuously but a screen-reader user hears nothing. Announce step completions and raised flags through a polite `aria-live` region (one short sentence per event, e.g. "Step done: fill the kettle"), give the skeleton view a text alternative, and announce connection status changes. Do not touch `TaskMap.tsx` (T057 owns the legend next to it).
Interface: no contract changes; use the existing `useLiveSession` messages.
Acceptance:
- Tests (Testing Library) assert the live region text after a mock step event and after a flag; the skeleton has an accessible name.
- No change to the visual layout.
- `scripts/ci.sh` passes.

### T062 — Nurse shift handoff summary (separate screen)
- status: todo
- class: heavy
- priority: 3
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/handoff.py, pipeline/src/routine_watch/api.py (add the route only), pipeline/tests/test_handoff.py, web/src/handoff/, web/src/App.tsx (one nav entry)
- owner: —
- claimed: —
- pr: —
- source: proposed

What: Rationale: a nurse starting a shift wants one view of "who changed in the last 12 h" (Usefulness/Clarity, Use-of-AI hook). `GET /handoff?hours=12` lists residents with flags, pending-review alerts and drift trends in that window, plus a short plain-language summary from the existing `Explainer` interface (fake by default, no real call without `LIVE_API=1`). Wording: "flagged for review", never "diagnosed".
Interface: `handoff.build_handoff(now, hours) -> {"window_hours": int, "residents": [{"resident_id", "name", "flags": int, "pending_review": int, "trending": bool}], "summary": str}`; web screen `web/src/handoff/Handoff.tsx` reachable from one button in `App.tsx`, off the main demo path.
Acceptance:
- pytest: Mrs. K appears with her flag in the demo window; stable resident has 0 flags; summary comes from the fake explainer and contains no "diagnos".
- Web test renders the list and summary from mock data.
- `scripts/ci.sh` passes.

### T063 — Wire the alert evidence screen into the app
- status: done
- class: light
- priority: 1
- kind: feature
- deps: —
- area: web/src/App.tsx, web/src/App.test.tsx
- owner: max-codex-light-1
- claimed: 2026-10-17T05:41Z
- pr: #55

What: `AlertView` (T028, `web/src/alert/AlertView.tsx`) is merged but `App.tsx` still shows an "Alert evidence — not built yet" placeholder, so the demo can't reach screen 4. Replace the placeholder with an "Alerts" section listing alerts and opening `AlertView` for one.
Interface: in `App.tsx`, load alerts with `fetchAlerts()` from `web/src/alert/api.ts` (it falls back to `web/src/mock/alerts.ts`); render one button per alert (resident + plain-language label); clicking sets `openAlert` state and renders `<AlertView alertId={id} onBack={() => setOpenAlert(null)} />` in place of the overview (same pattern as `openResident`). Remove the `screens` placeholder array. Read only `App.tsx`, `App.test.tsx`, `alert/api.ts`, `alert/AlertView.tsx` (props), `mock/alerts.ts`.
Acceptance:
- No "not built yet" text remains in `App.tsx`.
- App test: clicking the `mrs-k-change-1` alert shows the alert view; Back returns to the overview.
- `scripts/ci.sh` passes.

### T064 — Show the task map legend on the live session screen
- status: done
- class: light
- priority: 2
- kind: feature
- deps: —
- area: web/src/live/LiveSession.tsx, web/src/live/LiveSession.test.tsx
- owner: max-codex-light-2
- claimed: 2026-10-17T05:43Z
- pr: #57

What: `TaskMapLegend` (T057) exists but is not rendered anywhere. Render it inside the "Task map" card in `LiveSession.tsx`, directly below `<TaskMap>`.
Interface: `import { TaskMapLegend } from './TaskMapLegend.tsx'`; no prop changes. Read only `LiveSession.tsx`, `LiveSession.test.tsx`, `TaskMapLegend.tsx`.
Acceptance:
- LiveSession test asserts the list labelled "Task map legend" is present with the five state labels.
- `scripts/ci.sh` passes.

### T065 — Docs: scenario README table lists only 4 of 8 scenarios
- status: done
- class: light
- priority: 2
- kind: docs
- deps: —
- area: tests/scenarios/README.md
- owner: max-codex-light-1
- claimed: 2026-10-17T05:45Z
- pr: #58

What: The "The scenarios here" table in `tests/scenarios/README.md` misses `tea_sequence_error`, `tea_single_bad_no_flag`, `tea_substitution`, `tea_unclear_not_error`. Add one row each (level steps/frames + one sentence on what it guards), taken from the comment at the top of each `tests/scenarios/<name>/expected.yaml`. Also drop the stale sentence saying hesitation is missing if `pipeline/src/routine_watch/hesitation.py` now produces hesitation errors (check its docstring; if unsure, leave it).
Interface: docs only. Read only the README and the four `expected.yaml` files (plus `hesitation.py` docstring).
Acceptance:
- Table has one row per directory in `tests/scenarios/` (8 rows, alphabetical or grouped as today).
- `scripts/ci.sh` passes.

### T066 — Scenario: self-corrected slip is reported but does not flag
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/tea_self_corrected/
- owner: max-codex-light-2
- claimed: 2026-10-17T05:48Z
- pr: #60

What: SPEC §7 says a mistake the resident fixes within a short window is a weaker "self-corrected slip", not a full error. No scenario covers it. Add a steps-level scenario where the resident pours before the teabag is in, then puts the teabag in and pours again within the window.
Interface: `tests/scenarios/tea_self_corrected/{steps.jsonl,expected.yaml}`. Read only `tests/scenarios/README.md` (format), `tests/scenarios/tea_sequence_error/` (template), `pipeline/src/routine_watch/tasks/tea.yaml` (step ids) and the docstring + `SELF_CORRECT_WINDOW_S` in `pipeline/src/routine_watch/errors.py`. Record the actual replay output (`cd pipeline && uv run python -m routine_watch.replay ../tests/scenarios/tea_self_corrected`) in `expected.yaml`, and assert `score:` so a change to self-correction weighting shows up. Give it a `history:` with one earlier bad session so the scenario proves the slip alone does not push it over to `flag: true` (adjust if the real output disagrees; say so in the comment).
Acceptance:
- `scripts/e2e.sh tests/scenarios/tea_self_corrected` passes; header comment says what it guards.
- `scripts/ci.sh` passes.

### T067 — Scenario: optional milk and sugar both done is a clean session
- status: in-review
- class: light
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/tea_milk_sugar/
- owner: max-codex-light-1
- claimed: 2026-10-17T05:49Z
- pr: #61

What: `tea_normal` skips sugar; nothing checks that doing both optional steps (milk and sugar) is never counted as an error or perseveration. Add a steps-level scenario doing every step including milk and sugar, with 3+ clean history sessions, expecting no errors, `score: 0.0`, `flag: false`.
Interface: `tests/scenarios/tea_milk_sugar/{steps.jsonl,expected.yaml}`. Read only `tests/scenarios/README.md`, `tests/scenarios/tea_normal/` (template) and `pipeline/src/routine_watch/tasks/tea.yaml`.
Acceptance:
- `scripts/e2e.sh tests/scenarios/tea_milk_sugar` passes with the recorded real output.
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

### T069 — Tests for ErrorList and SuggestedChecks
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/alert/ErrorList.test.tsx, web/src/alert/SuggestedChecks.test.tsx
- owner: max-codex-light-2
- claimed: 2026-10-17T05:54Z
- pr: #63

What: Both components have no tests. Read only `web/src/alert/ErrorList.tsx`, `web/src/alert/SuggestedChecks.tsx`, `web/src/contracts.ts` (types `TaskError`, `SuggestedCheck`) and `web/src/alert/FeedbackButtons.test.tsx` (test style).
Interface: new test files only; do not change the components.
Acceptance:
- ErrorList: each error type renders its phrase (e.g. omission → "skipped <step>"), the timestamp formats as m:ss, and the chip colour matches red/amber/grey; an empty list renders without crashing.
- SuggestedChecks: renders one item per check, and nothing (or an empty state) for an empty list.
- `cd web && npm run lint && npm test && npm run build` passes.

### T070 — Tests for Sparkline and SessionList
- status: in-review
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/overview/Sparkline.test.tsx, web/src/resident/SessionList.test.tsx
- owner: max-codex-light-2
- claimed: 2026-10-17T06:00Z
- pr: #68

What: Both components have no tests. Read only `web/src/overview/Sparkline.tsx`, `web/src/resident/SessionList.tsx`, `web/src/resident/types.ts`, `web/src/resident/format.ts` and `web/src/resident/DriftCard.test.tsx` (test style).
Interface: new test files only; do not change the components.
Acceptance:
- Sparkline: renders an svg path for ≥2 scores, handles 0 and 1 score without NaN in any attribute.
- SessionList: one row per session with formatted date/score/errors; empty list shows the empty state; any click/select callback fires with the right session.
- `cd web && npm run lint && npm test && npm run build` passes.

### T071 — Tests for useLiveSession and mockLiveStream
- status: claimed
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/live/useLiveSession.test.ts, web/src/live/mockLiveStream.test.ts
- owner: max-codex-light-1
- claimed: 2026-10-17T06:01Z
- pr: —

What: The live screen's state hook and mock stream are untested. Read only `web/src/live/useLiveSession.ts`, `web/src/live/mockLiveStream.ts`, `web/src/live/LiveSession.test.tsx` (how it fakes the socket) and `.tasks/LESSONS.md` (pending effects after teardown break CI).
Interface: new test files only; use `vi.useFakeTimers()` and a fake WebSocket; no real network.
Acceptance:
- mockLiveStream: emits messages in order, ends with a session-ended message, and the returned stop function stops further messages.
- useLiveSession (renderHook): step states update from messages, the end message sets the ended state, and the socket closes on unmount.
- `cd web && npm run lint && npm test && npm run build` passes, run twice with no flakes.

### T072 — Live camera session messages (capture → recogniser → live messages)
- status: todo
- class: heavy
- priority: 1
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/live_camera.py, pipeline/tests/test_live_camera.py, docs/CODEMAP.md (notes only)
- owner: —
- claimed: —
- pr: #74
- note: merge conflict with main on PR #74: check out its branch, merge origin/main, fix, push

What: `/ws/live` only replays recorded scenarios; the demo needs the camera path too (SPEC §10, §16 decision B). Build the generator that turns a live capture stream into the same messages `live.session_messages` yields, so wiring it into the route is a one-line follow-up.
Interface: `async def camera_session_messages(frames: AsyncIterator[CaptureFrame] | Iterable[CaptureFrame], task: str = "tea") -> AsyncIterator[dict]` in `live_camera.py`, reusing `live.py`/`recogniser.py`/`replay.py` helpers (import, don't copy; don't edit `live.py` or `api.py`). Frames come from `capture.record_stream` with `FakeLandmarker`/`FakeDetector` in tests; never store frames.
Acceptance:
- Feeding a recorded scenario's `frames.jsonl` through `camera_session_messages` yields the same step/error/end messages as `session_messages` for that scenario (test over ≥3 scenarios).
- No real camera, network or paid API in tests; `scripts/ci.sh` passes.

### T073 — Review: live screen hard-codes the tea steps instead of the session's task graph
- status: in-review
- class: standard
- priority: 1
- kind: bug
- deps: T064
- area: pipeline/src/routine_watch/live.py, pipeline/tests/test_live.py, web/src/live/useLiveSession.ts, web/src/live/LiveSession.tsx, web/src/live/mockLiveStream.ts, web/src/live/LiveSession.test.tsx
- source: reviewer
- owner: ian-claude-standard
- claimed: 2026-10-17T05:57Z
- pr: #66

What: `LiveSession.tsx` renders `<TaskMap steps={MOCK_STEPS}>` and `stepLabel()` looks labels up in `MOCK_STEPS` even when `source === 'live'`. The `/ws/live` protocol never tells the client which steps exist, so any non-tea task (T041 medication) or a renamed step shows the wrong map and "Session" labels.
Interface: `live.session_messages` yields first `{"type": "session_start", "session_id", "task_id", "steps": [{"id", "label", "optional"}]}` from `scenario.graph`. Add it to the `LiveMessage` union; `useLiveSession` stores `steps` in state (mock stream sends the same message built from `MOCK_STEPS`); `LiveSession.tsx` uses `state.steps` for the map and labels, never `MOCK_STEPS` directly.
Acceptance:
- pytest: first message of `session_messages` for `tea_abandoned` is `session_start` with the graph's step ids in order.
- vitest: a live stream with a custom 2-step `session_start` renders those 2 labels in the task map.
- `scripts/ci.sh` passes.

### T074 — Review: one stray second skeleton marks the whole session "assisted"
- status: in-review
- class: light
- priority: 1
- kind: bug
- deps: —
- area: pipeline/src/routine_watch/replay.py, pipeline/tests/test_replay.py
- source: reviewer
- owner: max-codex-light-1
- claimed: 2026-10-17T05:55Z
- pr: #64

What: `replay.score_session` sets `assisted = any(len(frame.poses) >= 2 for frame in scenario.frames)`. Now that real capture runs MediaPipe with `num_poses=2` (T039), a single false-positive pose or someone walking past for one frame scores the session 0 and drops it from the baseline, which hides real changes from the nurse.
Interface: add `assisted_of(frames: Sequence[CaptureFrame], min_seconds: float = ASSISTED_MIN_S) -> bool` in `replay.py` with `ASSISTED_MIN_S = 2.0`: true only when ≥2 poses appear in consecutive frames spanning at least `min_seconds` (by `frame.t`). `score_session` uses it.
Acceptance:
- Tests: one isolated 2-pose frame → not assisted; 2 poses held for ≥2 s → assisted; existing scenario expected outputs unchanged (add a frames fixture if no scenario covers it).
- `scripts/ci.sh` passes.

### T075 — Review: error-type labels and colours defined three times in the web app
- status: todo
- class: light
- priority: 2
- kind: improvement
- deps: T064
- area: web/src/ui/errorTypes.ts (new), web/src/ui/errorTypes.test.ts (new), web/src/live/LiveSession.tsx, web/src/alert/ErrorList.tsx, web/src/resident/format.ts
- source: reviewer
- owner: —
- claimed: —
- pr: —

What: `LiveSession.tsx` (`ERROR_LABELS`, `ERROR_COLOR`), `alert/ErrorList.tsx` (phrase + colour maps) and `resident/format.ts` (plain names) each map `ErrorType` separately, so the same error can read or colour differently across screens.
Interface: `web/src/ui/errorTypes.ts` exports `ERROR_TYPE_LABEL: Record<ErrorType, string>`, `ERROR_TYPE_TONE: Record<ErrorType, 'red' | 'amber' | 'grey'>` (SPEC §9 colours) and `describeError(type, stepLabel): string`. The three files import from it; delete their local maps. Visible text may only change where screens disagreed today; note any such change in the PR.
Acceptance:
- Unit test covers every `ErrorType` in all three exports.
- `scripts/ci.sh` passes.

### T076 — Tests for ContextTimeline and BaselineChart
- status: claimed
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/resident/ContextTimeline.test.tsx, web/src/resident/BaselineChart.test.tsx
- owner: max-codex-light-2
- claimed: 2026-10-17T06:07Z
- pr: —

What: Both resident-detail components have no tests. Add focused render tests; do not change the components.
Interface: read only web/src/resident/ContextTimeline.tsx, web/src/resident/BaselineChart.tsx, web/src/resident/types.ts, and web/src/resident/format.test.ts (for test style). Use vitest + @testing-library/react like the existing tests.
Acceptance:
- ContextTimeline: empty list shows "No care records for this resident."; records render newest first; temperature/fluid_intake/med_change get their readable labels ("Temperature 37.9 °C", "Fluid intake 800 ml", "Medication change: ...").
- BaselineChart: renders without crashing for typical props and for an empty series (no NaN in rendered attributes).
- `cd web && npm test -- --run` and `scripts/ci.sh` pass.

### T077 — Tests for the offline fallbacks in overview/api.ts and resident/api.ts
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/overview/api.test.ts, web/src/resident/api.test.ts
- owner: ian-claude-standard-2
- claimed: 2026-10-17T06:11Z
- pr: #71

What: The demo relies on the web app falling back to mock data when the pipeline API is down (SPEC §10 fallback), but `fetchResidents`, `fetchResident` and `fetchDrift` are untested. Add tests with a stubbed `fetch` (`vi.stubGlobal`); do not change the source files.
Interface: read only web/src/overview/api.ts, web/src/resident/api.ts, web/src/mock/residents.ts, web/src/mock/residentDetail.ts, and web/src/alert/api.test.ts (for the fetch-stub pattern).
Acceptance:
- Each function: returns the JSON body on a 200; returns the mock data on a non-OK response; returns the mock data when fetch rejects.
- `fetchResident` returns null for an unknown id when offline; the resident id is URL-encoded in the request URL.
- `cd web && npm test -- --run` and `scripts/ci.sh` pass.

### T078 — Scenario: kettle boiled twice is a repetition flag
- status: in-review
- class: light
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/tea_kettle_twice/
- owner: ian-claude-standard
- claimed: 2026-10-17T06:17Z
- pr: #75

What: Add a replay scenario for the "repetition" error type (SPEC §7): the resident boils the kettle twice, then finishes the tea normally.
Interface: copy the layout of tests/scenarios/tea_skip_teabag_pour_twice/ (frames.jsonl + expected.yaml); read tests/scenarios/README.md for the format and pipeline/src/routine_watch/tasks/tea.yaml for step ids. Do not edit README.md (separate task) or any pipeline code.
Acceptance:
- expected.yaml lists exactly one repetition error on the kettle step and states whether the session flags, matching what the replay produces.
- `scripts/e2e.sh` passes with the new scenario included; `scripts/ci.sh` passes.

### T079 — Alerts use get_explainer() instead of a hard-wired template
- status: in-review
- class: light
- priority: 1
- kind: improvement
- deps: —
- area: pipeline/src/routine_watch/alerts.py, pipeline/tests/test_alerts_explainer.py
- owner: ian-claude-standard-2
- claimed: 2026-10-17T06:07Z
- pr: #70

What: `alerts.py` line ~40 builds `_explainer = TemplateExplainer()`, so the merged Claude summariser (T032, `explain_claude.py`) is never used. Switch to `get_explainer()` so `LIVE_API=1` + `ANTHROPIC_API_KEY` turns on Claude summaries; default stays the template. Read only `alerts.py`, `explain.py`, `explain_claude.py`.
Interface: in `alerts.py`, replace `_explainer = TemplateExplainer()` with a lazily-created `get_explainer()` result (a module-level `_get_explainer()` helper so tests can monkeypatch it). No other behaviour change.
Acceptance:
- New `pipeline/tests/test_alerts_explainer.py`: with `LIVE_API` unset, `build_alerts(...)` summaries equal the current template output; monkeypatching the helper to return a fake explainer (`summarise` returns `"FAKE"`) makes every alert summary `"FAKE"`. No network.
- `cd pipeline && uv run pytest -q` and `scripts/ci.sh` pass.

### T080 — Evidence view: skeleton replay and ghost overlay on the alert screen
- status: todo
- class: standard
- priority: 1
- kind: feature
- deps: T037
- area: web/src/alert/AlertView.tsx, web/src/alert/alert.css, web/src/alert/AlertView.test.tsx, web/src/evidence/api.ts, web/src/evidence/api.test.ts, web/src/mock/
- owner: —
- claimed: —
- pr: —

What: SPEC §5 MVP 5 and §10 step 5: the alert screen must show the skeleton replay of the flagged moment, with the ghost of the resident's normal routine. `ReplayPlayer` and `GhostReplay` exist in `web/src/evidence/` but no screen uses them. Fetch the replay from the T037 evidence API (offline mock fallback like the other `api.ts` files) and render it in an "Evidence" card on `AlertView`, starting at the first error's `t_start`.
Interface: `web/src/evidence/api.ts` `fetchReplay(alertId: string): Promise<...>` matching T037's route/response (read `pipeline/src/routine_watch/evidence.py` after T037 merges); mock data in `web/src/mock/`.
Acceptance:
- AlertView test: replay card renders with mocked data; loading and error/empty states use `ui/` primitives; no raw video or image elements.
- `cd web && npm test` and `scripts/ci.sh` pass.

### T081 — Live session result counts toward the resident's flag (demo step 4)
- status: todo
- class: heavy
- priority: 1
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/live.py, pipeline/src/routine_watch/session_log.py, pipeline/src/routine_watch/demo.py, pipeline/tests/test_live_flag.py, docs/CODEMAP.md (notes only)
- owner: —
- claimed: —
- pr: —

What: SPEC §10 step 4: when a live (or fallback pre-recorded) session for Mrs. K finishes with qualifying errors, it must become one of her sessions, so her sparkline spikes and, being the second qualifying session in the window, the "possible delirium" flag and alert appear on the next `/residents` and `/alerts` fetch. Today `live.py` scores the session but nothing records it.
Interface: new `session_log.py` (in-memory, process-local) `record(resident_id, session: Session) -> None`, `sessions_for(resident_id) -> list[Session]`, `reset()`; `live.py` records the finished session; `demo.py` merges logged sessions into the resident's history before scoring/flagging. Keep it swappable for T038's store later (same shape, no DB here).
Acceptance:
- pytest: playing `tea_skip_teabag_pour_twice` for Mrs. K via `session_messages` then calling `/residents` and `/alerts` (TestClient) shows her flagged with the new session listed; playing `tea_normal` does not flag; `reset()` restores the seeded demo.
- `scripts/e2e.sh` and `scripts/ci.sh` pass.

### T082 — Scenario: medication taken without water is an omission
- status: todo
- class: light
- priority: 2
- kind: test
- deps: T041
- area: tests/scenarios/med_no_water/, tests/scenarios/README.md
- owner: —
- claimed: —
- pr: —

What: Second-task coverage for the tester: a recorded medication session where the resident takes the pill but never pours/drinks water. Copy the shape of the scenario T041 adds for the medication task (read its `frames.jsonl` + `expected.yaml` and `tests/scenarios/README.md` only).
Interface: `tests/scenarios/med_no_water/{frames.jsonl,expected.yaml}` expecting one `omission` error on the water step and no flag on its own; one new README row.
Acceptance:
- `scripts/e2e.sh` passes including the new scenario; `scripts/ci.sh` passes.

### T083 — Docs: CODEMAP notes for the Claude explainer and Gemini verifier
- status: done
- class: light
- priority: 3
- kind: docs
- deps: —
- area: docs/CODEMAP.md (notes only)
- owner: ian-claude-standard-2
- claimed: 2026-10-17T06:23Z
- pr: #77

What: `docs/CODEMAP.md` notes don't mention `explain_claude.py` (T032) or how `get_explainer()` / `get_verifier()` choose the fake vs the real client. Add 2–4 lines: both default to offline fakes, real calls only with `LIVE_API=1` + key, through `api_cache.py`, models from `ANTHROPIC_MODEL` / `GEMINI_MODEL`. Read only `docs/CODEMAP.md`, the top docstrings of `explain_claude.py`, `verifier.py`, `api_cache.py`.
Acceptance:
- Notes only (generated file list untouched); `scripts/ci.sh` passes.

### T084 — Pattern library + scorer + Alert.patterns contract (SPEC §7.5)
- status: todo
- class: heavy
- priority: 1
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/contracts.py, pipeline/src/routine_watch/patterns.py, pipeline/src/routine_watch/patterns_library.py, pipeline/src/routine_watch/alerts.py, pipeline/tests/test_patterns.py, contracts/, web/src/contracts.ts
- owner: —
- claimed: —
- pr: —

What: The pivot in SPEC §7.5 (decision D): every flag ranks the patterns the change is consistent with. Deterministic rules over features, library as data, LLM never adds patterns.
Interface:
- Contract: `PatternMatch {pattern_id, name, confidence (0–1), urgency: routine|next_round|same_shift|urgent, evidence: [str], checks: [SuggestedCheck or str]}`; `Alert.patterns: list[PatternMatch]` (empty = "no clear pattern"). Regenerate schemas + `web/src/contracts.ts`; keep existing fields working.
- `patterns_library.py`: the six patterns from §7.5 as data (signals + weights, time profile, checks, urgency, source citation). Only `sudden_change` and `slow_drift` need to score well now; others present with conservative weights.
- `patterns.py`: `extract_features(sessions, baseline, care_records) -> Features` and `score_patterns(features, library) -> list[PatternMatch]` (top 3 above threshold, sorted).
- `alerts.py`: fill `Alert.patterns` from the scorer.
Acceptance:
- Unit tests: a sudden-spike history ranks `sudden_change` first; a gradual rise ranks `slow_drift` first; flat noise → no pattern; a new sedating med raises the medication pattern.
- Wording in evidence/checks uses "consistent with" / "rule out", never "diagnosis".
- `scripts/ci.sh` passes; update `docs/CODEMAP.md` data-flow notes.

### T085 — PatternList component for ranked "possible patterns" (not wired yet)
- status: done
- class: light
- priority: 1
- kind: feature
- deps: —
- area: web/src/alert/PatternList.tsx, web/src/alert/PatternList.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T06:15Z
- pr: #73

What: SPEC §9 screen 4 now shows "Possible patterns", ranked. Build the presentational component now so T088 only has to wire it once T084 lands the contract.
Interface: `export interface PatternView { pattern_id: string; name: string; confidence: number /*0-1*/; urgency: 'routine'|'next_round'|'same_shift'|'urgent'; evidence: string[]; checks: string[] }` and `export function PatternList({ patterns }: { patterns: PatternView[] })`. Each item: name, "consistent with" phrasing (e.g. heading "Consistent with: Sudden change (delirium)"), confidence as a percentage, urgency label, evidence bullets, "Consider ruling out:" checks. `urgent` items get a distinct class (`pattern--urgent`) and an "Urgent" label (not colour alone). Empty list renders "Change detected, no clear pattern". Read for style only: `web/src/alert/SuggestedChecks.tsx`, `web/src/ui/Card.tsx`. Do not import from contracts.ts and do not edit any other file.
Acceptance:
- Vitest: renders items in the given order with name, % confidence, evidence and checks; urgent item has the urgent class and visible "Urgent" text; empty list shows "no clear pattern"; no text contains "diagnos".
- `cd web && npm test` and `scripts/ci.sh` pass.

### T086 — Synthetic history: evening-only worsening resident scenario
- status: todo
- class: light
- priority: 2
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/synth/history.py, pipeline/tests/test_history.py
- owner: —
- claimed: —
- pr: —

What: SPEC §8 needs a resident whose errors are concentrated in late-day sessions (sundowning pattern, §7.5). Add an `"evening"` scenario to the history generator.
Interface: `generate_history(resident_id, days, seed, scenario="evening")`; add `"evening"` to `SCENARIOS`. Sessions whose local hour (from `ts`) is ≥ 16 in the last ~7 days get 1–3 errors (sequence/omission/hesitation); morning sessions stay like `"normal"`. Read only `pipeline/src/routine_watch/synth/history.py` and `pipeline/tests/test_history.py`; don't touch `demo.py`.
Acceptance:
- pytest: deterministic for a fixed seed; mean errors of evening sessions in the last 7 days ≥ 3× morning sessions; morning sessions look like `normal`; at least one session before and after 16:00 exists each day (adjust session times only for this scenario if needed).
- `scripts/ci.sh` passes.

### T087 — Synthetic history: motor slowing after a sedating medication
- status: in-review
- class: standard
- priority: 2
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/synth/history.py, pipeline/src/routine_watch/synth/care_records.py, pipeline/tests/test_history.py, pipeline/tests/test_care_records.py
- owner: ian-claude-standard
- claimed: 2026-10-17T06:12Z
- pr: #72

What: SPEC §7.5/§8 motor slowing pattern: after a new sedating med (e.g. diphenhydramine) ~5 days before the end, step durations and gaps rise while sequencing errors stay rare. Sessions need a duration signal for T084's feature extractor.
Interface: new `"motor"` scenario in `generate_history` and `generate_care_records`. Add a per-session `duration_s` (total task seconds) to every generated session (all scenarios; normal ≈ 150–200 s), and for `"motor"` raise it ~40–60 % after the med start with mostly `hesitation` errors. Care records: a `medication` entry for the sedating med on the start day. Keep existing keys unchanged so `demo.py` keeps working.
Acceptance:
- pytest: `motor` durations after the med start average ≥ 1.4× before; sequence/omission errors stay ≤ normal rate; care record present on the right day; all existing history/care-record tests still pass.
- `scripts/ci.sh` passes.

### T088 — Alert screen shows ranked possible patterns
- status: todo
- class: standard
- priority: 1
- kind: feature
- deps: T084, T085
- area: web/src/alert/AlertView.tsx, web/src/alert/AlertView.test.tsx, web/src/alert/PatternList.tsx, web/src/mock/alerts.ts
- owner: —
- claimed: —
- pr: —

What: SPEC §9 screen 4 / demo step 5: the alert view shows "Possible patterns" right under the summary, from `Alert.patterns`.
Interface: switch `PatternList` to the generated `PatternMatch` type from `web/src/contracts.ts` (drop the local `PatternView` or alias it); render it in `AlertView` between summary and error list; give mock Mrs. K alert a `sudden_change` top pattern with evidence and rule-out checks.
Acceptance:
- Vitest: AlertView renders the top pattern name and its checks; an alert with `patterns: []` shows "no clear pattern".
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

### T090 — "What was it?" picker in the feedback buttons (UI only)
- status: done
- class: light
- priority: 2
- kind: feature
- deps: —
- area: web/src/alert/FeedbackButtons.tsx, web/src/alert/FeedbackButtons.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T06:19Z
- pr: #76

What: SPEC §5 MVP 8: after "Confirmed", the nurse can optionally say what it turned out to be. Add the picker to the component only; posting it is a later task.
Interface: new optional props `causeOptions?: {id: string; label: string}[]`, `cause?: string | null`, `onCauseChange?: (id: string) => void`. When `value === 'confirmed'` and `causeOptions` is given, render a labelled group "What was it? (optional)" with one toggle button per option plus "Other" (`id: 'other'`), `aria-pressed` on the selected one. Without these props the component behaves exactly as today. Read only those two files.
Acceptance:
- Vitest: picker hidden before confirming and when `causeOptions` is absent; shown after confirmed; clicking an option calls `onCauseChange` with its id; existing tests unchanged and passing.
- `cd web && npm test` and `scripts/ci.sh` pass.

### T091 — Tests: demo residents land on their intended status
- status: in-review
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_demo.py
- owner: ian-claude
- claimed: 2026-10-17T06:22Z
- pr: #78

What: `pipeline/src/routine_watch/demo.py` pins seeds so each resident gets its intended status, but no test guards it; upcoming pattern work (T084, T089) will change this file.
Interface: new `pipeline/tests/test_demo.py` only. Read `pipeline/src/routine_watch/demo.py`. Don't edit source.
Acceptance:
- pytest: `demo_residents()` is deterministic (two calls equal); `mrs-k` status is `flagged`; `mrs-ahmed` and `mr-silva` are `normal`; `mr-chen` is not `normal`; every resident has 14 days of score points sorted by `ts`; no resident has an empty name or room.
- `scripts/ci.sh` passes.

### T092 — PatternList styles: urgent patterns visually distinct
- status: in-review
- class: light
- priority: 1
- kind: improvement
- deps: —
- area: web/src/alert/PatternList.tsx, web/src/alert/PatternList.css (new), web/src/alert/PatternList.test.tsx
- owner: ian-claude
- claimed: 2026-10-17T06:27Z
- pr: #81

What: `PatternList` (merged in #73) uses class names (`pattern`, `pattern--urgent`, `pattern__urgency--*`, `pattern__confidence`) that no stylesheet defines, so urgent patterns look like every other one (SPEC §9 screen 4: "Urgent patterns are visually distinct"). Read only the files in `area`, `web/src/index.css` (tokens) and `web/src/alert/alert.css` (style reference; do not edit it).
Interface: new `PatternList.css` imported from `PatternList.tsx`. CSS vars from `index.css` only, no hex colours (dark theme). Urgent: a thick left border and the red error token; `same_shift`: amber token; others: muted. Confidence as a small pill. Also add `aria-label="Possible patterns"` on the outer `<ul>`.
Acceptance:
- Vitest: the urgent item has class `pattern--urgent` and the non-urgent does not; the list has accessible name "Possible patterns"; existing tests still pass.
- No hex colours in `PatternList.css`.
- `cd web && npm run lint && npm test && npm run build` passes.

### T093 — Heat calendar: weekday headers and a legend
- status: todo
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/HeatCalendar.tsx, web/src/resident/HeatCalendar.test.tsx
- owner: —
- claimed: —
- pr: —

What: The heat calendar grid has no weekday labels and no key, so a nurse can't tell which column is Monday or what a darker cell means. Read only the two files in `area` and `web/src/index.css` (tokens).
Interface: keep `export default function HeatCalendar({ days })`. Add a header row of seven `role="columnheader"` cells (`Mon` … `Sun`) above the day cells (shift day rows down by one), and below the grid a one-line legend `<p>`: "Darker = more errors that day. Grey = no session." CSS vars only.
Acceptance:
- Vitest: seven column headers in Monday-first order; legend text present; a day still lands in the right weekday column; empty `days` still renders nothing.
- `cd web && npm run lint && npm test && npm run build` passes.

### T094 — Tests: change-detection edge cases
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_change_detection_edges.py (new)
- owner: —
- claimed: —
- pr: —

What: `pipeline/tests/test_change_detection.py` covers the happy paths of the flag rule (SPEC §7: two or more sessions above the baseline threshold within 48 h; one bad session never alerts) but not the boundaries. Read only `pipeline/src/routine_watch/change_detection.py` and the existing test file. Don't edit source; if a boundary case reveals a bug, mark that test `xfail(strict=True, reason=...)` and say so in the PR.
Interface: new test file only.
Acceptance:
- pytest cases: two bad sessions exactly 48 h apart (assert what the code defines and name the test after it); unsorted input gives the same result as sorted; fewer than three history scores gives no baseline/flag; a score exactly equal to the threshold never counts; three bad sessions in 48 h flag.
- `scripts/ci.sh` passes.

### T095 — Tests: hesitation edge cases
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_hesitation_edges.py (new)
- owner: —
- claimed: —
- pr: —

What: Hesitation (a step or gap much longer than this resident's own average) has five tests; boundaries are untested. Read only `pipeline/src/routine_watch/hesitation.py` and `pipeline/tests/test_hesitation.py`. Don't edit source; if a case reveals a bug, mark it `xfail(strict=True, reason=...)` and say so in the PR.
Interface: new test file only.
Acceptance:
- pytest cases: a step id with no history is never flagged; empty input returns an empty list; a duration just above vs just below the threshold; zero-length durations; history for one step doesn't affect another step.
- `scripts/ci.sh` passes.

### T096 — Scenario: stirring three times is perseveration
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/tea_stir_three_times/
- owner: —
- claimed: —
- pr: —

What: Repeating a step is the signal behind the executive pattern (SPEC §7.5, perseveration with intact order). Add a steps-level scenario: a complete, correctly ordered tea session where `stir` happens three times in a row. Read only `tests/scenarios/README.md` and `tests/scenarios/tea_substitution/` (copy its shape). Do not edit `tests/scenarios/README.md` (a later docs task adds the rows).
Interface: `tests/scenarios/tea_stir_three_times/{expected.yaml,steps.jsonl}` with a comment saying what it's for; no history, so `flag: false`.
Acceptance:
- `scripts/e2e.sh tests/scenarios/tea_stir_three_times` passes and asserts the perseveration error(s) on `stir` and no omission/sequence errors.
- `scripts/ci.sh` passes.

### T097 — Scenario: two bad sessions 60 h apart do not flag
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/tea_bad_sessions_far_apart/
- owner: —
- claimed: —
- pr: —

What: Guards the 48 h window end to end: today's bad session (teabag skipped) plus one bad session 60 hours ago and quiet older history must **not** flag. Read only `tests/scenarios/README.md` (the `history:` section) and `tests/scenarios/tea_skip_teabag_pour_twice/` (copy its shape; that one flags with a bad session 30 h ago). Do not edit `tests/scenarios/README.md`.
Interface: `tests/scenarios/tea_bad_sessions_far_apart/{expected.yaml,steps.jsonl}` with a comment saying what it's for; `history:` has at least three quiet sessions plus the 60 h bad one; `flag: false`.
Acceptance:
- `scripts/e2e.sh tests/scenarios/tea_bad_sessions_far_apart` passes; changing 60 to 30 makes it flag (check locally, mention in PR).
- `scripts/ci.sh` passes.

### T098 — scripts/smoke.sh: hit every API route of a running stack
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: scripts/smoke.sh (new)
- owner: ian-claude-standard-2
- claimed: 2026-10-17T06:29Z
- pr: #79

What: The tester and the demo-day checklist need one command that proves a running `scripts/dev.sh up` stack answers correctly, without a browser. Read `scripts/dev.sh`, `scripts/e2e.sh` (style) and the route list in `pipeline/src/routine_watch/api.py`.
Interface: `scripts/smoke.sh [API_URL]` (default `http://localhost:${API_PORT:-8000}`): checks `GET /health`, `GET /residents` (non-empty, `mrs-k` present), `GET /residents/mrs-k`, `GET /alerts`, `GET /alerts/<first id>`, and that the dashboard URL (`DASHBOARD_PORT`, default 5173) returns HTML. Uses `curl` + `python3 -c` for JSON (no `jq`). Prints PASS/FAIL per check, exits non-zero on any failure. Never sets `LIVE_API`. Does not POST feedback (it mutates state).
Acceptance:
- `scripts/dev.sh up && scripts/smoke.sh; scripts/dev.sh down` passes locally (paste output in PR); with the stack down it fails fast (≤10 s) with a clear message.
- `shellcheck scripts/smoke.sh` clean if available; `scripts/ci.sh` passes.

### T099 — Unit overview: one-line status summary at the top
- status: todo
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/overview/UnitOverview.tsx, web/src/overview/UnitOverview.test.tsx
- owner: —
- claimed: —
- pr: —

What: For the 10-second read (SPEC §9), the overview should say up front how many residents need attention. Read only the two files in `area`, `web/src/overview/types.ts` and `web/src/ui/SectionHeader.tsx`.
Interface: above the list render `<p role="status">` with e.g. "2 flagged for review · 1 on watch · 3 normal" (counts from the fetched residents; omit zero parts; "All residents normal" when nothing is flagged or on watch). Nothing while loading. No new fetches.
Acceptance:
- Vitest (stub `fetch` and `await screen.findBy…` per LESSONS): mixed statuses give the right counts; all-normal gives "All residents normal"; existing tests pass.
- `cd web && npm run lint && npm test && npm run build` passes.

### T100 — Feedback store records "what was it?" causes per resident
- status: done
- class: standard
- priority: 2
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/feedback.py, pipeline/tests/test_feedback.py
- owner: ian-claude-standard
- claimed: 2026-10-17T06:29Z
- pr: #80

What: The dashboard now has a "What was it?" picker (#76, SPEC §5 MVP 8). Prepare the backend half without touching contracts or the API (both busy): the store keeps an optional cause per alert and counts causes per resident, which the pattern feedback loop (Nice to have 8) will use later.
Interface: `FeedbackStore.record(alert_id, resident_id, feedback, cause: str | None = None)` (existing callers unchanged); `FeedbackStore.cause_of(alert_id) -> str | None`; `FeedbackStore.cause_counts(resident_id) -> dict[str, int]` counting only `confirmed` alerts; re-recording an alert replaces its cause. Cause ids are free strings (pattern ids or `"other"`). Thresholds behave exactly as before.
Acceptance:
- pytest: cause stored and replaced; false alarms don't count; counts are per resident; existing threshold tests unchanged and passing.
- `scripts/ci.sh` passes.

### T101 — Evidence players: keyboard and screen-reader pass
- status: todo
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/evidence/ReplayPlayer.tsx, web/src/evidence/ReplayPlayer.test.tsx, web/src/evidence/GhostReplay.tsx, web/src/evidence/GhostReplay.test.tsx
- owner: —
- claimed: —
- pr: —

What: The skeleton replay and ghost replay are the evidence a nurse opens "one tap away" (SPEC §9); make them usable without a mouse and honest to screen readers. Read only the files in `area` and `web/src/ui/Button.tsx`.
Interface: play/pause is a real `<button>` with `aria-pressed` or a changing label; the scrubber (if any) has `aria-valuetext` like "12.0 s of 40.0 s"; Space toggles play when the player is focused; the drawing has `role="img"` with an `aria-label` saying what is shown (e.g. "Skeleton replay, today vs usual routine"); respect `prefers-reduced-motion` by not auto-playing. No prop changes that break current callers.
Acceptance:
- Vitest: keyboard toggle works; accessible names present; no autoplay when `matchMedia('(prefers-reduced-motion: reduce)')` matches (stub it).
- `cd web && npm run lint && npm test && npm run build` passes.

### T102 — Docs: README quickstart for teammates and judges
- status: todo
- class: light
- priority: 2
- kind: docs
- deps: —
- area: README.md
- owner: —
- claimed: —
- pr: —

What: Make the top-level README a 1-minute quickstart. Read only `README.md`, `scripts/dev.sh`, `scripts/e2e.sh`, `scripts/ci.sh` (headers only) and SPEC.md §1 and §12.
Interface: sections: what it is (2 lines, "flags a change for review"; never any form of "diagnos*"), run it (`scripts/dev.sh up|down`, ports), test it (`scripts/ci.sh`, `scripts/e2e.sh`), offline by default (`OFFLINE_MODE`, `LIVE_API` unset = fakes, no paid calls), privacy (skeletons and boxes only, no video stored), where things are (pointers to `docs/CODEMAP.md`, `tests/scenarios/README.md`). Under ~80 lines.
Acceptance:
- Every command in it works from a fresh clone (say which you ran in the PR).
- `scripts/ci.sh` passes (test_privacy.py scans wording).

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

### T104 — Session quality: mostly-unclear sessions are unclear, not scored
- status: todo
- class: standard
- priority: 2
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/quality.py (new), pipeline/tests/test_quality.py (new)
- owner: —
- claimed: —
- pr: —

What: SPEC §12/§13: pose and detection are less reliable with walkers, wheelchairs or bad lighting; low-confidence sessions must be treated as unclear rather than as errors, so they never push a resident toward a flag. Add the pure rule now; wiring it into replay/live is a later task (those files are busy).
Interface: `session_quality(events: list[StepEvent], *, unclear_fraction: float = 0.4, min_events: int = 3) -> Literal["ok", "unclear"]`: `unclear` when there are fewer than `min_events` events or more than `unclear_fraction` of them are unclear / below confidence 0.6 (import an existing threshold constant from `recogniser.py` or `verifier.py` if one exists; don't copy it). Module docstring cites SPEC §12. Read `contracts.py` (`StepEvent` only) and `recogniser.py` / `verifier.py` for the constant. Add a one-line note for `docs/CODEMAP.md` in the PR description (don't edit it; it's busy).
Acceptance:
- pytest: clean session → ok; half unclear → unclear; too few events → unclear; exactly at the fraction → ok.
- `scripts/ci.sh` passes.

### T105 — Review: Claude summary guard lets spelled-out numbers through
- status: todo
- class: light
- priority: 2
- kind: bug
- deps: —
- area: pipeline/src/routine_watch/explain_claude.py, pipeline/tests/test_explain_claude.py
- source: reviewer

What: `_passes_guard` only checks digit tokens (`_NUMBER_RE`), so a reply like "Mrs. K made three errors" when she made 2 passes and a nurse sees a wrong count (SPEC §6.4: never state a number not in the facts).
Interface: in `explain_claude.py`, map number words `one`..`twenty` (whole-word, case-insensitive) to digits before the allowed-number check, so they must also be in `_allowed_numbers`. Nothing else changes.
Acceptance:
- tests: fake client replying "three errors" with observed=2 → template fallback; "two errors" with observed=2 → Claude reply kept; "someone" / "once" are not treated as numbers.
- `cd pipeline && uv run pytest -q` passes.
