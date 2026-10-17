# ARCHIVE

Done tasks moved off the board by `tasks.py archive`. Read only when needed.

### T001 — Monorepo scaffold
- status: done
- class: heavy
- priority: 0
- deps: —
- area: repo root, pipeline/, web/, contracts/, scripts/ci.sh
- owner: ian-claude
- claimed: 2026-10-17T03:11Z
- pr: #2

What: Create the project skeleton every later task builds on.
Interface: `pipeline/` Python 3.11 package managed by uv (capture, recogniser, task graph, errors, baseline, FastAPI api); `web/` Vite + React + TypeScript nurse dashboard; `contracts/` shared schemas (empty placeholder + README); `.env.example`. Each has a trivial passing test.
Acceptance:
- `scripts/ci.sh` runs ruff + pytest for pipeline/ and lint/test/build for web/, and passes.
- Short "Layout" section added to README.md describing each dir.

### T002 — Event contracts
- status: done
- class: heavy
- priority: 0
- deps: T001
- area: contracts/, pipeline/routine_watch/contracts.py, web/src/contracts.ts
- owner: ian-claude
- claimed: 2026-10-17T03:22Z
- pr: #4

What: Define the data that flows between stages (SPEC §6, §7, §16): CaptureFrame (the single per-frame JSONL record: timestamp, pose skeleton keypoints, MediaPipe hand landmarks, object boxes; used by live camera, fallback video, tests and scenarios), ObjectDetection, StepEvent (step id, objects, t_start, t_end, confidence, source rule|verifier, unclear flag), TaskError (type ∈ omission|sequence|perseveration|substitution|hesitation|abandonment, step, timestamps, evidence refs, self_corrected), Session (resident, task, start/end, assisted flag, score), Alert (resident, sessions, errors, baseline comparison, summary, suggested checks, feedback).
Interface: JSON Schema files in `contracts/`, matching pydantic models and TS types. No raw frames anywhere.
Acceptance:
- Round-trip test: pydantic model → JSON → validates against schema, for each type.
- `web` type-checks against the TS types.
- A sample `contracts/examples/capture.jsonl` (a few frames) validates against the CaptureFrame schema.

### T003 — Tea task graph definition
- status: done
- class: standard
- priority: 1
- deps: T001
- area: pipeline/src/routine_watch/tasks/, pipeline/tests/test_tea_graph.py
- owner: ian-claude
- claimed: 2026-10-17T03:36Z
- pr: #7

What: The "make tea" dependency graph from SPEC §7 as data plus a loader. Steps: fill kettle, boil, get cup, teabag in cup, pour water, (optional) milk, (optional) sugar, stir, remove teabag. Dependencies, allowed objects per step (spoon|teaspoon), once-only flags, optional flags.
Interface: `tasks/tea.yaml`; `load_task(name) -> TaskGraph` with `deps(step)`, `allowed_objects(step)`, `is_optional(step)`, `valid_orders()` helper for tests.
Acceptance:
- Tests: "fill kettle" and "get cup" in either order are both valid; "pour" requires "teabag in cup"; optional steps can be skipped.

### T004 — Synthetic care-record generator
- status: done
- class: light
- priority: 2
- deps: T001
- area: pipeline/routine_watch/synth/care_records.py, pipeline/tests/test_care_records.py
- owner: ian-claude-light
- claimed: 2026-10-17T03:22Z
- pr: #3

What: Generate fake care-record context for demo residents: medication changes, temperature readings, daily fluid intake. Read only the files in `area` and `pipeline/pyproject.toml`.
Interface: `generate_care_records(resident_id: str, days: int = 14, seed: int = 0, scenario: str = "normal") -> list[dict]`. Each dict: `{"resident_id", "ts" (ISO), "kind": "med_change"|"temperature"|"fluid_intake", "value", "note"}`. Scenario `"spike"`: new antibiotic 2 days before the end, temperature rises to ~38.2 °C in the last day, fluid intake drops. `"normal"`: no med changes, temp 36.4–37.0, fluids 1200–1800 ml/day.
Acceptance:
- Deterministic for a given seed.
- Tests check both scenarios' properties above.
- `cd pipeline && uv run pytest tests/test_care_records.py -q` passes.

### T005 — Scenario replay harness (e2e)
- status: done
- class: heavy
- priority: 1
- deps: T002, T003
- area: scripts/e2e.sh, tests/scenarios/, pipeline/src/routine_watch/replay.py, pipeline/tests/test_replay.py
- owner: ian-claude
- claimed: 2026-10-17T03:45Z
- pr: #12

What: The simulation layer the tester runs. A scenario is a recorded/synthetic capture stream plus the expected outcome; replaying it runs the full pipeline offline.
Interface: `tests/scenarios/<name>/frames.jsonl` (capture records per T002 contracts), `expected.yaml` (`steps: [...]`, `errors: [{type, step}]`, `flag: true|false`, optional `history:` synthetic prior sessions). `python -m routine_watch.replay <dir>` prints a JSON result; `scripts/e2e.sh` runs all scenarios with `OFFLINE_MODE=true`, prints PASS/FAIL per scenario with a diff, exits non-zero on any failure.
Acceptance:
- Two hand-written step-level scenarios to start: `tea_normal` (0 errors) and `tea_skip_teabag_pour_twice` (omission + perseveration). Frame-level generation can stub steps until the recogniser lands; document the stub.
- `scripts/e2e.sh` passes locally and is called from `scripts/ci.sh`.

### T006 — Dev stack script
- status: done
- class: standard
- priority: 1
- deps: T001
- area: scripts/dev.sh, README.md (Run section)
- owner: ian-claude-standard
- claimed: 2026-10-17T04:20Z
- pr: #14

What: One command to bring the whole local stack up and down, used by humans and the tester.
Interface: `scripts/dev.sh up` starts API + dashboard in the background (logs to `.dev/`), waits until healthy, prints `DASHBOARD_URL=...` and `API_URL=...`; `scripts/dev.sh down` stops everything; `scripts/dev.sh status`. Works with no API keys (`OFFLINE_MODE=true`, mock data).
Acceptance:
- `up` then `curl` both URLs return 200, `down` leaves no processes on those ports. Idempotent (`up` twice is fine).

### T007 — Session score weights
- status: done
- class: light
- priority: 1
- deps: —
- area: pipeline/src/routine_watch/scoring.py, pipeline/tests/test_scoring.py
- owner: ian-claude-light
- claimed: 2026-10-17T03:35Z
- pr: #5

What: Turn per-session error counts into one session score (weighted sum, hand-set weights). Read only the files in `area`, `pipeline/src/routine_watch/errors.py` (for `ERROR_TYPES`) and `pipeline/pyproject.toml`. Do not edit errors.py.
Interface: `WEIGHTS: dict[str, float]` = omission 3.0, substitution 3.0, sequence 2.0, perseveration 2.0, abandonment 2.0, hesitation 1.0; `SELF_CORRECTED_WEIGHT = 0.5`; `session_score(counts: Mapping[str, int], self_corrected: int = 0, assisted: bool = False) -> float`. Assisted sessions return 0.0 (they are excluded). Unknown error type raises `ValueError`.
Acceptance:
- `set(WEIGHTS) == set(ERROR_TYPES)`; omission and substitution weigh the most, hesitation the least.
- Tests: empty counts → 0.0; `{"omission": 1, "perseveration": 1}` → 5.0; self-corrected slips add 0.5 each; assisted → 0.0; unknown type raises.
- `cd pipeline && uv run pytest tests/test_scoring.py -q` and `scripts/ci.sh` pass.

### T008 — Per-resident baseline and change flag
- status: done
- class: light
- priority: 1
- deps: —
- area: pipeline/src/routine_watch/change_detection.py, pipeline/tests/test_change_detection.py
- owner: ian-claude-light
- claimed: 2026-10-17T03:36Z
- pr: #6

What: Pure functions that build a resident's baseline from past session scores and decide whether recent sessions flag a change for review. Read only the files in `area`, `pipeline/src/routine_watch/baseline.py` (import `FLAG_MIN_SESSIONS`; do not edit it) and `pipeline/pyproject.toml`.
Interface: `@dataclass(frozen=True) class Baseline: mean: float; std: float; threshold: float`; `build_baseline(scores: list[float], k: float = 2.0, min_std: float = 0.5) -> Baseline` (threshold = mean + k * max(std, min_std); raises `ValueError` on fewer than 3 scores); `flag_change(sessions: list[tuple[datetime, float]], baseline: Baseline, now: datetime, window_h: float = 48.0, min_sessions: int = FLAG_MIN_SESSIONS) -> bool` (True when at least `min_sessions` sessions within `window_h` hours before `now` score above the threshold).
Acceptance:
- Tests: one bad session never flags; two bad sessions 30 h apart flag; two bad sessions 60 h apart do not; sessions at or below threshold never count; all-zero history still gives threshold 1.0 (min_std floor).
- `cd pipeline && uv run pytest tests/test_change_detection.py -q` and `scripts/ci.sh` pass.

### T009 — Synthetic session history generator
- status: done
- class: light
- priority: 2
- deps: T004
- area: pipeline/src/routine_watch/synth/history.py, pipeline/tests/test_history.py
- owner: ian-claude-light
- claimed: 2026-10-17T03:49Z
- pr: #8

What: Fake ~14 days of tea-making sessions per demo resident, used to build baselines (SPEC §8: most residents normal, one sudden spike, one slow drift). Read only the files in `area`, `pipeline/src/routine_watch/synth/__init__.py`, `pipeline/src/routine_watch/errors.py` (for `ERROR_TYPES`) and `pipeline/pyproject.toml`.
Interface: `generate_history(resident_id: str, days: int = 14, seed: int = 0, scenario: str = "normal") -> list[dict]`, one or two sessions per day, sorted by time. Each dict: `{"resident_id", "ts" (ISO 8601 UTC), "task": "tea", "errors": {error_type: count}, "self_corrected": int, "duration_s": float, "assisted": bool}`. `"normal"`: mostly zero errors, at most one hesitation or self-corrected slip on ~20% of sessions. `"spike"`: normal until the last 36 h, then every session has an omission plus a perseveration. `"drift"`: total errors per session trend upward across the whole window, with at most one error per session in the first 3 days.
Acceptance:
- Deterministic for a given seed; unknown scenario raises `ValueError`.
- Tests check each scenario's property above.
- `cd pipeline && uv run pytest tests/test_history.py -q` and `scripts/ci.sh` pass.

### T010 — Error classifier (graph rules)
- status: done
- class: heavy
- priority: 1
- deps: T002, T003
- area: pipeline/src/routine_watch/errors.py, pipeline/tests/test_errors.py
- owner: ian-claude
- claimed: 2026-10-17T04:06Z
- pr: #13

What: Turn one session's step events plus the task graph into TaskErrors for the graph-based types in SPEC §7: omission, sequence, perseveration, substitution, abandonment, plus self-corrected slips. Hesitation is T014 (needs a baseline); do not implement it here.
Interface: `classify_errors(events: list[StepEvent], graph: TaskGraph, *, session_id: str, ended: bool = True, abandon_after_s: float = 120.0, self_correct_window_s: float = 15.0) -> list[TaskError]` in `errors.py` (keep `ERROR_TYPES`). Consumes `routine_watch.contracts.StepEvent/TaskError/EvidenceRef` and `routine_watch.tasks.TaskGraph` (`deps`, `allowed_objects`, `is_optional`, `is_once_only`). Events with `unclear=True` are ignored. Each error's `evidence` points at the StepEvent(s) involved. Deterministic `error_id`s.
Acceptance:
- Tests: valid alternative orders and skipped optional steps → no errors; skip teabag then pour → omission on `teabag_in_cup`; pour twice with steps between → perseveration; stir with a non-allowed object → substitution; a step before its dep with the dep done later → sequence; dep done within `self_correct_window_s` → `self_corrected=True`; gap > `abandon_after_s` with required steps left → abandonment; unclear events never produce errors.
- `cd pipeline && uv run pytest tests/test_errors.py -q` and `scripts/ci.sh` pass. Once T005 is merged, the `tea_skip_teabag_pour_twice` scenario must be driven by this classifier in a follow-up (note it in the PR).

### T011 — Step recogniser state rules
- status: done
- class: heavy
- priority: 1
- deps: T002, T003
- area: pipeline/src/routine_watch/recogniser.py, pipeline/tests/test_recogniser.py, pipeline/tests/fixtures/recogniser/
- owner: ian-claude
- claimed: 2026-10-17T04:23Z
- pr: #20

What: State rules over hand–object interactions that turn a stream of CaptureFrames into timestamped StepEvents with confidence (SPEC §6.2, §16 "Hands"). No verifier calls here: events below `MIN_STEP_CONFIDENCE` are emitted with `unclear=True` and a hook left for the Gemini verifier (later task).
Interface: `recognise(frames: Iterable[CaptureFrame], graph: TaskGraph, *, session_id: str) -> list[StepEvent]` (`source="rule"`). Rules use hand landmarks near object boxes (e.g. hand overlaps teabag box then teabag box overlaps cup box → `teabag_in_cup`; kettle box tilted/over cup → `pour`). Keep thresholds as module constants.
Acceptance:
- Hand-built small JSONL fixtures (generated by a helper in the test, not raw video) for at least: fill kettle, teabag in cup, pour, stir; each recognised with correct ordering and t_start ≤ t_end.
- Ambiguous fixture → event with `unclear=True`, never dropped silently.
- `cd pipeline && uv run pytest tests/test_recogniser.py -q` and `scripts/ci.sh` pass.

### T012 — Demo residents API
- status: done
- class: standard
- priority: 1
- deps: T007, T008, T009, T004
- area: pipeline/src/routine_watch/api.py, pipeline/src/routine_watch/demo.py, pipeline/tests/test_api_residents.py
- owner: ian-claude-standard
- claimed: 2026-10-17T04:24Z
- pr: #15

What: Serve the 3–5 synthetic demo residents (SPEC §8: most normal, one spike, one drift; demo resident "Mrs. K" is the spike) to the dashboard, scored and flagged with the existing pure functions. Offline, no DB yet.
Interface: `demo.py`: `demo_residents() -> list[dict]` built from `synth.history.generate_history`, `synth.care_records.generate_care_records`, `scoring.session_score`, `change_detection.build_baseline/flag_change`. Routes: `GET /residents` → `[{id, name, room, status: "normal"|"watch"|"flagged", scores: [{ts, score}]}]`; `GET /residents/{id}` → that plus `sessions`, `care_records`, `baseline: {mean, std, threshold}`; 404 for unknown id. Status: flagged if `flag_change`, watch if the latest session is above threshold, else normal.
Acceptance:
- Tests via FastAPI TestClient: spike resident is `flagged`, normal residents `normal`, 404 works, output deterministic.
- `cd pipeline && uv run pytest tests/test_api_residents.py -q` and `scripts/ci.sh` pass.

### T013 — Dashboard unit overview screen
- status: done
- class: standard
- priority: 1
- deps: T001
- area: web/src/ (new files under web/src/overview/ and web/src/mock/, plus App.tsx wiring)
- owner: ian-claude-standard
- claimed: 2026-10-17T04:28Z
- pr: #16

What: SPEC §9 screen 1: resident list with a status chip (normal / watch / flagged) and a sparkline of each resident's error score. Visual first; a nurse should read it in 10 s.
Interface: `type ResidentSummary = {id: string; name: string; room: string; status: "normal"|"watch"|"flagged"; scores: {ts: string; score: number}[]}` (same shape as T012's `GET /residents`). `fetchResidents()` calls `${API_URL}/residents` and falls back to `web/src/mock/residents.ts` when the API is unreachable. Sparkline in plain SVG (no chart library). Flagged residents sort first.
Acceptance:
- Vitest + Testing Library: renders all mock residents, chip text/colour per status, flagged first, fallback to mock on fetch failure.
- `cd web && npm test && npm run build` and `scripts/ci.sh` pass.

### T014 — Hesitation detector
- status: done
- class: light
- priority: 2
- deps: —
- area: pipeline/src/routine_watch/hesitation.py, pipeline/tests/test_hesitation.py
- owner: ian-claude-light
- claimed: 2026-10-17T03:57Z
- pr: #9

What: Flag steps or gaps that took much longer than this resident's own average. Read only the files in `area`, `pipeline/src/routine_watch/baseline.py` (import `HESITATION_SIGMA`; do not edit it) and `pipeline/pyproject.toml`.
Interface: `hesitations(durations: Mapping[str, float], history: Mapping[str, Sequence[float]], sigma: float = HESITATION_SIGMA, min_history: int = 3, min_std: float = 1.0) -> list[str]`. `durations` maps a step or gap name to seconds this session; `history` maps the same names to past durations. Returns names (sorted) where `duration > mean + sigma * max(std, min_std)`. Names with fewer than `min_history` past values are never flagged. Population std.
Acceptance:
- Tests: duration well above mean flagged; at/below threshold not; too little history not; `min_std` floor stops flags when history is constant and the new value is only slightly longer; output sorted.
- `cd pipeline && uv run pytest tests/test_hesitation.py -q` and `scripts/ci.sh` pass.

### T015 — Suggested checks rules
- status: done
- class: light
- priority: 2
- deps: —
- area: pipeline/src/routine_watch/checks.py, pipeline/tests/test_checks.py
- owner: ian-claude-light
- claimed: 2026-10-17T03:58Z
- pr: #10

What: Pick the checks an alert suggests to the care team from the care-record context. Read only the files in `area`, `pipeline/src/routine_watch/synth/care_records.py` (for record dict shape; do not edit it) and `pipeline/pyproject.toml`. Never use the word "diagnose".
Interface: `suggest_checks(care_records: list[dict], now: datetime, lookback_h: float = 72.0) -> list[str]`, values from `CHECKS = ("infection_or_uti", "hydration", "medication_review", "cam_screen")`. Rules over records with `ts` within `lookback_h` before `now`: any `temperature` ≥ 37.8 → `infection_or_uti`; any `fluid_intake` < 1000 → `hydration`; any `med_change` → `medication_review`; `cam_screen` always included last. Output order follows `CHECKS`, no duplicates. Records are dicts `{"resident_id","ts" (ISO 8601),"kind","value","note"}`.
Acceptance:
- Tests: `generate_care_records("r1", scenario="spike")` with `now` = end of its window → all four checks; `scenario="normal"` → only `cam_screen`; records older than lookback ignored.
- `cd pipeline && uv run pytest tests/test_checks.py -q` and `scripts/ci.sh` pass.

### T016 — Alert summary template (offline explainer)
- status: done
- class: light
- priority: 2
- deps: —
- area: pipeline/src/routine_watch/explain.py, pipeline/tests/test_explain.py
- owner: ian-claude-light
- claimed: 2026-10-17T04:00Z
- pr: #11

What: The deterministic, offline plain-language alert summary; it is the default fake behind which the Claude explainer will sit later. Uses only the evidence passed in. Read only the files in `area` and `pipeline/pyproject.toml`.
Interface: `class Explainer(Protocol): def summarise(self, errors: list[dict], baseline: dict, context: list[str]) -> str`; `class TemplateExplainer` implementing it. `errors`: `[{"type", "step_id", "t_start"}]` (seconds); `baseline`: `{"observed", "baseline_mean", "baseline_days"}`; `context`: short strings like "new antibiotic started 2 days ago". Output ≤ 3 sentences, e.g. "Flagged for review: 2 errors this session (skipped teabag in cup at 0:42, repeated pour at 1:15) vs 0.2 normally over 14 days. Context: new antibiotic started 2 days ago." Step ids rendered with underscores replaced by spaces.
Acceptance:
- Tests: mentions every error with mm:ss timestamp; includes the baseline comparison; includes context only when given; never contains "diagnos" (case-insensitive) or any fact not in the inputs; empty errors → a "no errors" sentence.
- `cd pipeline && uv run pytest tests/test_explain.py -q` and `scripts/ci.sh` pass.

### T017 — Explainer: name the step, not just the error type
- status: done
- class: light
- priority: 1
- deps: —
- area: pipeline/src/routine_watch/explain.py, pipeline/tests/test_explain.py
- owner: ian-claude-standard
- claimed: 2026-10-17T04:32Z
- pr: #17

What: Review finding on PR #11: `TemplateExplainer` renders only `error["type"]`, so real classifier output (`type="omission"`, `step_id="teabag_in_cup"`) reads "omission at 0:42", which a nurse can't act on. Render type and step together. Read only the files in `area` and `pipeline/pyproject.toml`.
Interface: unchanged `TemplateExplainer.summarise(errors, baseline, context)`. Each error renders as a phrase from a small dict keyed by type, with the step id's underscores replaced by spaces: omission → "skipped {step}", perseveration → "repeated {step}", sequence → "{step} out of order", substitution → "wrong object for {step}", hesitation → "long pause at {step}", abandonment → "stopped before {step}"; unknown types → "{type} at {step}" (underscores → spaces). Then " at m:ss" as now.
Acceptance:
- Update tests to use real types: `{"type":"omission","step_id":"teabag_in_cup","t_start":42}` → contains "skipped teabag in cup at 0:42"; `{"type":"perseveration","step_id":"pour","t_start":75}` → "repeated pour at 1:15"; unknown type falls back; existing "no diagnos", context and empty-errors tests still pass.
- `cd pipeline && uv run pytest tests/test_explain.py -q` and `scripts/ci.sh` pass.

### T018 — Nurse feedback threshold tuning
- status: done
- class: light
- priority: 1
- deps: —
- area: pipeline/src/routine_watch/feedback.py, pipeline/tests/test_feedback.py
- owner: ian-claude-standard
- claimed: 2026-10-17T04:34Z
- pr: #18

What: SPEC MVP 7: a one-tap "confirmed" / "false alarm" on an alert nudges that resident's threshold. Pure in-memory logic; the API route is a later task. Read only the files in `area`, `pipeline/src/routine_watch/contracts.py` (classes `FeedbackVerdict`, `AlertFeedback`; do not edit it) and `pipeline/pyproject.toml`.
Interface: `class FeedbackStore` with `record(alert_id: str, resident_id: str, feedback: AlertFeedback) -> None` (re-recording the same alert_id replaces the earlier verdict), `get(alert_id: str) -> AlertFeedback | None`, and `threshold(resident_id: str, base: float) -> float`. Rule: `base * (1 + FALSE_ALARM_STEP) ** n_false_alarms * (1 - CONFIRMED_STEP) ** n_confirmed`, clamped to `[base * MIN_FACTOR, base * MAX_FACTOR]`; module constants `FALSE_ALARM_STEP = 0.1`, `CONFIRMED_STEP = 0.05`, `MIN_FACTOR = 0.8`, `MAX_FACTOR = 1.5`.
Acceptance:
- Tests: no feedback → base; one false alarm → base*1.1; confirmed lowers it; many false alarms clamp at 1.5×; replacing a verdict for the same alert_id doesn't double count; residents are independent; `get` returns the stored feedback.
- `cd pipeline && uv run pytest tests/test_feedback.py -q` and `scripts/ci.sh` pass.

### T019 — Suggested checks + feedback buttons components
- status: done
- class: light
- priority: 2
- deps: —
- area: web/src/alert/SuggestedChecks.tsx, web/src/alert/FeedbackButtons.tsx, web/src/alert/alert.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T04:37Z
- pr: #19

What: Two small presentational pieces of the alert/evidence view. Read only the files in `area`, `web/src/contracts.ts` (types `SuggestedCheck`, `FeedbackVerdict`; do not edit it), `web/src/App.test.tsx` (test style) and `web/package.json`. Do not edit App.tsx or anything else.
Interface: `SuggestedChecks({checks}: {checks: SuggestedCheck[]})` renders a list with labels: infection_or_uti → "Check for infection / UTI", hydration → "Check hydration", medication_review → "Review recent medication changes", cam_screen → "Run a CAM delirium screen"; renders nothing for an empty list. `FeedbackButtons({value, onChange}: {value?: FeedbackVerdict | null; onChange: (v: FeedbackVerdict) => void})` renders buttons "Confirmed" and "False alarm", calls `onChange` with `"confirmed"`/`"false_alarm"`, and marks the selected one `aria-pressed="true"`. Plain CSS classes, no new dependencies. Never use the word "diagnose".
Acceptance:
- Vitest + Testing Library: four labels render in the given order; empty list renders nothing; each button calls onChange with the right verdict; aria-pressed reflects `value`.
- `cd web && npm test && npm run build` and `scripts/ci.sh` pass.

### T020 — Replay harness uses the real error classifier
- status: done
- class: standard
- priority: 1
- deps: T005, T010, T014
- area: pipeline/src/routine_watch/replay.py, pipeline/tests/test_replay.py
- owner: ian-claude-standard
- claimed: 2026-10-17T04:40Z
- pr: #21

What: Review finding on PR #13: `replay.find_errors` is still the stub T005 shipped. Replace it with `errors.classify_errors` (plus `hesitation.hesitations` where a baseline is available) so `scripts/e2e.sh` exercises the real pipeline.
Interface: delete the stub body; `replay` calls `classify_errors(events, graph, session_id=..., ended=True)`. Keep the public replay CLI/output format unchanged so `scripts/e2e.sh` and `expected.yaml` files still work.
Acceptance:
- All three scenarios in `tests/scenarios/` pass through `scripts/e2e.sh` with the real classifier; no "STUB" section left in replay.py.
- `cd pipeline && uv run pytest tests/test_replay.py -q` and `scripts/ci.sh` pass.

### T021 — Alerts + feedback API
- status: done
- class: standard
- priority: 1
- deps: T012, T015, T016, T018
- area: pipeline/src/routine_watch/alerts.py, pipeline/src/routine_watch/api.py, pipeline/tests/test_api_alerts.py
- owner: ian-claude-standard
- claimed: 2026-10-17T04:46Z
- pr: #24

What: Build `Alert` contracts for flagged demo residents (summary from `TemplateExplainer`, checks from `checks.suggest_checks`, errors from their latest sessions) and expose them plus the one-tap nurse feedback loop (SPEC §5 MVP 5 and 7).
Interface: `alerts.build_alerts(residents) -> list[Alert]`; `GET /alerts`, `GET /alerts/{id}` (404 unknown), `POST /alerts/{id}/feedback` body `{verdict: "confirmed"|"false_alarm", note?}` → records in a module-level `FeedbackStore` and returns the updated alert incl. feedback and the resident's adjusted threshold. In-memory only, no DB. Deterministic alert ids.
Acceptance:
- Mrs. K yields exactly one alert; normal residents none. Summary never contains "diagnos".
- Feedback round-trip test; re-posting replaces the verdict; bad verdict → 422.
- `cd pipeline && uv run pytest tests/test_api_alerts.py -q` and `scripts/ci.sh` pass.

### T022 — Resident detail screen
- status: done
- class: standard
- priority: 2
- deps: T012, T013
- area: web/src/resident/ (except HeatCalendar.*), web/src/overview/UnitOverview.tsx, web/src/App.tsx, web/src/mock/residentDetail.ts, web/src/index.css
- owner: ian-claude
- claimed: 2026-10-17T04:48Z
- pr: #26

What: SPEC §9 screen 2. Clicking a resident in the unit overview opens their detail: baseline chart (score per session, threshold line, today's point highlighted), session list, and context timeline of care records (meds, temperature). Leave a placeholder slot for the heat calendar (T023).
Interface: `fetchResident(id)` → `GET ${apiUrl}/residents/{id}` with mock fallback (same pattern as `web/src/overview/api.ts`); `ResidentDetail({residentId, onBack})`. Simple state-based navigation in App.tsx, no router dependency. Plain SVG, no new deps.
Acceptance:
- Vitest: renders chart, sessions and care records from mock; back button returns to overview; fetch failure falls back to mock.
- `cd web && npm test && npm run build` and `scripts/ci.sh` pass.

### T023 — Heat calendar component
- status: done
- class: light
- priority: 2
- deps: —
- area: web/src/resident/HeatCalendar.tsx, web/src/resident/HeatCalendar.test.tsx
- owner: max-codex-light-1
- claimed: 2026-10-17T04:45Z
- pr: #22

What: Presentational calendar grid of error score per day (SPEC Nice-to-have 2). Read only the files in `area`, `web/src/App.test.tsx` (test style) and `web/package.json`. Do not edit any other file.
Interface: `HeatCalendar({days}: {days: {date: string /* YYYY-MM-DD */; score: number | null}[]})` renders one cell per day in week rows (Mon first), colour from neutral (low/0) to red (high) using inline style or CSS classes, `null` = grey "no session". Each cell has `title` and `aria-label` like "2026-01-03: score 4.5". Empty list renders nothing. No new dependencies.
Acceptance:
- Vitest + Testing Library: correct cell count, aria-labels, null cells marked no session, higher score gets a "hotter" class/colour than lower, empty renders nothing.
- `cd web && npm test && npm run build` and `scripts/ci.sh` pass.

### T024 — Task map component
- status: done
- class: light
- priority: 2
- deps: —
- area: web/src/live/TaskMap.tsx, web/src/live/TaskMap.test.tsx
- owner: max-codex-light-2
- claimed: 2026-10-17T04:46Z
- pr: #23

What: Presentational task-graph map for the live session screen: steps turn green when done, flash red for omission, amber for repeat or sequence. Read only the files in `area`, `web/src/App.test.tsx` (test style) and `web/package.json`. Do not edit any other file.
Interface: `TaskMap({steps, states}: {steps: {id: string; label: string}[]; states: Record<string, 'pending' | 'done' | 'omission' | 'repeat' | 'sequence'>})`. Renders steps in the given order as a horizontal row of boxes with arrows between them; each box has class `step step--<state>` and `data-state`; missing state = pending. Add a `<style>` or CSS module-free class names (green done, red omission with a CSS pulse animation, amber repeat/sequence). No new dependencies.
Acceptance:
- Vitest + Testing Library: steps render in order with labels; each state maps to the right class; missing state is pending.
- `cd web && npm test && npm run build` and `scripts/ci.sh` pass.

### T025 — Skeleton view component
- status: done
- class: light
- priority: 2
- deps: —
- area: web/src/live/SkeletonView.tsx, web/src/live/SkeletonView.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T04:52Z
- pr: #25

What: SVG drawing of one `CaptureFrame` (pose landmarks, hand landmarks, object boxes) for the live session and replay views. Never shows video, only skeleton and boxes (privacy rule). Read only the files in `area`, `web/src/contracts.ts` (types `CaptureFrame`, `Pose`, `HandLandmarks`, `Landmark`, `ObjectDetection`; do not edit it), `web/src/App.test.tsx` and `web/package.json`.
Interface: `SkeletonView({frame, width = 480, height = 360}: {frame: CaptureFrame | null; width?: number; height?: number})`. Landmarks are normalised 0–1; draw circles per landmark, lines for a small fixed set of pose connections (shoulders, arms, torso), hand points, and labelled rectangles for object boxes. `null` frame → "Waiting for camera" text. No new dependencies.
Acceptance:
- Vitest + Testing Library with a hand-built frame: renders one rect + label per object, circles for landmarks; null frame shows the waiting text.
- `cd web && npm test && npm run build` and `scripts/ci.sh` pass.

### T026 — Replay harness uses the real recogniser
- status: done
- class: standard
- priority: 1
- deps: T011, T020
- area: pipeline/src/routine_watch/replay.py, pipeline/tests/test_replay.py, tests/scenarios/README.md, tests/scenarios/tea_no_kettle/
- owner: ian-claude-standard
- claimed: 2026-10-17T04:55Z
- pr: #27

What: Review finding on PR #20/#21: `replay.steps_from_frames` is still the STUB recogniser, so `frames.jsonl` scenarios never exercise `recogniser.recognise` (T011). Replace the stub with the real recogniser and delete the "Stubs" section of the scenarios README.
Interface: `replay.run` calls `recognise(frames, graph, session_id=...)` for `frames.jsonl` scenarios; `steps.jsonl` scenarios unchanged. Remove `STUB_CONFIDENCE`, `touched_objects`, `steps_from_frames` and the stub helpers. Public CLI/output format unchanged.
Acceptance:
- `tea_no_kettle` passes through the real recogniser (fix its `frames.jsonl` only if the recogniser's rules genuinely need different frames; say so in the PR). No "STUB" left in replay.py or README.
- `cd pipeline && uv run pytest tests/test_replay.py -q`, `scripts/e2e.sh` and `scripts/ci.sh` pass.

### T027 — Web alerts API client + mock
- status: done
- class: light
- priority: 1
- deps: —
- area: web/src/alert/api.ts, web/src/alert/api.test.ts, web/src/mock/alerts.ts
- owner: max-codex-light-1
- claimed: 2026-10-17T05:05Z
- pr: #28

What: Dashboard client for the alerts API (already live on the backend). Read only the files in `area`, `web/src/overview/api.ts` (copy its fallback pattern), `web/src/config.ts`, `web/src/contracts.ts` (type `Alert`, `FeedbackVerdict`; do not edit it), `web/src/overview/UnitOverview.test.tsx` (test style) and `web/package.json`. Do not edit any other file.
Interface: `fetchAlerts(): Promise<Alert[]>` → `GET ${apiUrl}/alerts`; `fetchAlert(id): Promise<Alert | null>` → `GET ${apiUrl}/alerts/{id}` (404 → null); `postFeedback(id: string, verdict: FeedbackVerdict, note?: string): Promise<Alert>` → `POST ${apiUrl}/alerts/{id}/feedback` JSON `{verdict, note}`. GETs fall back to `mockAlerts` on network error / non-ok; a failed POST returns the mock alert with `feedback = {verdict, by: "nurse", at: new Date().toISOString(), note}` set locally. `mockAlerts`: one `change_flag` alert for resident `mrs-k` with two errors (`omission` of `teabag_in_cup` at t=42, `perseveration` of `pour` at t=75), baseline `{task_id:"make_tea", metric:"error_score", observed:5, baseline_mean:0.2, baseline_sd:0.4, baseline_days:14, threshold:1.2}`, all four suggested checks, a summary starting "Flagged for review:". Never the word "diagnose".
Acceptance:
- Vitest with `vi.stubGlobal('fetch', ...)`: success paths, fallback on rejection, 404 → null, POST body shape, failed POST sets feedback locally.
- `cd web && npm test && npm run build` and `scripts/ci.sh` pass.

### T029 — Live session WebSocket (scenario-driven)
- status: done
- class: heavy
- priority: 1
- deps: T020
- area: pipeline/src/routine_watch/live.py, pipeline/src/routine_watch/api.py (add the route only), pipeline/tests/test_live.py
- owner: ian-claude
- claimed: 2026-10-17T05:04Z
- pr: #37

What: SPEC §16 B and §10 fallback: one WebSocket carries the live view. For now it plays a recorded scenario through the pipeline in (sped-up) real time, which is also the demo fallback; the camera source plugs into the same generator later.
Interface: `live.session_messages(scenario_dir, speed=1.0) -> AsyncIterator[dict]` yielding `{"type":"frame","frame":CaptureFrame}` (downsampled to ≤10 fps), `{"type":"step","event":StepEvent}`, `{"type":"step_state","states":{step_id: "pending"|"done"|"omission"|"repeat"|"sequence"}}` (matches web `TaskMap`), `{"type":"error","error":TaskError}`, `{"type":"session_end","score":float,"flag":bool,"alert_id":str|None}`. Errors are classified incrementally (`classify_errors(..., ended=False)` per new event, `ended=True` at the end), deduplicated by error_id. Route `WS /ws/live?scenario=<name>&speed=<x>`; unknown scenario → close code 4404. For `steps.jsonl` scenarios, skip frame messages.
Acceptance:
- Tests with FastAPI TestClient websocket and speed=1000: `tea_skip_teabag_pour_twice` yields omission + perseveration errors, step_state shows teabag_in_cup=omission and pour=repeat, session_end flag true; `tea_normal` yields no errors; unknown scenario → 4404.
- `cd pipeline && uv run pytest tests/test_live.py -q` and `scripts/ci.sh` pass.

### T031 — On-disk API response cache + LIVE_API guard
- status: done
- class: light
- priority: 1
- deps: —
- area: pipeline/src/routine_watch/api_cache.py, pipeline/tests/test_api_cache.py
- owner: max-codex-light-2
- claimed: 2026-10-17T05:05Z
- pr: #29

What: Every paid API call (Gemini, Claude) must go through an on-disk cache under `.cache/api/` and only run when `LIVE_API=1`. Read only the files in `area`, `pipeline/src/routine_watch/hesitation.py` (code style) and `pipeline/pyproject.toml`. Standard library only.
Interface: `class LiveApiDisabled(RuntimeError)`; `live_api_enabled() -> bool` (env `LIVE_API == "1"`); `request_key(namespace: str, request: dict) -> str` = sha256 hex of `namespace + json.dumps(request, sort_keys=True, separators=(",", ":"))` (bytes values must be pre-hashed by the caller); `cached_call(namespace, request, fn: Callable[[], dict], cache_dir: Path | None = None) -> dict`: returns the cached JSON at `<cache_dir>/<namespace>/<key>.json` if present; else if not live raises `LiveApiDisabled`; else calls `fn()`, writes the result atomically (tmp file + rename) and returns it. Default `cache_dir` = env `API_CACHE_DIR` or `<repo root>/.cache/api`.
Acceptance:
- Tests (use `tmp_path`, `monkeypatch`): cache hit never calls fn even with LIVE_API=0; miss with LIVE_API=0 raises; miss with LIVE_API=1 calls once then hits; key stable under dict key order; different namespaces don't collide.
- `cd pipeline && uv run pytest tests/test_api_cache.py -q` and `scripts/ci.sh` pass.

### T028 — Alert / evidence view screen
- status: done
- class: standard
- priority: 1
- kind: feature
- deps: T027
- area: web/src/alert/AlertView.tsx, web/src/alert/AlertView.test.tsx, web/src/alert/ErrorList.tsx, web/src/alert/alert.css
- owner: ian-claude-standard
- claimed: 2026-10-17T05:28Z
- pr: #46

What: SPEC §9 screen 4, readable in 10 seconds: plain-language summary on top, baseline comparison ("5.0 vs 0.2 normal over 14 days"), error list with m:ss timestamps and nurse-readable phrases (same wording as `pipeline/src/routine_watch/explain.py`), `SuggestedChecks`, and `FeedbackButtons` wired to `postFeedback`; after feedback show the updated threshold. Each error row has an `onOpenEvidence(error)` callback (replay view comes later). Don't touch App.tsx (T022 owns it); a later task wires navigation.
Interface: `AlertView({alertId, onBack, onOpenEvidence?})` loads via `fetchAlert` (mock fallback); `ErrorList({errors, onOpen})`.
Acceptance:
- Vitest: renders summary, comparison, both mock errors with "0:42"/"1:15", four checks; clicking "False alarm" calls postFeedback and shows the new threshold; no "diagnos" in rendered text.
- `cd web && npm test && npm run build` and `scripts/ci.sh` pass.

### T033 — Slow-drift trend detector
- status: done
- class: light
- priority: 2
- deps: —
- area: pipeline/src/routine_watch/drift.py, pipeline/tests/test_drift.py
- owner: max-codex-light-1
- claimed: 2026-10-17T05:08Z
- pr: #30

What: SPEC Nice-to-have 6: a sustained upward trend in a resident's daily error score over weeks, reported as a trend for review, separate from the sudden-change flag. Read only the files in `area`, `pipeline/src/routine_watch/change_detection.py` (style; do not edit) and `pipeline/pyproject.toml`. Standard library only.
Interface: `@dataclass(frozen=True) class Drift: slope_per_day: float; days: int; trending: bool`; `drift(daily: Sequence[tuple[date, float]], min_days: int = 7, min_slope: float = 0.1) -> Drift`. Slope = Theil–Sen (median of pairwise slopes, x in days). `trending` = `days >= min_days and slope_per_day >= min_slope`. Fewer than 2 points → slope 0, not trending. Input order doesn't matter.
Acceptance:
- Tests: flat series not trending; steady +0.2/day over 14 days trending; one huge spike in an otherwise flat series NOT trending (robustness); 5 days of rising scores not trending (too short); unsorted input same result.
- `cd pipeline && uv run pytest tests/test_drift.py -q` and `scripts/ci.sh` pass.

### T034 — More step-level scenarios
- status: done
- class: light
- priority: 2
- deps: —
- area: tests/scenarios/tea_sequence_error/, tests/scenarios/tea_substitution/, tests/scenarios/tea_unclear_not_error/, tests/scenarios/tea_single_bad_no_flag/
- owner: max-codex-light-2
- claimed: 2026-10-17T05:08Z
- pr: #31

What: Widen e2e coverage of SPEC §7. Read only `tests/scenarios/README.md`, every file in `tests/scenarios/tea_normal/` and `tests/scenarios/tea_skip_teabag_pour_twice/` (copy their style), `pipeline/src/routine_watch/tasks/tea.yaml` and `contracts/step_event.schema.json`. Add four `steps.jsonl` + `expected.yaml` scenarios, each with a header comment saying what it proves. Do not edit any code.
Interface: `tea_sequence_error`: pour before teabag_in_cup, teabag added after → one `sequence` error. `tea_substitution`: stir done with `milk` instead of `spoon` → one `substitution` error. `tea_unclear_not_error`: normal session where teabag_in_cup has confidence 0.4 and `unclear: true` → no errors. `tea_single_bad_no_flag`: the demo bad session with quiet history and NO other recent bad session → errors as usual, `flag: false` (a single bad session never alerts).
Acceptance:
- `scripts/e2e.sh` passes for all scenarios. If the pipeline disagrees with SPEC §7 on one, don't edit code: leave that scenario out and describe the disagreement in the PR body.
- `scripts/ci.sh` passes.

### T035 — Ghost replay overlay component
- status: done
- class: light
- priority: 2
- deps: —
- area: web/src/evidence/GhostReplay.tsx, web/src/evidence/GhostReplay.test.tsx
- owner: max-codex-light-1
- claimed: 2026-10-17T05:11Z
- pr: #32

What: SPEC Nice-to-have 1: today's skeleton drawn over the resident's normal routine at the same moment. Skeleton only, never video. Read only the files in `area`, `web/src/contracts.ts` (types `CaptureFrame`, `Pose`, `Landmark`; do not edit), `web/src/live/TaskMap.test.tsx` (test style) and `web/package.json`. Self-contained SVG; do not import other components.
Interface: `GhostReplay({today, normal, t, width = 480, height = 360}: {today: CaptureFrame[]; normal: CaptureFrame[]; t: number; width?: number; height?: number})`. Picks the frame with the closest `t` from each list; draws the normal pose as grey circles+lines at 40% opacity (`data-layer="normal"`) under today's pose in blue (`data-layer="today"`). Landmarks are normalised 0–1. Pose connections: shoulders 11–12, arms 11–13–15 and 12–14–16, torso 11–23, 12–24, 23–24. Empty list → that layer omitted; both empty → text "No skeleton data". A small legend "Today" / "Usual".
Acceptance:
- Vitest: both layers render with the right circle counts; nearest-t frame chosen; empty normal → only today layer; both empty → text.
- `cd web && npm test && npm run build` and `scripts/ci.sh` pass.

### T036 — Skeleton replay player
- status: done
- class: light
- priority: 2
- deps: T025
- area: web/src/evidence/ReplayPlayer.tsx, web/src/evidence/ReplayPlayer.test.tsx
- owner: max-codex-light-2
- claimed: 2026-10-17T05:11Z
- pr: #34

What: Plays a span of skeleton frames as the "evidence one tap away" for an error. Read only the files in `area`, `web/src/live/SkeletonView.tsx` (import it; do not edit), `web/src/contracts.ts` (type `CaptureFrame`), `web/src/live/TaskMap.test.tsx` and `web/package.json`.
Interface: `ReplayPlayer({frames, autoPlay = false, fps = 10}: {frames: CaptureFrame[]; autoPlay?: boolean; fps?: number})`: renders `SkeletonView` for the current frame, a Play/Pause button, an `<input type="range" aria-label="Replay position">` scrubber, and the current time as m:ss. Uses `setInterval` at `fps`; stops at the end. Empty frames → "No replay available".
Acceptance:
- Vitest with fake timers: play advances frames; pause stops; scrubber jumps; stops at end; empty list text.
- `cd web && npm test && npm run build` and `scripts/ci.sh` pass.

### T040 — Privacy guard test
- status: done
- class: light
- priority: 2
- deps: —
- area: pipeline/tests/test_privacy.py
- owner: max-codex-light-1
- claimed: 2026-10-17T05:14Z
- pr: #36

What: SPEC §8/§12 as a test: nothing that flows between stages or is stored can carry an image, and nothing says "diagnose". Read only `pipeline/tests/test_contracts.py` (style), `contracts/README.md` and the file list of `contracts/` and `tests/scenarios/`. Do not edit any other file.
Interface: pytest only. (1) Walk every `contracts/*.schema.json`; fail if any property name matches `image|frame_bytes|jpeg|png|video|pixels|base64` (case-insensitive) or has `contentEncoding`. (2) Every line of every `tests/scenarios/*/*.jsonl` and `contracts/examples/*.jsonl` is < 20 kB and contains no `data:image` / long base64 run (≥ 200 chars of `[A-Za-z0-9+/=]`). (3) No file under `pipeline/src/` or `web/src/` (excluding tests) contains `diagnos` except in a negation like "never diagnos" / "not diagnos" / "It never diagnoses" — list offenders.
Acceptance:
- Test passes on current main (if it finds a real offender, report it in the PR instead of editing other files, and mark that check `xfail` with the reason).
- `cd pipeline && uv run pytest tests/test_privacy.py -q` and `scripts/ci.sh` pass.

### T039 — Capture process: MediaPipe + local detector → JSONL
- status: done
- class: heavy
- priority: 1
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/capture.py, pipeline/src/routine_watch/detector.py, pipeline/tests/test_capture.py, pipeline/pyproject.toml (optional extra `capture`), .env.example
- owner: ian-claude
- claimed: 2026-10-17T05:21Z
- pr: #54

What: SPEC MVP 1–2 and §16: the privacy boundary. Webcam or video file → MediaPipe pose + hands + local object detector → one `CaptureFrame` JSONL record per frame; frames dropped after processing, never written. Roboflow weights run locally (no hosted inference, no training runs); until weights exist, `FakeDetector` returns no boxes.
Interface: `frame_record(t, pose_landmarks, hand_landmarks, detections, source) -> CaptureFrame` (pure, tested); `class Detector(Protocol): detect(image) -> list[ObjectDetection]`, `FakeDetector`, `LocalDetector(weights_path)` (ONNX/ultralytics, import guarded); `run(source: int | Path, out: Path, fps: int = 15)`; CLI `python -m routine_watch.capture --camera 0 | --video path --out file.jsonl`. Heavy deps (mediapipe, opencv) only in the `capture` extra and imported lazily so CI doesn't need them.
Acceptance:
- Tests (no camera, no mediapipe needed): `frame_record` from fake landmark objects validates against `contracts/capture_frame.schema.json`; output records contain no image/bytes/base64 fields; CLI `--help` works without the extra installed.
- `cd pipeline && uv run pytest tests/test_capture.py -q` and `scripts/ci.sh` pass.

### T042 — Design system: tokens + shared UI primitives
- status: done
- class: standard
- priority: 0
- deps: —
- area: web/src/index.css, web/src/ui/, web/src/ui/*.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T05:06Z
- pr: #33

What: One visual language for every screen so parallel web tasks don't drift. Keep the current calm dark theme; extend it, don't restyle.
Interface: tokens in `web/src/index.css` (colour incl. status normal/watch/flagged and error red/amber/unclear grey, spacing scale, radii, type scale, focus ring); shared components in `web/src/ui/`: `Card`, `StatusChip` (move/replace `overview/StatusChip.tsx`), `Button` (primary/secondary/danger), `SectionHeader`, `EmptyState`, `ErrorState`, `Loading`; `web/src/ui/README.md` with one-line usage each.
Acceptance:
- Existing screens switched to the tokens/components with no visual regressions beyond consistency; no hard-coded hex in components.
- Contrast ≥ 4.5:1 for text tokens; Vitest tests for each component.
- `cd web && npm run lint && npm test && npm run build` passes.

### T043 — Live session screen (WebSocket client + mock stream)
- status: done
- class: standard
- priority: 1
- kind: feature
- deps: —
- area: web/src/live/LiveSession.tsx, web/src/live/useLiveSession.ts, web/src/live/mockLiveStream.ts, web/src/live/LiveSession.test.tsx, web/src/App.tsx (add the nav entry only)
- owner: ian-claude-standard
- claimed: 2026-10-17T05:14Z
- pr: #40

What: SPEC §9 screen 3 and §10 step 3: skeleton view next to the task map; steps turn green, errors flash red (omission) or amber (repeat/sequence). Consumes the T029 WebSocket protocol and falls back to a scripted mock stream, so the screen works before T029 lands and when the API is down.
Interface: `useLiveSession(scenario: string, speed = 1): {frame, states, errors, ended: {score, flag, alert_id} | null, source: "live" | "mock"}` opening `ws(s)://<apiUrl host>/ws/live?scenario=..&speed=..`; messages exactly as T029 (`frame`, `step`, `step_state`, `error`, `session_end`). On connect error / close before any data → replay `mockLiveStream` (a short tea_skip_teabag_pour_twice-like script: a few frames, step_states incl. teabag_in_cup=omission and pour=repeat, two errors, session_end flag true) on timers. `LiveSession` renders the existing `SkeletonView` + `TaskMap`, an error ticker (type + step + m:ss), a "mock data" badge when source=mock, and on a flagged `session_end` a "Flagged for review" banner (never "diagnose").
Acceptance:
- Vitest with a fake WebSocket class: messages update map states and the error list; session_end shows the banner; WS failure falls back to mock with the badge (fake timers).
- `cd web && npm run lint && npm test && npm run build` passes.

### T045 — Privacy & limits panel
- status: done
- class: light
- priority: 2
- deps: —
- area: web/src/about/PrivacyPanel.tsx, web/src/about/PrivacyPanel.test.tsx
- owner: max-codex-light-2
- claimed: 2026-10-17T05:14Z
- pr: #35

What: A small static panel for the demo close (SPEC §10 step 6, §12): what the system stores and doesn't, and its limits. Not wired into App.tsx in this task. Read only the files in `area` and `web/src/live/TaskMap.tsx` (component style).
Interface: `export function PrivacyPanel()` rendering a `<section aria-labelledby>` with heading "Privacy and limits" and these bullets verbatim: "Only skeleton points and object boxes leave the camera. No video is stored."; "No face recognition. Each camera is linked to a room by configuration."; "It flags a change for a nurse to review. It is not a medical assessment."; "Low-confidence moments are shown as unclear, never counted as errors."; "Pose tracking is less accurate with walkers, wheelchairs and unusual postures."; "Residents or their decision-maker opt in, and monitoring can be turned off per room."
Acceptance:
- Vitest: heading and all six bullets render; rendered text never contains "diagnos" (case-insensitive).
- `cd web && npm run lint && npm test && npm run build` passes.

### T046 — Confidence / unclear badge component
- status: done
- class: light
- priority: 2
- kind: feature
- deps: —
- area: web/src/alert/ConfidenceBadge.tsx, web/src/alert/ConfidenceBadge.test.tsx
- owner: max-codex-light-2
- claimed: 2026-10-17T05:26Z
- pr: #43

What: SPEC §12 "show uncertainty": a small badge shown next to a step event or alert. Read only the files in `area` and `web/src/alert/SuggestedChecks.tsx` (style).
Interface: `export function ConfidenceBadge({ confidence, unclear }: { confidence: number; unclear?: boolean })`. `unclear` → text "Unclear" with `title="Low confidence; not counted as an error"`; otherwise confidence ≥ 0.8 → "High confidence", ≥ 0.5 → "Medium confidence", else "Low confidence"; also shows the rounded percentage (e.g. "87%"). Clamp confidence to [0,1]. Set `data-level="high|medium|low|unclear"` for styling; no hard-coded hex (CSS vars only, e.g. `var(--color-unclear)`).
Acceptance:
- Vitest: 0.87 → "High confidence" + "87%"; 0.6 → Medium; 0.2 → Low; unclear wins over any confidence; 1.4 clamps to "100%".
- `cd web && npm run lint && npm test && npm run build` passes.

### T047 — Bug: flaky web CI ("window is not defined" after App.test.tsx)
- status: done
- class: light
- priority: 0
- deps: —
- area: web/src/App.test.tsx, web/src/test-setup.ts, web/vite.config.ts
- owner: max-codex-light-2
- claimed: 2026-10-17T05:17Z
- pr: #38

What: main CI run 39005334024 failed although all 52 web tests passed: Vitest reported an unhandled `ReferenceError: window is not defined` from react-dom, originating in `src/App.test.tsx`. The test renders `<App />` and returns synchronously, while the overview's API fetch (which falls back to mock data when the API is unreachable) resolves after jsdom is torn down and triggers a React update. Timing-dependent, so it fails only sometimes.
Interface: make the test wait for the async work, e.g. stub `fetch` to reject immediately (`vi.stubGlobal('fetch', ...)`) and `await screen.findBy...` for the fallback content, plus `afterEach(cleanup)` / `vi.unstubAllGlobals()`. If other tests render components that fetch, apply the same pattern via a shared `web/src/test-setup.ts` (`setupFiles` in the vite config).
Acceptance:
- Run the web test suite 5 times in a row (`cd web` then the test script, looped); all pass with zero "Unhandled Errors".
- No behaviour assertions change; only async handling.

### T048 — Bug: heat calendar ignores dark theme; dark text on dark-red cell unreadable
- status: done
- class: light
- priority: 1
- deps: —
- area: web/src/resident/HeatCalendar.tsx, web/src/resident/HeatCalendar.test.tsx
- owner: max-codex-light-1
- claimed: 2026-10-17T05:17Z
- pr: #39

What: Tester found on Mrs. K's detail screen (main 7c48d9c) that the "Daily scores" calendar renders as a light-grey/white block inside the dark card, and the highest-score day ("1", score 5) shows near-black text on dark red (fails 4.5:1 contrast). Cause: hard-coded colours in `HeatCalendar.tsx` (`#bdbdbd`, `hsl(0, 80%, L%)`, default text colour). Read only the files in `area` and `web/src/index.css` (tokens; do not edit it).
Interface: `HeatCalendar({days})` unchanged. Cell colours from CSS vars only (e.g. `var(--color-surface-2)` for null/low, mixing toward `var(--color-error)` or flagged-red for high); no hex/hsl literals. Text colour switches to light on high-score cells so every cell meets ≥ 4.5:1. Grid has no light background.
Repro: `scripts/dev.sh up` → open http://localhost:5173 → click Mrs. K → look at "Daily scores". `scripts/dev.sh down`.
Expected: calendar sits in the dark theme; every day number readable. Actual: white block; "1" cell unreadable.
Acceptance:
- Vitest: no inline style contains a hex or `hsl(` literal; high-score cell (score ≥ 4) gets the light-text class/style; existing tests still pass.
- `cd web && npm run lint && npm test && npm run build` passes.

### T030 — Gemini step verifier behind an interface
- status: done
- class: standard
- priority: 2
- kind: feature
- deps: T031
- area: pipeline/src/routine_watch/verifier.py, pipeline/tests/test_verifier.py, pipeline/pyproject.toml
- owner: ian-claude-standard
- claimed: 2026-10-17T05:39Z
- pr: #56

What: SPEC §6.2 and §16 A: when `recogniser.needs_verifier(event)` is true, ask a vision LLM which step happened. Fake by default; Gemini only with `LIVE_API=1`, via `api_cache`, model from `GEMINI_MODEL` (default flash-lite). Images are in-memory JPEG bytes from a ring buffer, never written to disk (the cache stores only the JSON response, keyed by a hash).
Interface: `VerifierResult(step_id: str | None, objects: list[str], confidence: float)`; `class Verifier(Protocol): def verify(self, images: list[bytes], candidates: list[str], timeout_s: float = 3.0) -> VerifierResult | None` (None = unclear); `FakeVerifier(answers: dict | None)`; `GeminiVerifier` (REST via httpx or `google-genai`, max 8 images); `get_verifier()` returns Fake unless `LIVE_API=1` and `GEMINI_API_KEY` set; `resolve(event, verifier, images, candidates) -> StepEvent` sets `source="verifier"` on a confident answer, `unclear=True` on None/timeout/exception.
Acceptance:
- Tests use FakeVerifier and a stubbed HTTP transport only; no network. Timeout/exception → unclear; answer outside `candidates` → unclear.
- `cd pipeline && uv run pytest tests/test_verifier.py -q` and `scripts/ci.sh` pass.

### T049 — Slow-drift trend card component
- status: done
- class: light
- priority: 2
- kind: feature
- deps: —
- area: web/src/resident/DriftCard.tsx, web/src/resident/DriftCard.test.tsx
- owner: max-codex-light-1
- claimed: 2026-10-17T05:27Z
- pr: #44

What: SPEC Nice-to-have 6: show a slow upward trend in a resident's error score, separate from the sudden-change flag. Pure presentational component; not wired into any screen yet. Read only the files in `area`, `web/src/ui/Card.tsx`, `web/src/ui/README.md` and `pipeline/src/routine_watch/drift.py` (the data it will display).
Interface: `export function DriftCard({ slopePerDay, days, trending, minDays = 7 }: { slopePerDay: number; days: number; trending: boolean; minDays?: number })`, built on the `Card` primitive. `days < minDays` → "Not enough history yet (N of 7 days)"; `trending` → heading "Slow drift" and text "Error score rising about +0.15 per day over N days. Flagged for review." (slope to 2 dp); otherwise "No slow drift over N days". Never use the word "diagnose". `data-state="insufficient|trending|stable"`; CSS vars only, no hex.
Acceptance:
- Vitest covers the three states, the 2 dp formatting, and asserts the text never matches /diagnos/i.
- `cd web && npm run lint && npm test && npm run build` passes.

### T051 — Feedback buttons announce the recorded choice
- status: done
- class: light
- priority: 3
- kind: feature
- deps: —
- area: web/src/alert/FeedbackButtons.tsx, web/src/alert/FeedbackButtons.test.tsx
- source: proposed
- owner: max-codex-light-2
- claimed: 2026-10-17T05:38Z
- pr: #53

What: Accessibility (Execution/Clarity): after a tap, screen-reader and sighted users get a confirmation that the verdict was saved. Read only the files in `area`.
Interface: keep the current props. Add a `<p role="status" aria-live="polite">` under the buttons: `value === 'confirmed'` → "Marked as confirmed", `'false_alarm'` → "Marked as false alarm", no value → empty. Wrap the buttons in `role="group"` with `aria-label="Nurse feedback"`. Keep `aria-pressed`.
Acceptance:
- Vitest: group label present; status text for each value; clicking calls `onChange` with the verdict; empty status with no value.
- `cd web && npm run lint && npm test && npm run build` passes.

### T032 — Claude alert summariser behind the Explainer interface
- status: done
- class: standard
- priority: 2
- kind: feature
- deps: T031
- area: pipeline/src/routine_watch/explain_claude.py, pipeline/tests/test_explain_claude.py, pipeline/pyproject.toml
- owner: ian-claude-standard
- claimed: 2026-10-17T05:50Z
- pr: #62

What: SPEC §6.4: Claude writes the plain-language summary from the detected evidence only. Template stays the default and the fallback.
Interface: `ClaudeExplainer(client=None, model=env ANTHROPIC_MODEL or "claude-haiku-4-5")` implementing `explain.Explainer.summarise(errors, baseline, context)`; calls go through `api_cache.cached_call("anthropic", ...)`; prompt forbids diagnosis, speculation and facts not in input. Output guard: if the reply contains "diagnos" (any case), any number or m:ss not present in the template output/inputs, or exceeds 3 sentences, return `TemplateExplainer` output instead. Any exception/timeout → template. `get_explainer()` returns Template unless `LIVE_API=1` and `ANTHROPIC_API_KEY` set.
Acceptance:
- Tests with an injected fake client only: good reply used; "diagnosed" reply rejected; invented timestamp rejected; exception → template; `get_explainer()` default is Template.
- `cd pipeline && uv run pytest tests/test_explain_claude.py -q` and `scripts/ci.sh` pass.

### T053 — Review: offline feedback fallback hides API rejections from the nurse
- status: done
- class: light
- priority: 1
- deps: —
- area: web/src/alert/api.ts, web/src/alert/api.test.ts
- source: reviewer
- owner: max-codex-light-2
- claimed: 2026-10-17T05:23Z
- pr: #41

What: `postFeedback` falls back to writing the verdict into the in-memory mock whenever `response.ok` is false, so a 404/422/500 from a reachable API reports success while the feedback is lost on refresh. Only a network failure (fetch throws) should fall back to the mock. Read only the files in `area`.
Interface: keep the signature. If fetch throws → current mock fallback. If the response is not ok → throw `new Error(`Feedback not saved (${response.status})`)`. Leave `fetchAlerts`/`fetchAlert` as they are (read-only).
Acceptance:
- Vitest: a 500 response rejects and does not mutate `mockAlerts`; a network error still records locally; an ok response returns the API alert.
- `cd web && npm run lint && npm test && npm run build` passes.

### T054 — Review: task map and skeleton view ignore the dark design tokens
- status: done
- class: light
- priority: 1
- kind: improvement
- deps: —
- area: web/src/live/TaskMap.tsx, web/src/live/SkeletonView.tsx, web/src/index.css (add tokens/rules only), web/src/live/TaskMap.test.tsx
- source: reviewer
- owner: max-codex-light-1
- claimed: 2026-10-17T05:23Z
- pr: #42

What: `TaskMap.tsx` injects an inline `<style>` with light-theme hex colours (#f1f5f9 boxes, #dcfce7 done) that glare on the dark dashboard, and `SkeletonView.tsx` hard-codes stroke/fill hex values. Both must use the CSS variables in `web/src/index.css` (`--panel`, `--border`, `--text`, `--error-red-*`, `--error-amber-*`, `--status-normal-*`), like T048 does for the heat calendar. Read only the files in `area`.
Interface: move TaskMap styles into `index.css` under `.task-map` using `var(--…)`; keep class names and the omission pulse. In SkeletonView replace hex literals with `var(--…)` (add `--skeleton-bone`, `--skeleton-box`, `--hand-left`, `--hand-right` to `:root`). No behaviour change.
Acceptance:
- `grep -n '#[0-9a-fA-F]\{3,6\}' web/src/live/TaskMap.tsx web/src/live/SkeletonView.tsx` returns nothing.
- `cd web && npm run lint && npm test && npm run build` passes.

### T055 — Review: session scoring duplicated in replay.py and live.py
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: pipeline/src/routine_watch/replay.py, pipeline/src/routine_watch/live.py, pipeline/tests/test_replay.py, pipeline/tests/test_live.py
- source: reviewer
- owner: max-codex-light-2
- claimed: 2026-10-17T05:29Z
- pr: #45

What: `replay.run` and `live.session_messages` each re-implement session_id selection, `assisted` (≥2 poses in any frame), error counting, `session_score` and `change_flag`, so the e2e verdict and the live demo can drift apart. Extract one helper used by both. Both also crash with IndexError on a scenario with no frames and no events; raise `ReplayError` instead.
Interface: in `replay.py` add `session_id_of(scenario: Scenario) -> str` (raises `ReplayError` when empty) and `score_session(scenario: Scenario, errors: Sequence[TaskError]) -> tuple[float, bool, bool]` returning `(score, assisted, flag)`. `run` and `live.session_messages` use them; output unchanged.
Acceptance:
- New tests: empty scenario raises `ReplayError` from `run` and from `session_messages`.
- `scripts/ci.sh` passes with no change to existing expected outputs.

### T056 — Scenario: tea abandoned mid-task
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/tea_abandoned/, tests/scenarios/README.md
- owner: max-codex-light-1
- claimed: 2026-10-17T05:30Z
- pr: #47

What: No e2e scenario covers abandonment (resident starts tea, then nothing for >120 s with required steps left). Add one, written at step level, so the tester replays it end to end.
Interface: `tests/scenarios/tea_abandoned/{steps.jsonl,expected.yaml}`. Read only: `tests/scenarios/README.md` (format), `tests/scenarios/tea_no_kettle/` (example with history), `pipeline/src/routine_watch/errors.py` lines 50-150 (abandonment rule, `ABANDON_AFTER_S = 120`), `pipeline/tests/test_errors.py` abandonment section. Steps: fill_kettle, get_cup, boil, then a gap >120 s, then one more step (or stop); expected errors include `abandonment` plus whatever omissions the classifier reports (run it and record the real output, don't guess). Give it a `history:` so it flags (two bad sessions within 48 h, ≥3 prior). Add a row to the README table.
Acceptance:
- `scripts/e2e.sh` passes with 8/8 scenarios; `scripts/ci.sh` passes.
- expected.yaml has a header comment explaining the scenario, like the existing ones.

### T057 — Task map legend component
- status: done
- class: light
- priority: 2
- kind: feature
- deps: —
- area: web/src/live/TaskMapLegend.tsx, web/src/live/TaskMapLegend.test.tsx
- owner: max-codex-light-2
- claimed: 2026-10-17T05:32Z
- pr: #48

What: Judges and nurses see red/amber squares on the live task map with no key. Add a small legend explaining each state in plain words (never "diagnose"). Not wired into a screen yet (T043 owns the live screen).
Interface: `export function TaskMapLegend(): JSX.Element` listing the five states of `StepState` in `web/src/live/TaskMap.tsx` (pending "not yet", done "done", omission "missed step", repeat "repeated step", sequence "out of order"), each with a swatch using the same classes/colours as TaskMap.tsx. Read only `web/src/live/TaskMap.tsx`, `web/src/index.css` (design tokens) and `web/src/ui/README.md`. Swatches are decorative (`aria-hidden`); text carries the meaning; rendered as a `<dl>` or `<ul>` with an accessible name "Task map legend".
Acceptance:
- Vitest: renders all five labels; list is reachable by role with name "Task map legend"; no text contains "diagnos".
- `scripts/ci.sh` passes.

### T058 — Review: merge duplicate pipeline modules found by the code map
- status: done
- class: standard
- priority: 1
- kind: improvement
- deps: —
- area: pipeline/src/routine_watch/baseline.py, pipeline/src/routine_watch/change_detection.py, pipeline/src/routine_watch/task_graph.py, pipeline/src/routine_watch/tasks/, pipeline/tests/, docs/CODEMAP.md
- owner: ian-claude-standard
- claimed: 2026-10-17T05:34Z
- pr: #51
- source: reviewer

What: `baseline.py` and `change_detection.py` both describe per-resident baseline/change detection, and `task_graph.py` looks like the T001 placeholder next to the real `tasks/graph.py`. Two homes for one concept confuse every later worker.
Interface: keep one module per concept. Check which one is imported (`grep -rn "baseline\|change_detection\|task_graph" pipeline/ web/ scripts/`); move any real logic into the live module, delete the placeholder, update imports and tests. No behaviour change.
Acceptance:
- `scripts/ci.sh` passes (incl. `scripts/e2e.sh`).
- `python3 scripts/codemap.py pipeline` shows a single baseline/change module and a single task-graph module.
- Remove the "Known overlaps" lines you fixed from `docs/CODEMAP.md`.

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
- status: done
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

### T037 — Skeleton replay API for evidence
- status: done
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
- status: done
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

### T044 — Alert notifier behind an interface (push alert)
- status: done
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

### T070 — Tests for Sparkline and SessionList
- status: done
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

### T072 — Live camera session messages (capture → recogniser → live messages)
- status: done
- class: heavy
- priority: 1
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/live_camera.py, pipeline/tests/test_live_camera.py, docs/CODEMAP.md (notes only)
- owner: —
- claimed: —
- pr: #74
- note: 

What: `/ws/live` only replays recorded scenarios; the demo needs the camera path too (SPEC §10, §16 decision B). Build the generator that turns a live capture stream into the same messages `live.session_messages` yields, so wiring it into the route is a one-line follow-up.
Interface: `async def camera_session_messages(frames: AsyncIterator[CaptureFrame] | Iterable[CaptureFrame], task: str = "tea") -> AsyncIterator[dict]` in `live_camera.py`, reusing `live.py`/`recogniser.py`/`replay.py` helpers (import, don't copy; don't edit `live.py` or `api.py`). Frames come from `capture.record_stream` with `FakeLandmarker`/`FakeDetector` in tests; never store frames.
Acceptance:
- Feeding a recorded scenario's `frames.jsonl` through `camera_session_messages` yields the same step/error/end messages as `session_messages` for that scenario (test over ≥3 scenarios).
- No real camera, network or paid API in tests; `scripts/ci.sh` passes.

### T073 — Review: live screen hard-codes the tea steps instead of the session's task graph
- status: done
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
- status: done
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
- status: done
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
- status: done
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

### T082 — Scenario: medication taken without water is an omission
- status: done
- note: superseded by T041 (#59), which added tests/scenarios/meds_skip_water
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

### T080 — Evidence view: skeleton replay and ghost overlay on the alert screen
- status: done
- class: standard
- priority: 1
- kind: feature
- deps: T037
- area: web/src/alert/AlertView.tsx, web/src/alert/alert.css, web/src/alert/AlertView.test.tsx, web/src/evidence/api.ts, web/src/evidence/api.test.ts, web/src/mock/
- owner: ian-claude-standard
- claimed: 2026-10-17T06:41Z
- pr: #84

What: SPEC §5 MVP 5 and §10 step 5: the alert screen must show the skeleton replay of the flagged moment, with the ghost of the resident's normal routine. `ReplayPlayer` and `GhostReplay` exist in `web/src/evidence/` but no screen uses them. Fetch the replay from the T037 evidence API (offline mock fallback like the other `api.ts` files) and render it in an "Evidence" card on `AlertView`, starting at the first error's `t_start`.
Interface: `web/src/evidence/api.ts` `fetchReplay(alertId: string): Promise<...>` matching T037's route/response (read `pipeline/src/routine_watch/evidence.py` after T037 merges); mock data in `web/src/mock/`.
Acceptance:
- AlertView test: replay card renders with mocked data; loading and error/empty states use `ui/` primitives; no raw video or image elements.
- `cd web && npm test` and `scripts/ci.sh` pass.

### T061 — Live session screen accessibility pass
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/live/LiveSession.tsx, web/src/live/LiveSession.test.tsx, web/src/live/SkeletonView.tsx, web/src/live/SkeletonView.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T06:52Z
- pr: #85

What: The live screen updates continuously but a screen-reader user hears nothing. Announce step completions and raised flags through a polite `aria-live` region (one short sentence per event, e.g. "Step done: fill the kettle"), give the skeleton view a text alternative, and announce connection status changes. Do not touch `TaskMap.tsx` (T057 owns the legend next to it).
Interface: no contract changes; use the existing `useLiveSession` messages.
Acceptance:
- Tests (Testing Library) assert the live region text after a mock step event and after a flag; the skeleton has an accessible name.
- No change to the visual layout.
- `scripts/ci.sh` passes.

### T075 — Review: error-type labels and colours defined three times in the web app
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: T064
- area: web/src/ui/errorTypes.ts (new), web/src/ui/errorTypes.test.ts (new), web/src/live/LiveSession.tsx, web/src/alert/ErrorList.tsx, web/src/resident/format.ts
- source: reviewer
- owner: ian-claude-standard
- claimed: 2026-10-17T06:59Z
- pr: #89

What: `LiveSession.tsx` (`ERROR_LABELS`, `ERROR_COLOR`), `alert/ErrorList.tsx` (phrase + colour maps) and `resident/format.ts` (plain names) each map `ErrorType` separately, so the same error can read or colour differently across screens.
Interface: `web/src/ui/errorTypes.ts` exports `ERROR_TYPE_LABEL: Record<ErrorType, string>`, `ERROR_TYPE_TONE: Record<ErrorType, 'red' | 'amber' | 'grey'>` (SPEC §9 colours) and `describeError(type, stepLabel): string`. The three files import from it; delete their local maps. Visible text may only change where screens disagreed today; note any such change in the PR.
Acceptance:
- Unit test covers every `ErrorType` in all three exports.
- `scripts/ci.sh` passes.

### T081 — Live session result counts toward the resident's flag (demo step 4)
- status: done
- class: heavy
- priority: 1
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/live.py, pipeline/src/routine_watch/session_log.py, pipeline/src/routine_watch/demo.py, pipeline/tests/test_live_flag.py, docs/CODEMAP.md (notes only)
- owner: ian-claude
- claimed: 2026-10-17T06:46Z
- pr: #87

What: SPEC §10 step 4: when a live (or fallback pre-recorded) session for Mrs. K finishes with qualifying errors, it must become one of her sessions, so her sparkline spikes and, being the second qualifying session in the window, the "possible delirium" flag and alert appear on the next `/residents` and `/alerts` fetch. Today `live.py` scores the session but nothing records it.
Interface: new `session_log.py` (in-memory, process-local) `record(resident_id, session: Session) -> None`, `sessions_for(resident_id) -> list[Session]`, `reset()`; `live.py` records the finished session; `demo.py` merges logged sessions into the resident's history before scoring/flagging. Keep it swappable for T038's store later (same shape, no DB here).
Acceptance:
- pytest: playing `tea_skip_teabag_pour_twice` for Mrs. K via `session_messages` then calling `/residents` and `/alerts` (TestClient) shows her flagged with the new session listed; playing `tea_normal` does not flag; `reset()` restores the seeded demo.
- `scripts/e2e.sh` and `scripts/ci.sh` pass.

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

### T050 — Drift endpoint for a resident
- status: done
- class: standard
- priority: 2
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/api.py (add the route only), pipeline/src/routine_watch/demo.py (expose daily scores only if needed), pipeline/tests/test_api_drift.py
- owner: ian-claude-standard
- claimed: 2026-10-17T07:06Z
- pr: #91

What: Back the drift card (T049) with data: `GET /residents/{resident_id}/drift` runs `routine_watch.drift.drift` over that resident's demo sessions, one point per day (mean score per date). The demo "slow drift" resident must come out `trending: true`, Mrs. K and the stable resident `false`.
Interface: response `{"resident_id": str, "slope_per_day": float, "days": int, "trending": bool}`; 404 for unknown resident, same style as `get_resident`.
Acceptance:
- pytest via FastAPI TestClient: 200 shape, 404, drift resident trending, stable resident not trending.
- `scripts/ci.sh` passes.

### T086 — Synthetic history: evening-only worsening resident scenario
- status: done
- class: light
- priority: 2
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/synth/history.py, pipeline/tests/test_history.py
- owner: ian-claude-light-2
- claimed: 2026-10-17T07:05Z
- pr: #90

What: SPEC §8 needs a resident whose errors are concentrated in late-day sessions (sundowning pattern, §7.5). Add an `"evening"` scenario to the history generator.
Interface: `generate_history(resident_id, days, seed, scenario="evening")`; add `"evening"` to `SCENARIOS`. Sessions whose local hour (from `ts`) is ≥ 16 in the last ~7 days get 1–3 errors (sequence/omission/hesitation); morning sessions stay like `"normal"`. Read only `pipeline/src/routine_watch/synth/history.py` and `pipeline/tests/test_history.py`; don't touch `demo.py`.
Acceptance:
- pytest: deterministic for a fixed seed; mean errors of evening sessions in the last 7 days ≥ 3× morning sessions; morning sessions look like `normal`; at least one session before and after 16:00 exists each day (adjust session times only for this scenario if needed).
- `scripts/ci.sh` passes.

### T087 — Synthetic history: motor slowing after a sedating medication
- status: done
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
- status: done
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

### T084 — Pattern library + scorer + Alert.patterns contract (SPEC §7.5)
- status: done
- class: heavy
- priority: 1
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/contracts.py, pipeline/src/routine_watch/patterns.py, pipeline/src/routine_watch/patterns_library.py, pipeline/src/routine_watch/alerts.py, pipeline/tests/test_patterns.py, contracts/, web/src/contracts.ts
- owner: ian-claude
- claimed: 2026-10-17T07:04Z
- pr: #99

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

### T092 — PatternList styles: urgent patterns visually distinct
- status: done
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
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/HeatCalendar.tsx, web/src/resident/HeatCalendar.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T06:37Z
- pr: #83

What: The heat calendar grid has no weekday labels and no key, so a nurse can't tell which column is Monday or what a darker cell means. Read only the two files in `area` and `web/src/index.css` (tokens).
Interface: keep `export default function HeatCalendar({ days })`. Add a header row of seven `role="columnheader"` cells (`Mon` … `Sun`) above the day cells (shift day rows down by one), and below the grid a one-line legend `<p>`: "Darker = more errors that day. Grey = no session." CSS vars only.
Acceptance:
- Vitest: seven column headers in Monday-first order; legend text present; a day still lands in the right weekday column; empty `days` still renders nothing.
- `cd web && npm run lint && npm test && npm run build` passes.

### T094 — Tests: change-detection edge cases
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_change_detection_edges.py (new)
- owner: ian-claude-light-2
- claimed: 2026-10-17T07:09Z
- pr: #92

What: `pipeline/tests/test_change_detection.py` covers the happy paths of the flag rule (SPEC §7: two or more sessions above the baseline threshold within 48 h; one bad session never alerts) but not the boundaries. Read only `pipeline/src/routine_watch/change_detection.py` and the existing test file. Don't edit source; if a boundary case reveals a bug, mark that test `xfail(strict=True, reason=...)` and say so in the PR.
Interface: new test file only.
Acceptance:
- pytest cases: two bad sessions exactly 48 h apart (assert what the code defines and name the test after it); unsorted input gives the same result as sorted; fewer than three history scores gives no baseline/flag; a score exactly equal to the threshold never counts; three bad sessions in 48 h flag.
- `scripts/ci.sh` passes.

### T095 — Tests: hesitation edge cases
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_hesitation_edges.py (new)
- owner: ian-claude-light-2
- claimed: 2026-10-17T07:12Z
- pr: #94

What: Hesitation (a step or gap much longer than this resident's own average) has five tests; boundaries are untested. Read only `pipeline/src/routine_watch/hesitation.py` and `pipeline/tests/test_hesitation.py`. Don't edit source; if a case reveals a bug, mark it `xfail(strict=True, reason=...)` and say so in the PR.
Interface: new test file only.
Acceptance:
- pytest cases: a step id with no history is never flagged; empty input returns an empty list; a duration just above vs just below the threshold; zero-length durations; history for one step doesn't affect another step.
- `scripts/ci.sh` passes.

### T096 — Scenario: teabag added three times is perseveration, stirring twice is not
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/tea_teabag_three_times/
- owner: ian-claude-light-2
- claimed: 2026-10-17T07:21Z
- pr: #97
- note: rewritten by orchestrator: stir is once_only:false in tea.yaml by design (repeat stirring is normal), so use teabag_in_cup (once_only default true) instead.

What: Repeating a once-only step after other steps is the signal behind the executive pattern (SPEC §7.5, perseveration with intact order). Add a steps-level scenario: a complete, correctly ordered tea session where `teabag_in_cup` is done again after `pour` and once more after `stir`, and `stir` itself happens twice (which must NOT count). Read only `pipeline/src/routine_watch/tasks/tea.yaml` (the `once_only` comment at the top), `tests/scenarios/tea_kettle_twice/` and `tests/scenarios/tea_substitution/` (copy their shape). Do not edit `tests/scenarios/README.md` or `tea.yaml`.
Interface: `tests/scenarios/tea_teabag_three_times/{expected.yaml,steps.jsonl}` with a comment saying what it's for; no history, so `flag: false`.
Acceptance:
- `scripts/e2e.sh tests/scenarios/tea_teabag_three_times` passes and asserts perseveration error(s) on `teabag_in_cup` only, none on `stir`, and no omission/sequence errors.
- `scripts/ci.sh` passes.

### T097 — Scenario: two bad sessions 60 h apart do not flag
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/tea_bad_sessions_far_apart/
- owner: ian-claude-light-2
- claimed: 2026-10-17T07:17Z
- pr: #95

What: Guards the 48 h window end to end: today's bad session (teabag skipped) plus one bad session 60 hours ago and quiet older history must **not** flag. Read only `tests/scenarios/README.md` (the `history:` section) and `tests/scenarios/tea_skip_teabag_pour_twice/` (copy its shape; that one flags with a bad session 30 h ago). Do not edit `tests/scenarios/README.md`.
Interface: `tests/scenarios/tea_bad_sessions_far_apart/{expected.yaml,steps.jsonl}` with a comment saying what it's for; `history:` has at least three quiet sessions plus the 60 h bad one; `flag: false`.
Acceptance:
- `scripts/e2e.sh tests/scenarios/tea_bad_sessions_far_apart` passes; changing 60 to 30 makes it flag (check locally, mention in PR).
- `scripts/ci.sh` passes.

### T088 — Alert screen shows ranked possible patterns
- status: done
- class: standard
- priority: 1
- kind: feature
- deps: T084, T085
- area: web/src/alert/AlertView.tsx, web/src/alert/AlertView.test.tsx, web/src/alert/PatternList.tsx, web/src/mock/alerts.ts
- owner: ian-claude-standard-2
- claimed: 2026-10-17T07:32Z
- pr: #103

What: SPEC §9 screen 4 / demo step 5: the alert view shows "Possible patterns" right under the summary, from `Alert.patterns`.
Interface: switch `PatternList` to the generated `PatternMatch` type from `web/src/contracts.ts` (drop the local `PatternView` or alias it); render it in `AlertView` between summary and error list; give mock Mrs. K alert a `sudden_change` top pattern with evidence and rule-out checks.
Acceptance:
- Vitest: AlertView renders the top pattern name and its checks; an alert with `patterns: []` shows "no clear pattern".
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
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/overview/UnitOverview.tsx, web/src/overview/UnitOverview.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T07:25Z
- pr: #100

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

### T076 — Tests for ContextTimeline and BaselineChart
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/resident/ContextTimeline.test.tsx, web/src/resident/BaselineChart.test.tsx
- owner: max_API_light
- claimed: 2026-10-17T07:44Z
- pr: #110

What: Both resident-detail components have no tests. Add focused render tests; do not change the components.
Interface: read only web/src/resident/ContextTimeline.tsx, web/src/resident/BaselineChart.tsx, web/src/resident/types.ts, and web/src/resident/format.test.ts (for test style). Use vitest + @testing-library/react like the existing tests.
Acceptance:
- ContextTimeline: empty list shows "No care records for this resident."; records render newest first; temperature/fluid_intake/med_change get their readable labels ("Temperature 37.9 °C", "Fluid intake 800 ml", "Medication change: ...").
- BaselineChart: renders without crashing for typical props and for an empty series (no NaN in rendered attributes).
- note: released by orchestrator: stale claim (>90 min, no PR)
- `cd web && npm test -- --run` and `scripts/ci.sh` pass.

### T101 — Evidence players: keyboard and screen-reader pass
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/evidence/ReplayPlayer.tsx, web/src/evidence/ReplayPlayer.test.tsx, web/src/evidence/GhostReplay.tsx, web/src/evidence/GhostReplay.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T06:52Z
- pr: #86

What: The skeleton replay and ghost replay are the evidence a nurse opens "one tap away" (SPEC §9); make them usable without a mouse and honest to screen readers. Read only the files in `area` and `web/src/ui/Button.tsx`.
Interface: play/pause is a real `<button>` with `aria-pressed` or a changing label; the scrubber (if any) has `aria-valuetext` like "12.0 s of 40.0 s"; Space toggles play when the player is focused; the drawing has `role="img"` with an `aria-label` saying what is shown (e.g. "Skeleton replay, today vs usual routine"); respect `prefers-reduced-motion` by not auto-playing. No prop changes that break current callers.
Acceptance:
- Vitest: keyboard toggle works; accessible names present; no autoplay when `matchMedia('(prefers-reduced-motion: reduce)')` matches (stub it).
- note: released by ian-claude-standard-2: run ended without progress
- `cd web && npm run lint && npm test && npm run build` passes.

### T102 — Docs: README quickstart for teammates and judges
- status: done
- class: light
- priority: 2
- kind: docs
- deps: —
- area: README.md
- owner: ian-claude-light-2
- claimed: 2026-10-17T07:40Z
- pr: #106

What: Make the top-level README a 1-minute quickstart. Read only `README.md`, `scripts/dev.sh`, `scripts/e2e.sh`, `scripts/ci.sh` (headers only) and SPEC.md §1 and §12.
Interface: sections: what it is (2 lines, "flags a change for review"; never any form of "diagnos*"), run it (`scripts/dev.sh up|down`, ports), test it (`scripts/ci.sh`, `scripts/e2e.sh`), offline by default (`OFFLINE_MODE`, `LIVE_API` unset = fakes, no paid calls), privacy (skeletons and boxes only, no video stored), where things are (pointers to `docs/CODEMAP.md`, `tests/scenarios/README.md`). Under ~80 lines.
Acceptance:
- Every command in it works from a fresh clone (say which you ran in the PR).
- `scripts/ci.sh` passes (test_privacy.py scans wording).

### T104 — Session quality: mostly-unclear sessions are unclear, not scored
- status: done
- class: standard
- priority: 2
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/quality.py (new), pipeline/tests/test_quality.py (new)
- owner: ian-claude-standard
- claimed: 2026-10-17T06:33Z
- pr: #82

What: SPEC §12/§13: pose and detection are less reliable with walkers, wheelchairs or bad lighting; low-confidence sessions must be treated as unclear rather than as errors, so they never push a resident toward a flag. Add the pure rule now; wiring it into replay/live is a later task (those files are busy).
Interface: `session_quality(events: list[StepEvent], *, unclear_fraction: float = 0.4, min_events: int = 3) -> Literal["ok", "unclear"]`: `unclear` when there are fewer than `min_events` events or more than `unclear_fraction` of them are unclear / below confidence 0.6 (import an existing threshold constant from `recogniser.py` or `verifier.py` if one exists; don't copy it). Module docstring cites SPEC §12. Read `contracts.py` (`StepEvent` only) and `recogniser.py` / `verifier.py` for the constant. Add a one-line note for `docs/CODEMAP.md` in the PR description (don't edit it; it's busy).
Acceptance:
- pytest: clean session → ok; half unclear → unclear; too few events → unclear; exactly at the fraction → ok.
- `scripts/ci.sh` passes.

### T105 — Review: Claude summary guard lets spelled-out numbers through
- status: done
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
- owner: ian-claude-light-2
- claimed: 2026-10-17T07:43Z
- pr: #109
- `cd pipeline && uv run pytest -q` passes.

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

### T071 — Tests for useLiveSession and mockLiveStream
- status: done
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

### T109 — Resident detail: not-found, API-down and no-sessions states
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/ResidentDetail.tsx, web/src/resident/ResidentDetail.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T07:59Z
- pr: #120
- note: WIP from a session that ended early is on branch task/T109-wip (ResidentDetail.tsx + test): start from it: git switch task/T109-wip && git merge origin/main
- rating: 5/5 clear

What: The resident screen must stay legible when things go wrong: an unknown resident id, the API being unreachable, or a resident with no sessions yet. A nurse should understand each state in 10 s.
Interface: `ResidentDetail` only; reuse the existing `web/src/resident/api.ts` fetch (do not change it) and existing CSS classes/design tokens.
Acceptance:
- 404 → "Resident not found" with a link back to the unit overview.
- network/5xx error → short plain message + a "Try again" button that refetches.
- zero sessions → empty-state copy instead of blank charts (no crash in BaselineChart/HeatCalendar).
- Tests for all three states in ResidentDetail.test.tsx; `scripts/ci.sh` passes.

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

### T115 — Docs: CODEMAP notes for drift endpoint, evidence sources, smoke.sh, feedback causes
- status: done
- class: light
- priority: 2
- kind: docs
- deps: —
- area: docs/CODEMAP.md
- owner: ian-claude-light-2
- claimed: 2026-10-17T07:58Z
- pr: #119
- rating: 5/5 clear

What: Recent merges (T050 drift endpoint, T107 evidence replays `tea_no_kettle` with a `tea_normal` ghost, T098/T108 `scripts/smoke.sh`, T100 feedback causes) aren't in the CODEMAP notes. Add 1–3 lines each.
Interface: notes only; read the module docstrings of `pipeline/src/routine_watch/{api,evidence,feedback,drift}.py` and the header of `scripts/smoke.sh`. Run `python3 scripts/codemap.py` to regenerate the file list.
Acceptance:
- Each of the four is described where a newcomer would look; no stale claims (e.g. "evidence replays one scenario").
- `scripts/ci.sh` passes.

### T116 — Scenario: pill taken before the water is poured is a sequence error
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/meds_pill_before_water/
- owner: max_API_light
- claimed: 2026-10-17T08:00Z
- pr: #121
- rating: 5/5 clear

What: The second task has only a normal and an omission scenario. Add a step-level scenario where the pill is taken before the glass is filled, producing exactly one sequence error.
Interface: `steps.jsonl` + `expected.yaml` in the same format as `tests/scenarios/meds_skip_water/`. Read only `pipeline/src/routine_watch/tasks/meds.yaml`, `tests/scenarios/meds_skip_water/*` and `tests/scenarios/tea_sequence_error/*`.
Acceptance:
- `scripts/e2e.sh` passes with the new scenario listed; the error list is exactly one sequence error on the correct step.
- Note in the PR that `tests/scenarios/README.md` needs a row (outside area; the orchestrator will batch README rows).

### T117 — Web mock residents include the evening and motor residents
- status: done
- class: light
- priority: 2
- kind: feature
- deps: T111
- area: web/src/mock/residents.ts, web/src/mock/residentDetail.ts
- owner: max_API_light
- claimed: 2026-10-17T08:05Z
- pr: #125
- rating: 5/5 clear

What: The offline web fallback should show the same residents as the API after T111. Add the two new residents (same ids, names, rooms, status) to the web mocks.
Interface: mirror the ids/names from `pipeline/src/routine_watch/demo.py`; keep the existing mock shape.
Acceptance:
- vitest: mock list ids equal the API demo ids (hard-coded list in the test, with a comment pointing at demo.py).
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
- status: done
- class: standard
- priority: 1
- kind: bug
- deps: —
- area: pipeline/src/routine_watch/alerts.py, pipeline/tests/test_alerts*.py
- owner: ian-claude-standard-2
- claimed: 2026-10-17T07:53Z
- pr: #123
- source: tester
- rating: 5/5 clear

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
