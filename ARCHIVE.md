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

### T103 — Room monitoring pause toggle (component only)
- status: done
- class: light
- priority: 3
- kind: feature
- deps: —
- area: web/src/about/MonitoringToggle.tsx (new), web/src/about/MonitoringToggle.test.tsx (new)
- source: proposed
- owner: max_API_light
- claimed: 2026-10-17T08:15Z
- pr: #134
- rating: 5/5 clear

What: Responsible design made visible for judges (SPEC §12: "per room and can be turned off"): a per-room monitoring on/paused switch. Component only; wiring and API are later tasks. Read only `web/src/about/PrivacyPanel.tsx` (style) and `web/src/ui/Button.tsx`.
Interface: `export function MonitoringToggle({ room, on, onChange }: { room: string; on: boolean; onChange: (on: boolean) => void })` renders `<button role="switch" aria-checked={on}>` labelled "Monitoring in room {room}" with visible text "On" / "Paused", plus when paused a note "No camera data is processed while paused." CSS vars only.
Acceptance:
- Vitest: role switch with correct `aria-checked`; click calls `onChange(!on)`; paused note shows only when off.
- `cd web && npm run lint && npm test && npm run build` passes.

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

### T068 — Show the demo-data banner in the app
- status: done
- class: light
- priority: 3
- kind: feature
- deps: T052, T063
- area: web/src/App.tsx, web/src/App.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T08:22Z
- pr: #135
- rating: 5/5 clear

What: Render the `DemoBanner` component from T052 (`web/src/ui/DemoBanner.tsx`) once, at the top of `App.tsx` above the header, on every screen.
Interface: read only `App.tsx`, `App.test.tsx`, `ui/DemoBanner.tsx`.
Acceptance:
- App test: banner visible on overview and after opening a resident.
- `scripts/ci.sh` passes.

### T106 — Evidence replay: stop fetching the alert twice
- status: done
- class: light
- priority: 3
- kind: improvement
- deps: —
- area: web/src/evidence/api.ts, web/src/evidence/api.test.ts, web/src/alert/AlertView.tsx
- owner: max_API_light
- claimed: 2026-10-17T08:23Z
- pr: #139
- rating: 5/5 clear

What: Since T080 (#84), `AlertView` loads the alert with `fetchAlert`, then `fetchReplay(alertId)` calls `fetchAlert` again for the same alert. Change `fetchReplay` to take the already-loaded `Alert` so the screen makes one alert request.
Interface: `fetchReplay(alert: Alert): Promise<EvidenceReplay | null>` in `web/src/evidence/api.ts`; in `AlertView.tsx`, run the replay effect once the alert has loaded (keyed on alert id). Read only these three files plus `web/src/alert/AlertView.test.tsx`.
Acceptance:
- `api.test.ts` updated to pass an `Alert`; no `fetchAlert` call inside `evidence/api.ts`.
- AlertView still shows Loading / Empty / replay states as before (existing tests pass unchanged in behaviour).
- `cd web && npm test` and `scripts/ci.sh` pass.

### T129 — Feedback "what was it?" cause reaches the API (contract + API + web)
- status: done
- class: heavy
- priority: 2
- kind: feature
- deps: —
- area: contracts/alert.schema.json, contracts/examples/, pipeline/src/routine_watch/contracts.py, pipeline/src/routine_watch/api.py, pipeline/tests/test_api_alerts.py, web/src/contracts.ts, web/src/alert/api.ts, web/src/alert/api.test.ts, web/src/alert/FeedbackButtons.tsx, web/src/alert/FeedbackButtons.test.tsx
- owner: ian-claude
- claimed: 2026-10-17T08:17Z
- pr: #140
- rating: 4/5 area list left out AlertView.tsx/AlertView.test.tsx/alert.css (the picker's only consumer, so the cause can't reach the API without them), and 'the example alert' doesn't exist: contracts/examples/ has only capture.jsonl

What: SPEC §5 MVP 8. The "what was it?" picker (T090) and the per-resident cause store (T100) exist, but the contract and `POST /alerts/{id}/feedback` have no `cause`, so the nurse's answer is dropped. Wire it end to end.
Interface: optional `cause` (a pattern_id from `patterns_library`, or `"other"`, or null) on `AlertFeedback` in `contracts/alert.schema.json` + `contracts.py` + `web/src/contracts.ts`; `AlertFeedbackIn.cause` validated against known pattern ids (422 otherwise); API calls the FeedbackStore cause-recording method from T100; web `postFeedback` sends the picked cause. Update every consumer and the example alert.
Acceptance:
- API test: posting `{verdict: "confirmed", cause: "sudden_change"}` returns the alert with `feedback.cause == "sudden_change"` and the store has it for mrs-k; unknown cause → 422; omitting cause still works.
- Web test: picking a cause then confirming sends it in the request body.
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
- status: done
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
- status: done
- class: light
- priority: 3
- kind: test
- deps: T139
- area: tests/test_scenarios_readme.py
- owner: ian-claude-standard
- claimed: 2026-10-17T08:24Z
- pr: #137
- rating: 4/5 clear; one gap: the acceptance criterion 'scripts/ci.sh ... runs the new test' doesn't hold on this repo since root tests/ has no pyproject.toml and ci.sh never executes them (same as pre-existing test_tasks_py.py), so the task instructions anticipated this correctly

What: The scenario README keeps falling behind new scenarios (T065, T139). Add a pytest that fails when a scenario directory has no row in the README, so CI catches it.
Interface: New file `tests/test_scenarios_readme.py`: list dirs in `tests/scenarios/` that contain `expected.yaml`; assert each name appears in `tests/scenarios/README.md`. Read only `tests/scenarios/README.md` and `tests/test_tasks_py.py` (for how root tests are written and run).
Acceptance:
- Passes on main after T139; deleting a row makes it fail with the missing scenario's name in the message.
- `scripts/ci.sh` passes and runs the new test (if it doesn't, say so in the PR; don't edit ci.sh).

### T089 — Unit overview shows the top pattern for flagged/watch residents
- status: done
- class: standard
- priority: 2
- kind: feature
- deps: T084
- area: pipeline/src/routine_watch/demo.py, pipeline/src/routine_watch/api.py, pipeline/tests/test_api_residents.py, web/src/overview/, web/src/mock/residents.ts
- owner: ian-claude-standard-2
- claimed: 2026-10-17T08:33Z
- pr: #149
- rating: 5/5 clear

What: SPEC §9 screen 1 and demo step 6 ("Mr. D on watch, slow drift"): each flagged or watch resident row shows its top pattern name next to the status chip.
Interface: `GET /residents` items gain `top_pattern: {pattern_id, name, urgency} | null` from T084's scorer; `web/src/overview/types.ts` `ResidentSummary.top_pattern`; `UnitOverview` renders it as text (not colour alone); normal residents show nothing.
Acceptance:
- pytest: Mrs. K's `top_pattern.pattern_id == "sudden_change"`, drift resident's is `slow_drift`, normal residents `null`.
- Vitest: row shows pattern text for flagged resident, none for normal.
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

### T114 — api.py: one resident lookup helper instead of copy-pasted loops
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: pipeline/src/routine_watch/api.py, pipeline/tests/test_api_residents.py
- owner: ian-claude-light-2
- claimed: 2026-10-17T08:45Z
- pr: #153
- rating: 5/5 clear

What: `get_resident`, `resident_drift` and the replay routes each loop over `demo_residents()` and raise the same 404. Extract `_resident_or_404(resident_id) -> dict` and use it everywhere. No behaviour change.
Interface: private helper in `api.py`; routes and responses unchanged. Read only `api.py` and `pipeline/tests/test_api*.py`.
Acceptance:
- No remaining `for resident in demo_residents()` loops in route bodies.
- New test: every resident-scoped route returns 404 with `{"detail": "resident not found"}` for an unknown id.
- `scripts/ci.sh` passes.

### T130 — Pattern feedback loop: nurse causes re-weight that resident's pattern ranking
- status: done
- class: heavy
- priority: 3
- kind: feature
- deps: T129
- area: pipeline/src/routine_watch/patterns.py, pipeline/src/routine_watch/alerts.py, pipeline/src/routine_watch/feedback.py, pipeline/tests/test_pattern_feedback.py
- owner: ian-claude
- claimed: 2026-10-17T08:32Z
- pr: #151
- rating: 4/5 clear on the mechanism; the false-alarm half needs the alert's top pattern at record time, which only api.py can pass - the area didn't list it

What: SPEC §5 Nice to have 8. Causes a nurse confirmed for a resident nudge that pattern's weight up for her next alerts (and a false alarm on a top pattern nudges it down), bounded so one answer can't flip the ranking alone.
Interface: `FeedbackStore.pattern_weights(resident_id) -> dict[str, float]` (default 1.0, clamped e.g. 0.7–1.3); `score_patterns(..., weights=None)` multiplies confidence before the threshold/sort; `build_alerts` passes the resident's weights. Evidence line notes "weighted by N past nurse answers" when weight ≠ 1.
Acceptance:
- Tests: no feedback → identical ranking to today; two confirmed `slow_drift` causes raise its confidence for that resident only; weights stay within bounds after many answers.
- Wording stays "consistent with"; no "diagnose".
- `scripts/ci.sh` passes.

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

### T156 — Bug: overview and Alerts list don't update when the live session flags Mrs. K
- status: done
- class: standard
- priority: 1
- kind: bug
- deps: —
- area: web/src/App.tsx, web/src/App.test.tsx, web/src/overview/UnitOverview.tsx, web/src/overview/UnitOverview.test.tsx
- source: tester
- owner: ian-claude-standard-2
- claimed: 2026-10-17T08:46Z
- pr: #155
- rating: 5/5 clear

What: After the live session ends with a flag (the "Open alert" button appears and `/alerts` now returns `alert-mrs-k`), the unit overview still shows Mrs. K as "Watch", the status line still says "4 on watch · 2 normal", and the Alerts list stays empty until a page reload. The demo beat "alert appears after the second bad session" only shows via the banner button.
Interface: when the live stream reports `session_end` (or a flag), App refetches `fetchAlerts()` and the overview refetches `fetchResidents()` (e.g. a `refreshKey` prop bumped by App).
Repro: `OFFLINE_MODE=true scripts/dev.sh up`, open http://localhost:5173, wait for the live session to finish with a flag; Mrs. K chip and Alerts list don't change.
Acceptance:
- test: a mocked live session ending with a flag triggers a second fetch of residents and alerts and the Flagged chip / alert row render.
- `cd web && npx vitest run` and `scripts/ci.sh` pass.

### T143 — Pattern scenario: motor slowing after a sedating medication
- status: done
- class: standard
- priority: 2
- kind: test
- deps: T157
- area: tests/scenarios/pattern_motor_slowing/
- owner: ian-claude-standard-2
- claimed: 2026-10-17T08:54Z
- pr: #162
- note: orch: was blocked because replay.py never passes duration_s, so durations_up is unreachable in scenarios. T157 adds scenario durations; after it this is data-only (use the new duration fields).
- rating: 5/5 clear, T157 unblocked it exactly as described

What: Same as T142 for SPEC §7.5's `motor_slowing` pattern: slower steps and hesitation without new sequence errors.
Interface: `tests/scenarios/pattern_motor_slowing/{steps.jsonl,expected.yaml}` in the format of `tests/scenarios/pattern_slow_drift/`, `top_pattern: motor_slowing`. Read the `motor_slowing` entry in `pipeline/src/routine_watch/patterns_library.py` for its signals. Don't change pipeline code; if unreachable without code changes, set blocked with the reason.
Acceptance:
- `scripts/e2e.sh` passes with the new scenario and `top_pattern: motor_slowing`.
- Header comment in expected.yaml explains the shape in 2-4 lines.

### T157 — replay.py: scenarios can give sessions a duration so motor_slowing is reachable
- status: done
- class: standard
- priority: 1
- kind: test
- deps: —
- area: pipeline/src/routine_watch/replay.py, pipeline/tests/test_replay_durations.py (new)
- owner: ian-claude-standard
- claimed: 2026-10-17T08:43Z
- pr: #154
- rating: 5/5 clear

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
- status: done
- class: light
- priority: 3
- kind: improvement
- deps: —
- area: web/src/overview/UnitOverview.tsx, web/src/overview/UnitOverview.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T09:01Z
- pr: #164
- rating: 5/5 clear

What: `UnitOverview` handles loading but renders an empty list when the API returns no residents. Show `EmptyState` with "No residents on this unit yet." (same wording as `web/src/handoff/Handoff.tsx`).
Interface: Read only the two files above and `web/src/ui/EmptyState.tsx`.
Acceptance:
- Test: mocked fetch returns `[]` → message visible, no list rendered.
- `cd web && npx vitest run src/overview` and `scripts/ci.sh` pass.

### T161 — Live screen: choose the tea or the medication session
- status: done
- class: standard
- priority: 2
- kind: feature
- deps: —
- area: web/src/live/LiveScreen.tsx (new), web/src/live/LiveScreen.test.tsx (new), web/src/App.tsx
- owner: ian-claude
- claimed: 2026-10-17T09:00Z
- pr: #166
- rating: 5/5 clear

What: SPEC §5 Nice to have 4 (a second task) exists in the pipeline (`tests/scenarios/meds_*`) but App hard-codes `tea_skip_teabag_pour_twice`, so judges never see it generalise. Add a two-option switch above the live session.
Interface: `LiveScreen({ onOpenAlert })` renders a segmented control ("Making tea" → `tea_skip_teabag_pour_twice`, "Medication with water" → `meds_skip_water`, default tea) and `<LiveSession scenario=… key=… />`. App.tsx swaps its `<LiveSession …/>` for `<LiveScreen …/>`, nothing else. Use `web/src/ui/Button.tsx`; `aria-pressed` on the active option.
Acceptance:
- Test: default renders the tea scenario; clicking "Medication with water" switches the scenario (mock `LiveSession`).
- Demo path unchanged by default. `scripts/ci.sh` passes.

### T163 — Docs: web/src/ui/README.md lists every shared component
- status: done
- class: light
- priority: 3
- kind: docs
- deps: —
- area: web/src/ui/README.md
- owner: ian-claude-light-2
- claimed: 2026-10-17T08:41Z
- pr: #150
- rating: 5/5 clear

What: The UI kit grew (DemoBanner, EmptyState, ErrorState, Loading, SectionHeader, StatusChip, errorTypes) and the README is where workers look before writing a new component. List each with one line on when to use it and its props.
Interface: Read only `web/src/ui/README.md` and the non-test `web/src/ui/*.tsx`/`*.ts` files.
Acceptance:
- Every non-test file in `web/src/ui/` appears in the README; no code changes.
- `scripts/ci.sh` passes.

### T165 — Test: pattern ids are safe feedback causes
- status: done
- class: light
- priority: 3
- kind: test
- deps: —
- area: pipeline/tests/test_feedback_cause_ids.py (new)
- owner: max_API_light
- claimed: 2026-10-17T08:45Z
- pr: #152
- rating: 5/5 clear

What: Since T129 a feedback `cause` is any pattern id or "other". Guard against a future pattern colliding with "other" or using an id the web can't round-trip.
Interface: Read only `pipeline/src/routine_watch/patterns_library.py` and `pipeline/src/routine_watch/api.py` lines 50-90. Assert ids in `BY_ID` are unique and match `^[a-z][a-z0-9_]*$`, none equals `api.OTHER_CAUSE`, and `api.KNOWN_CAUSES == set(BY_ID) | {"other"}`.
Acceptance:
- `cd pipeline && python -m pytest tests/test_feedback_cause_ids.py` and `scripts/ci.sh` pass.

### T144 — API: POST /demo/reset puts the demo back to its seeded history
- status: done
- class: standard
- priority: 2
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/api.py, pipeline/tests/test_api_demo_reset.py (new), scripts/smoke.sh
- source: proposed
- owner: ian-claude-standard-2
- claimed: 2026-10-17T09:05Z
- pr: #168
- rating: 5/5 clear

What: Demo robustness (SPEC §10, §13): after a rehearsal, Mrs. K stays flagged from the live session, so the next run of demo beat 4 never happens unless the server restarts. One endpoint resets recorded live sessions and feedback so the demo can be rerun on stage in a second.
Interface: `POST /demo/reset` → `{"ok": true}`; calls `session_log.reset()` and the equivalent reset in `routine_watch.feedback` (add a `reset()` there only if missing, in this PR). Only enabled when `OFFLINE_MODE` or a new `DEMO_RESET=1` env is set, else 404; document `DEMO_RESET` in `.env.example`.
Acceptance:
- Test: record a live session for mrs-k (flagged), POST /demo/reset, `/residents` shows her back at her seeded status; with the env unset the route is 404.
- smoke.sh hits the route once; `scripts/ci.sh` passes.

### T147 — Test: every shippable pattern has a replayable scenario
- status: done
- class: light
- priority: 3
- kind: test
- deps: T141, T142, T143
- area: pipeline/tests/test_pattern_scenarios_cover_library.py (new)
- owner: ian-claude-light-2
- claimed: 2026-10-17T09:10Z
- pr: #170
- rating: 5/5 clear

What: Guard SPEC §8 ("at least one replayable scenario per pattern") so a new pattern can't ship without one.
Interface: read `pipeline/src/routine_watch/patterns_library.py` (the list of patterns) and `tests/scenarios/*/expected.yaml`. Test collects every `top_pattern:` value from scenarios and asserts it covers every library `pattern_id` except `one_sided_change` (SPEC keeps it out of the demo).
Acceptance:
- `cd pipeline && python -m pytest tests/test_pattern_scenarios_cover_library.py` passes; `scripts/ci.sh` passes.

### T162 — Test: live websocket path finds the same errors and flag as scenario replay
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_live_matches_replay.py (new)
- owner: ian-claude-standard
- claimed: 2026-10-17T09:05Z
- pr: #171
- rating: 5/5 clear

What: The SPEC §10 fallback plays recorded scenarios through `live.session_messages`, while `scripts/e2e.sh` checks them through `replay.py`. Nothing asserts the two agree, so the demo could show different errors from what CI tested.
Interface: For each `tests/scenarios/*/` playable live, run `session_messages(scenario_path(name), speed=<very fast>)`, collect error messages and the final flag message, compare with `expected.yaml` (error type/step multiset, `flag`). Read only `pipeline/src/routine_watch/live.py` and `replay.py`. Scenarios that legitimately can't play live get an explicit skip with a reason.
Acceptance:
- Parametrised per scenario, < 20 s total, no network.
- A real mismatch → don't fix pipeline code here; xfail with a reason and list it in the PR so the orchestrator files a bug.
- `scripts/ci.sh` passes.

### T166 — Review: handoff summary uses old "the task" placeholder errors and a unit-wide baseline
- status: done
- class: standard
- priority: 1
- kind: bug
- source: reviewer
- deps: —
- area: pipeline/src/routine_watch/handoff.py, pipeline/src/routine_watch/alerts.py, pipeline/tests/test_handoff.py
- owner: ian-claude
- claimed: 2026-10-17T08:48Z
- pr: #159
- rating: 4/5 clear on the defect and the interface; it said baseline=the resident's own baseline (mean/days), but baseline['mean'] is an error score while the explainer's 'observed' is an error count - I used alerts.normal_error_rate (her own errors/session) to match what her alert already quotes

What: `handoff._explainer_errors` re-implements the placeholder-error synthesis that T121 replaced in `alerts._task_errors` (still `step_id="the task"`, t=0,10,20…), so the handoff sentence reads "… at the task, 0:00". `_summary` also compares the latest flagged session against `_unit_error_rate` (all residents mixed) instead of that resident's own baseline (SPEC §7: own history only), and doesn't say whose session it is.
Interface: In `handoff.py` drop `_UNKNOWN_STEP`/`_ERROR_SPACING_S`/`_explainer_errors`; build errors via `alerts._task_errors(session_id, session)` + `alerts._distinct_clauses` (make them public, e.g. `task_errors`/`distinct_clauses`, no other behaviour change). Baseline = that resident's own `baseline` (mean/days); prefix the context with the resident's name. Read only `handoff.py` and `alerts.py` lines 60-170.
Acceptance:
- test: handoff summary contains no "the task" and names a real step id; baseline numbers equal the flagged resident's own baseline.
- `scripts/ci.sh` passes.

### T167 — Review: nurse feedback tunes the threshold in /handoff and alert payload but not /residents status or /alerts
- status: done
- class: standard
- priority: 1
- kind: bug
- source: reviewer
- deps: —
- area: pipeline/src/routine_watch/api.py, pipeline/tests/test_api_feedback.py
- owner: ian-claude-standard
- claimed: 2026-10-17T08:51Z
- pr: #163
- rating: 4/5 clear

What: `handoff.build_handoff` and `api._alert_payload` apply `_feedback_store.threshold(...)`, but `list_residents`/`get_resident` status and `list_alerts` use the raw `baseline.threshold` from `demo_residents()`. After a nurse taps "not concerning", handoff says 0 flags while the overview still shows Flagged, which contradicts itself on stage.
Interface: one helper in `api.py` (e.g. `_tuned(resident) -> dict`) that recomputes status against the feedback-tuned threshold, reusing `demo`'s flag rule rather than duplicating it (expose a small `demo.status_for(resident, threshold)` if needed); use it in the residents and alerts routes. Read only `api.py`, `demo.py` lines 50-80, `feedback.py`.
Acceptance:
- test: post `not_concerning` feedback until the tuned threshold exceeds the latest score → `/residents` status and `/handoff` flags agree.
- `scripts/ci.sh` passes.

### T152 — Shift handoff rows open the resident's alert
- status: done
- class: standard
- priority: 3
- kind: feature
- deps: T151
- area: web/src/handoff/Handoff.tsx, web/src/handoff/Handoff.test.tsx, web/src/App.tsx, web/src/App.test.tsx
- source: proposed
- owner: ian-claude
- claimed: 2026-10-17T09:10Z
- pr: #177
- rating: 4/5 clear on the interface and the fallback; it didn't say the demo API only has an unreviewed alert after the live session has been played, so a fresh /handoff shows no button at all

What: From the handoff, the incoming nurse should reach the evidence in one tap. Rows with an unreviewed alert get an "Open alert" button that goes to the alert screen. Check `pipeline/src/routine_watch/handoff.py` for whether rows carry alert ids; if not, use the first matching alert from `fetchAlerts()` by resident id (don't change the API here; note it in the PR).
Interface: `Handoff({ onBack, onOpenAlert }: { onBack: () => void; onOpenAlert?: (alertId: string) => void })`; App passes `id => { setOpenHandoff(false); setOpenAlert(id) }`.
Acceptance:
- tests: button only on rows with unreviewed alerts; clicking calls `onOpenAlert` with the right id; App test: handoff → Open alert shows the alert view.
- `cd web && npx vitest run` passes; `scripts/ci.sh` passes.

### T168 — Review: live push alert text uses the raw resident id ("mrs-k")
- status: done
- class: light
- priority: 2
- kind: bug
- source: reviewer
- deps: —
- area: pipeline/src/routine_watch/live.py, pipeline/tests/test_live_notify.py
- owner: max_API_light
- claimed: 2026-10-17T08:40Z
- pr: #148
- rating: 5/5 clear

What: The push sent in `live.session_messages` says "A session just flagged a change for mrs-k to review." A nurse sees the slug, not the name. Have `_resident_flagged` look the resident up once (one `demo_residents()` call) and use `resident["name"]` in the summary.
Interface: Read only `live.py` lines 250-290 and `tests/test_live_notify.py`. Keep `alert_id` = `f"alert-{resident_id}"` (matches `alerts.py`).
Acceptance:
- test asserts the summary contains the resident's display name and not the id.
- `scripts/ci.sh` passes.

### T169 — Test: scenarios README lists every scenario folder
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_scenarios_readme.py (new), tests/scenarios/README.md
- owner: ian-claude-light-2
- claimed: 2026-10-17T08:50Z
- pr: #156
- rating: 5/5 clear

What: The "The scenarios here" table in `tests/scenarios/README.md` is hand-maintained and will drift as scenarios are added. Add a test that every directory under `tests/scenarios/` appears in that table as `` `name` `` and every name in the table is a real directory.
Interface: Read only `tests/scenarios/README.md` (section "## The scenarios here") and `ls tests/scenarios/`. New `pipeline/tests/test_scenarios_readme.py` locates the repo root from `__file__` (`Path(__file__).resolve().parents[2]`). If a folder is missing from the table, add a one-line row for it (read its `expected.yaml` to describe it).
Acceptance:
- test fails with the missing/extra names listed when the table and folders disagree.
- `scripts/ci.sh` passes.

### T170 — Test: dashboard error wording matches explain.py
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_error_phrases_match_web.py (new)
- owner: ian-claude-light-2
- claimed: 2026-10-17T08:54Z
- pr: #157
- rating: 5/5 clear

What: `web/src/ui/errorTypes.ts` `PHRASES` copies `pipeline/src/routine_watch/explain.py` `_PHRASES` by hand ("same wording as..."). Add a pipeline test that reads the TS file as text and checks each error type's phrase matches the Python template (Python `{step}` ↔ TS `${step}`).
Interface: Read only `pipeline/src/routine_watch/explain.py` lines 1-30 and `web/src/ui/errorTypes.ts`. Parse lines like `omission: (step) => \`skipped ${step}\`,` with a regex; import `_PHRASES` from `routine_watch.explain`. Do not change either source file.
Acceptance:
- test passes on current main and fails if one phrase is edited on either side (check manually, don't commit that).
- same set of error types on both sides.
- `scripts/ci.sh` passes.

### T171 — Sparkline: nurse-readable screen-reader label
- status: done
- class: light
- priority: 3
- kind: improvement
- deps: —
- area: web/src/overview/Sparkline.tsx, web/src/overview/Sparkline.test.tsx
- owner: max_API_light
- claimed: 2026-10-17T09:03Z
- pr: #165
- rating: 5/5 clear

What: The overview sparkline's label reads "error score trend, latest 2.4000001" (raw float, lowercase). Make it "Error score over the last N sessions, latest 2.4" using `formatScore` from `web/src/resident/format.ts`.
Interface: Read only `web/src/overview/Sparkline.tsx`, its test, and `formatScore` in `web/src/resident/format.ts` (import it; don't modify format.ts). Empty sparkline stays `aria-hidden`.
Acceptance:
- test asserts the label for a 3-point series with a long float latest value.
- `cd web && npm test -- Sparkline` and `scripts/ci.sh` pass.

### T172 — Heat calendar: colour legend and formatted scores
- status: done
- class: light
- priority: 3
- kind: improvement
- deps: —
- area: web/src/resident/HeatCalendar.tsx, web/src/resident/HeatCalendar.test.tsx
- owner: max_API_light
- claimed: 2026-10-17T09:18Z
- pr: #176
- rating: 5/5 clear

What: The heat calendar has no legend, so a nurse can't tell what darker red means, and cell labels show raw scores ("score 3.4000001"). Add a one-line legend under the grid ("Lighter = fewer errors · Darker = more errors · Grey = no session", with small swatches using the same CSS vars) and format cell labels with `formatScore`.
Interface: Read only `web/src/resident/HeatCalendar.tsx`, its test, and `formatScore` in `web/src/resident/format.ts` (import; don't modify). Swatches `aria-hidden`; legend text visible.
Acceptance:
- tests: legend text rendered; a cell label uses the formatted score.
- `cd web && npm test -- HeatCalendar` and `scripts/ci.sh` pass.

### T173 — Docs: CODEMAP note for the overview's top pattern
- status: done
- class: light
- priority: 3
- kind: docs
- deps: —
- area: docs/CODEMAP.md
- owner: ian-claude-light-2
- claimed: 2026-10-17T09:18Z
- pr: #175
- rating: 5/5 clear

What: T089 (PR #149) added `top_pattern` to `GET /residents` (computed in `demo.py` `_top_pattern`, only for watch/flagged residents) and shows it on the unit overview, but `docs/CODEMAP.md` notes don't mention it. Add a 1-3 line note. Also add one line that `web/src/live/LiveScreen.tsx` (T161, PR #166) wraps `LiveSession` with a tea/medication routine picker.
Interface: Read only `docs/CODEMAP.md`, `git show 597b34d --stat`, `web/src/live/LiveScreen.tsx`, and `_top_pattern` in `pipeline/src/routine_watch/demo.py`. Edit notes only, not the generated file list. Use "consistent with" wording.
Acceptance:
- note names `demo._top_pattern`, the `top_pattern` field and `web/src/overview/UnitOverview.tsx`.
- `scripts/ci.sh` passes.

### T174 — Test: demo top_pattern is set only for watch/flagged residents
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_demo_top_pattern.py (new)
- owner: max_API_light
- claimed: 2026-10-17T08:54Z
- pr: #158
- rating: 5/5 clear

What: Pin the new `top_pattern` behaviour of `demo_residents()`: `None` for every `normal` resident; for each non-normal resident either `None` or a dict with exactly `pattern_id`, `name`, `urgency`, where `pattern_id` exists in the pattern library and `urgency` is a valid urgency value; and Mrs. K (`mrs-k`) has a non-None top pattern.
Interface: Read only `pipeline/src/routine_watch/demo.py` (`_top_pattern`, `demo_residents`) and the pattern ids in `pipeline/src/routine_watch/patterns_library.py`. Don't change source files; if Mrs. K's top pattern is `None`, assert what it is and note it in the PR instead of changing code.
Acceptance:
- `cd pipeline && pytest tests/test_demo_top_pattern.py` and `scripts/ci.sh` pass.

### T175 — Test: LiveSession calls onSessionEnd once per session_end
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/live/LiveSession.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T08:58Z
- pr: #160
- rating: 5/5 clear

What: T156 (PR #155) added an `onSessionEnd` prop to `LiveSession` but `LiveSession.test.tsx` never exercises it; lock the "once per session_end" contract in.
Interface: read `web/src/live/LiveSession.tsx` (prop `onSessionEnd?: (ended: LiveSessionEnded) => void`, effect near line 90) and the existing `web/src/live/LiveSession.test.tsx` for how it drives the mock stream. Edit only the test file.
Acceptance:
- a test where a flagged session ends asserts `onSessionEnd` called exactly once with the ended payload; re-render does not call it again
- a test where a clear (unflagged) session ends also calls it once
- omitting the prop doesn't throw
- `cd web && npx vitest run src/live/LiveSession.test.tsx` and `scripts/ci.sh` pass

### T176 — Docs: scenarios README explains session duration_s
- status: done
- class: light
- priority: 2
- kind: docs
- deps: —
- area: tests/scenarios/README.md
- owner: max_API_light
- claimed: 2026-10-17T08:59Z
- pr: #161
- rating: 5/5 clear

What: T157 (PR #154) let scenarios give history sessions and the expected session a `duration_s`, which is how `motor_slowing` becomes reachable; `tests/scenarios/README.md` doesn't mention it, so scenario authors won't find it.
Interface: read `pipeline/src/routine_watch/replay.py` (`HistorySession.duration_s`, `Expected.duration_s`, docstrings near lines 98 and 142) and `pipeline/tests/test_replay_durations.py` for a worked example. Edit only the README: add a short "Session durations" section with a minimal YAML snippet showing both fields and one sentence on when to use them (duration-based patterns like motor slowing). Don't change the "scenarios here" table rows (a test parses it).
Acceptance:
- README has the section with a YAML example using the real field names
- `scripts/ci.sh` passes (incl. `pipeline/tests/test_scenarios_readme.py`)

### T164 — Guided demo tour behind ?tour=1
- status: done
- class: standard
- priority: 3
- kind: feature
- source: proposed
- deps: —
- area: web/src/tour/ (new), web/src/App.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T09:28Z
- pr: #186
- rating: 5/5 clear

What: Rationale: judges skim; a 7-step tour following SPEC §10 (baseline → live → alert → why → not just delirium → privacy) makes Clarity obvious and doubles as a presenter cue card. Off unless the URL has `?tour=1`, so it can't touch the demo path.
Interface: `web/src/tour/Tour.tsx` renders a small fixed card (title, body, Back/Next/Close, "n of 7") from a `web/src/tour/steps.ts` array of `{ title, body }`; plain-language copy using "flags a change for review" / "consistent with", never "diagnose". App.tsx mounts `<Tour />` only when `new URLSearchParams(location.search).has('tour')`. No navigation automation.
Acceptance:
- Tests: hidden without the param; with it, Next/Back move through steps and Close hides it; copy contains no "diagnos".
- `scripts/ci.sh` passes.

### T177 — Test: handoff summary and Mrs. K's alert name the same errors
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_handoff_alert_errors.py
- owner: ian-claude-light-2
- claimed: 2026-10-17T09:06Z
- pr: #167
- rating: 5/5 clear

What: T166 (PR #159) made the handoff build its errors with `alerts.task_errors` and `alerts.session_id_for` so a nurse reads the same steps and times in both places. Lock that in with a test.
Interface: Read only `pipeline/src/routine_watch/handoff.py` (`build_handoff`, `_window_sessions`, `_latest`), `pipeline/src/routine_watch/alerts.py` (`build_alerts`, `task_errors`, `session_id_for`) and `pipeline/tests/test_handoff.py` for fixtures. New test file only; don't change source.
Acceptance:
* For the demo data, the latest flagged session in the handoff window has error ids that all appear in that resident's alert `errors` (or, if the resident has no alert, the test asserts that explicitly and says why in a comment).
* `session_id_for("mrs-k", 3) == "mrs-k-3"` is asserted.
* `cd pipeline && python -m pytest tests/test_handoff_alert_errors.py -q` passes; `scripts/ci.sh` passes.

### T178 — smoke.sh: check GET /handoff
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: scripts/smoke.sh
- owner: ian-claude-standard-2
- claimed: 2026-10-17T09:15Z
- pr: #174
- rating: 5/5 clear

What: `scripts/smoke.sh` hits the API routes of a running stack but skips `GET /handoff` (shift handoff screen), so a broken handoff route wouldn't show up in smoke runs.
Interface: Read only `scripts/smoke.sh` and the `/handoff` route in `pipeline/src/routine_watch/api.py` (returns `{window_hours, residents: [...], summary: str}`, `hours` query 1-168, default 12). Add checks in the existing PASS/FAIL style.
Acceptance:
* New check: `GET /handoff` returns 200 with `window_hours == 12`, a non-empty `residents` list and a non-empty `summary` string.
* New check: `GET /handoff?hours=0` returns 422.
* `bash -n scripts/smoke.sh` passes; `scripts/ci.sh` passes. Say in the PR whether you ran it against `scripts/dev.sh up`.

### T181 — Alert screen: empty state when nothing is flagged
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/alert/AlertView.tsx, web/src/alert/AlertView.test.tsx
- owner: max_API_light
- claimed: 2026-10-17T09:08Z
- pr: #169
- rating: 5/5 clear

What: Check how the alert screen behaves when the alert fetch returns nothing (e.g. before the live session flags Mrs. K). It should show the shared `EmptyState` with nurse-readable copy ("No change flagged for review."), not a blank area or an endless spinner.
Interface: Read only `web/src/alert/AlertView.tsx`, `web/src/alert/api.ts`, `web/src/ui/EmptyState.tsx` and `web/src/alert/AlertView.test.tsx`. If the list is rendered elsewhere, edit only that file and note it in the PR.
Acceptance:
* Empty result renders `EmptyState` with the copy above; loading is still shown while fetching.
* Test covers the empty result; `cd web && npx vitest run src/alert/AlertView.test.tsx` and `scripts/ci.sh` pass.

### T180 — Handoff: each row says what's normal for that resident
- status: done
- class: standard
- priority: 3
- kind: feature
- deps: —
- area: web/src/handoff/
- owner: ian-claude-standard
- claimed: 2026-10-17T09:35Z
- source: proposed
- pr: #188
- rating: 5/5 clear

What: Rationale: a night nurse reading the handoff can't tell whether "2 flags" is unusual for that resident. Each row gets a short muted line like "Usually 0.4 errors a session" so the change reads against her own normal (SPEC §7, Clarity).
Interface: Read `web/src/handoff/Handoff.tsx`, `types.ts`, `api.ts`, `mockHandoff.ts` and the row fields in `pipeline/src/routine_watch/handoff.py`. If rows don't carry a baseline, take it from the resident detail fetch in `web/src/resident/api.ts` (one fetch per row is fine for the demo) and say so in the PR; don't change the API or `contracts/`.
Acceptance:
* Rows with history show the baseline line; residents with no history show nothing (no "NaN", no "0").
* Wording never says "diagnos"/"has <condition>"; plain numbers a nurse reads in 10 s.
* New/updated test in `web/src/handoff/Handoff.test.tsx`; `scripts/ci.sh` passes.

### T182 — Review: false alarm makes the alert 404, so the cause answer can't be saved
- status: done
- class: standard
- priority: 0
- kind: bug
- source: reviewer
- deps: —
- area: pipeline/src/routine_watch/api.py, pipeline/tests/test_api_feedback.py
- owner: ian-claude-standard
- claimed: 2026-10-17T09:15Z
- pr: #178
- rating: 5/5 clear

What: Since T167, `_alerts_by_id()` builds alerts only from `_flagged_residents()` (feedback-tuned). A "false alarm" raises the resident's threshold 10%; if that un-flags her, the alert disappears, so `GET /alerts/{id}` and the next `POST /alerts/{id}/feedback` return 404. AlertView posts the verdict, then posts again with the "what was it?" cause, so the nurse sees "Feedback could not be saved" and can never correct a mistaken tap. Fix: look alerts up by id from every raw-flagged resident (`build_alerts([r for r in demo_residents() if r["status"] == "flagged"], feedback=_feedback_store)`); keep the tuned filter only for the `/alerts` list.
Acceptance:
* Test: flagged resident, POST false_alarm with a threshold step big enough to un-flag; `/alerts` no longer lists it, but `GET /alerts/{id}` is 200 and a second POST with `cause` is 200 and stores the cause.
* `scripts/ci.sh` passes.

### T155 — Bug: alert opened after the live session shows other errors than the live session made
- status: done
- class: heavy
- priority: 0
- kind: bug
- deps: —
- area: pipeline/src/routine_watch/demo.py, pipeline/src/routine_watch/alerts.py, pipeline/src/routine_watch/session_log.py, pipeline/tests/
- source: tester
- owner: ian-claude
- claimed: 2026-10-17T09:36Z
- pr: #192
- rating: 4/5 clear repro and interface; the step id is teabag_in_cup not add_teabag, and the fix needs evidence.known_session (outside the listed area) or 'Open evidence' 404s on the live session's errors

What: On stage the live session (default demo scenario) flags "skipped Put the teabag in the cup · 1:10" and "repeated Pour the water · 1:30". Clicking "Open alert" then shows `alert-mrs-k` with errors "skipped fill kettle 0:51, repeated boil 1:42, skipped fill kettle 0:33, repeated boil 1:06" (sessions mrs-k-22, mrs-k-23): the recorded live session's score is merged into Mrs. K's history, but its actual errors are not; the alert's errors for that session are synthetic. The summary also says "4 errors this session" for errors spread over two sessions.
Interface: the session recorded by `routine_watch.live` (via `session_log`) must carry its real `ErrorEvent`s into the resident's newest session, so `build_alerts` lists them (with their real step ids and times) for that session; the summary should count errors per session or say "across 2 sessions".
Repro: `OFFLINE_MODE=true scripts/dev.sh up`, open http://localhost:5173, wait ~90 s for the live session to finish, click "Open alert"; compare the alert's Errors list with the live session's Errors list. Or `curl localhost:8000/alerts/alert-mrs-k` after the live session.
Acceptance:
- test: after playing the demo live scenario through the pipeline, `/alerts/alert-mrs-k` contains its omission of `add_teabag` and perseveration of `pour` with the live session's session_id.
- summary wording no longer says "this session" for multi-session errors; `scripts/ci.sh` and `scripts/e2e.sh` pass.

### T183 — Review: overview/handoff top pattern ignores nurse-feedback weights
- status: done
- class: light
- priority: 1
- kind: bug
- source: reviewer
- deps: T182
- area: pipeline/src/routine_watch/api.py, pipeline/src/routine_watch/handoff.py, pipeline/tests/test_api_residents.py
- owner: ian-claude
- claimed: 2026-10-17T09:23Z
- pr: #185
- rating: 5/5 clear - the fix, the helper and the acceptance test were all named exactly; only unstated bit was that alerts.py is outside the listed area

What: `/residents` shows `top_pattern` from `demo.py` (`score_patterns` with no weights), while the alert's `patterns[0]` is re-weighted by `FeedbackStore.pattern_weights` (T130). After a nurse answers "what was it?", the overview chip and the alert can name different patterns for the same resident. `handoff.build_handoff` also calls `build_alerts(residents)` without `feedback=`. Fix: in `api._tuned`, when the resident has pattern weights, recompute `top_pattern` with `score_patterns(features, weights=..., answers=...)` (reuse `alerts._patterns` or expose a small helper) and pass the store into `build_alerts` in handoff.
Acceptance:
* Test: confirm an alert with a cause that reorders the ranking; `/residents` top_pattern id equals `/alerts/{id}` `patterns[0].pattern_id`.
* `scripts/ci.sh` passes.

### T184 — Test: status_for with the raw threshold gives each resident's own status
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_status_for.py (new)
- owner: max_API_light
- claimed: 2026-10-17T09:13Z
- pr: #172
- rating: 5/5 clear

What: T167 (PR #163) added `demo.status_for(resident, threshold)`, which repeats the flag rule from `demo_residents()`. Pin that the two agree, so `/residents` can't drift from the demo's own status when no feedback has been given.
Interface: Read only `pipeline/src/routine_watch/demo.py` (`status_for`, `demo_residents`), `pipeline/tests/conftest.py` (autouse `session_log.reset`) and `pipeline/tests/test_live_flag.py` (how a live session is recorded). New file only.
Acceptance:
* For every resident in `demo_residents()`, `status_for(r, r["baseline"]["threshold"]) == r["status"]`.
* Same check after recording Mrs. K's live tea session the way `test_live_flag.py` does (she becomes flagged).
* `status_for(r, 1e9)` is never "flagged".
* `scripts/ci.sh` passes.

### T185 — demo.py: one flag rule shared by demo_residents and status_for
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: T184
- area: pipeline/src/routine_watch/demo.py, pipeline/tests/test_demo.py
- owner: ian-claude-standard-2
- claimed: 2026-10-17T09:21Z
- pr: #180
- rating: 5/5 clear

What: `demo_residents()` and `status_for()` each build `timestamped`, call `flag_change` and `_watch`, then `_status` (the second copy calls `_watch(sessions, sessions, ...)` instead of `(history, sessions, ...)`, which only works because live sessions fall after the baseline cutoff). Pull this into one private helper both call, with no behaviour change.
Interface: one private helper (e.g. `_status_from(history, sessions, scores, baseline: Baseline) -> str`); `status_for` signature unchanged; `api.py` untouched.
Acceptance:
* `flag_change(` and `_watch(` are each called once in `demo.py`.
* T184's test and `pipeline/tests/test_demo*.py` pass unchanged.
* `scripts/ci.sh` passes.

### T186 — Live screen: ?task=meds opens on the medication routine
- status: done
- class: light
- priority: 2
- kind: feature
- deps: —
- area: web/src/live/LiveScreen.tsx, web/src/live/LiveScreen.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T09:15Z
- pr: #173
- rating: 5/5 clear

What: The presenter wants to link straight to the second routine. `LiveScreen` (T161) always starts on tea; let `?task=meds` pick "Medication with water" first; `?task=tea`, anything else or no param keeps tea. Clicking a button still switches as now.
Interface: Read only `web/src/live/LiveScreen.tsx` and its test. Read `window.location.search` once in the `useState` initializer (`URLSearchParams`); no router, don't write to the URL.
Acceptance:
* Tests: no param → "Making tea" `aria-pressed=true`; `?task=meds` → "Medication with water" pressed and `LiveSession` gets `meds_skip_water`; `?task=bogus` → tea.
* `scripts/ci.sh` passes.

### T188 — Docs: DEMO.md covers /demo/reset and ?task=meds
- status: done
- class: light
- priority: 2
- kind: docs
- deps: —
- area: docs/DEMO.md
- owner: ian-claude-light-2
- claimed: 2026-10-17T09:22Z
- pr: #179
- rating: 5/5 clear

What: The demo runbook doesn't say how to put the demo back between rehearsals or how to open the medication routine directly. Add both.
Interface: read `docs/DEMO.md`, `pipeline/src/routine_watch/api.py` (`demo_reset`, `_demo_reset_enabled`), `web/src/live/LiveScreen.tsx` (the `?task=meds` query), `.env.example` (`DEMO_RESET`).
Acceptance:
- DEMO.md has a "Between rehearsals" step: `curl -X POST http://localhost:8000/demo/reset`, only works with `OFFLINE_MODE=true` or `DEMO_RESET=1`, returns `{"ok": true}`.
- DEMO.md mentions opening the live screen with `?task=meds` for the medication routine (tea stays the default).
- Only docs/DEMO.md changes; `scripts/ci.sh` passes.

### T189 — Demo banner: "Reset demo" button
- status: done
- class: standard
- priority: 2
- kind: feature
- deps: —
- area: web/src/ui/DemoBanner.tsx, web/src/ui/DemoBanner.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T09:23Z
- pr: #182
- rating: 5/5 clear

What: Presenters need a one-click way to undo a rehearsal's flag and feedback. Add a "Reset demo" button to the demo banner that POSTs `/demo/reset` and then reloads the page.
Interface: `DemoBanner({ onDismiss?, onReset? })`; default `onReset` does `fetch(\`${apiBase}/demo/reset\`, {method:'POST'})` using the API base from `web/src/config.ts`, then `window.location.reload()`. On a non-2xx/network error show inline "Couldn't reset the demo" text, no throw.
Acceptance:
- Button is a secondary `btn`, labelled "Reset demo"; disabled while the request is in flight.
- Tests (mock fetch): success calls reload; 404 shows the error text and doesn't reload.
- `cd web && npm test -- DemoBanner` and `scripts/ci.sh` pass.

### T190 — Test: LiveScreen ignores unknown ?task values
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/live/LiveScreen.test.tsx
- owner: max_API_light
- claimed: 2026-10-17T09:23Z
- pr: #181
- rating: 5/5 clear

What: T186 added `?task=meds`; pin that anything else (absent, `?task=tea`, `?task=foo`) still opens the tea routine.
Interface: read `web/src/live/LiveScreen.tsx` and its existing test; set `window.history.replaceState(null, '', '/?task=foo')` per case and restore afterwards.
Acceptance:
- Three cases (no query, `tea`, `foo`) all show tea selected in the picker.
- Only the test file changes; `cd web && npm test -- LiveScreen` and `scripts/ci.sh` pass.

### T191 — Test: FeedbackStore.reset() puts threshold and weights back to base
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_feedback.py
- owner: ian-claude-light-2
- claimed: 2026-10-17T09:26Z
- pr: #183
- rating: 5/5 clear

What: `FeedbackStore.reset()` (added by T144) has no unit test.
Interface: read `pipeline/src/routine_watch/feedback.py` and `pipeline/tests/test_feedback.py`.
Acceptance:
- Test: log a false alarm and a cause, call `reset()`, assert threshold equals the no-feedback base, the feedback for that alert id is None, and `cause_of` is None.
- `cd pipeline && pytest tests/test_feedback.py` and `scripts/ci.sh` pass.

### T193 — Scenario: medication taken twice is a repetition error
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/meds_pill_twice/ (new), tests/scenarios/README.md
- owner: ian-claude-standard-2
- claimed: 2026-10-17T09:27Z
- pr: #184
- rating: 5/5 clear

What: The medication routine has skip and order scenarios but none for a repeated step, the most safety-relevant meds error. Add one.
Interface: copy the shape of `tests/scenarios/meds_normal/` and `tests/scenarios/tea_kettle_twice/`; `frames.jsonl` + `expected.yaml` with one repetition error on the take-pill step.
Acceptance:
- `scripts/e2e.sh` passes including the new scenario; README lists it (the README coverage test passes).
- If the meds graph can't express it, stop and set the task blocked with the reason (don't change pipeline code).

### T195 — Unit overview: All / Flagged / Watch filter
- status: done
- class: standard
- priority: 3
- kind: feature
- source: proposed
- deps: —
- area: web/src/overview/UnitOverview.tsx, web/src/overview/UnitOverview.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T09:35Z
- pr: #187
- rating: 5/5 clear

What: Rationale: on a real unit a nurse wants only the residents needing attention in one tap (Clarity). Add a three-way filter above the resident list; All stays default so the demo path is unchanged.
Interface: local state in `UnitOverview`; buttons with `aria-pressed`; filters on the existing resident `status`; empty filter result uses `EmptyState` "No residents flagged for review." / "No residents to watch.".
Acceptance:
- Tests: each filter shows only matching residents; empty case shows the message; default is All.
- `cd web && npm test -- UnitOverview` and `scripts/ci.sh` pass.

### T196 — App: Alerts list names residents; alert Back returns to where it was opened
- status: done
- class: standard
- priority: 1
- kind: bug
- deps: —
- area: web/src/App.tsx, web/src/App.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T09:43Z
- pr: #190
- rating: 5/5 clear

What: The overview's Alerts list shows the raw id ("mrs-k: Change flagged for review"), not a name a nurse reads; and an alert opened from the shift handoff (T152, PR #177) goes Back to the overview instead of the handoff.
Interface: In `App.tsx`, label each alert with the resident's display name from `fetchResidents()` (`web/src/overview/api.ts`; fall back to the id if not found). Track where the alert was opened from (`'overview' | 'handoff' | 'live'`) so `AlertView`'s `onBack` returns there.
Acceptance:
* App test: Alerts list shows "Mrs. K" (mock residents), not "mrs-k".
* App test: Shift handoff → Open alert → Back lands on the handoff screen; overview → alert → Back lands on the overview.
* `cd web && npx vitest run src/App.test.tsx` and `scripts/ci.sh` pass.

### T197 — Heat calendar legend: CSS classes instead of inline styles
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/HeatCalendar.tsx, web/src/resident/heatCalendar.css, web/src/resident/HeatCalendar.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T09:51Z
- pr: #193
- note: released by ian-claude-light-2: run ended without progress; partial work on branch task/T197-wip-0932: start from it (git switch task/T197-wip-0932 && git merge origin/main)
- rating: 5/5 clear

What: T172 (PR #176) added three legend swatches with long inline `style={{...}}` objects. Move them to classes so the colours live in one place with the grid cells.
Interface: Read only `web/src/resident/HeatCalendar.tsx` and `web/src/alert/alert.css` (example of a component stylesheet). Create `heatCalendar.css` with `.heat-swatch`, `.heat-swatch--low`, `.heat-swatch--high`, `.heat-swatch--none` using the same CSS variables; import it in `HeatCalendar.tsx`. No visible change.
Acceptance:
* No `style={{` left on the legend swatches; legend text unchanged ("Lighter = fewer errors", "Darker = more errors", "Grey = no session").
* `cd web && npx vitest run src/resident/HeatCalendar.test.tsx` passes.

### T199 — Alert view: "Copy summary" for the chart note
- status: done
- class: standard
- priority: 3
- kind: feature
- source: proposed
- deps: —
- area: web/src/alert/AlertView.tsx, web/src/alert/alertText.ts, web/src/alert/alertText.test.ts, web/src/alert/AlertView.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T09:44Z
- pr: #189
- rating: 5/5 clear

What: Rationale: nurses chart what they saw; one tap copies the alert as plain text (like the handoff's Copy summary, T151) so the flag reaches the care record without retyping (Usefulness).
Interface: `alertText(alert: Alert): string` in `alertText.ts`: resident, "Change flagged for review", the summary, errors with times, "Consistent with: …" pattern names, suggested checks. A `Copy summary` button in `AlertView` using `navigator.clipboard.writeText`, with a "Copied" status like `web/src/handoff/Handoff.tsx`.
Acceptance:
* Unit test on `alertText` for the mock alert: contains "flagged for review" and "Consistent with", never "diagnos".
* AlertView test: clicking Copy summary calls clipboard with `alertText(alert)` and shows "Copied".
* `scripts/ci.sh` passes.

### T200 — Demo banner: CSS classes and an announced reset error
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/ui/DemoBanner.tsx, web/src/ui/DemoBanner.test.tsx, web/src/ui/demoBanner.css
- owner: ian-claude-standard-2
- claimed: 2026-10-17T09:51Z
- pr: #195
- rating: 5/5 clear

What: DemoBanner (PR #182) uses inline styles and its "Couldn't reset the demo" text is not announced to screen readers. Move styles to `demoBanner.css` and give the error `role="alert"`.
Interface: read only web/src/ui/DemoBanner.tsx, web/src/ui/DemoBanner.test.tsx and web/src/styles/ (design tokens). No behaviour change.
Acceptance:
- no `style={{` left in DemoBanner.tsx; classes use existing `var(--...)` tokens
- test: a failing onReset renders an element with role="alert" containing "Couldn't reset the demo"
- `cd web && npm test -- DemoBanner` passes; `scripts/ci.sh` passes

### T201 — Scenario: medication routine abandoned halfway
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/meds_abandoned/
- owner: ian-claude-light-2
- claimed: 2026-10-17T09:53Z
- pr: #194
- rating: 5/5 clear

What: add a meds scenario where the resident stops after the first steps, mirroring tea_abandoned, so the second task's abandonment path is covered end to end.
Interface: read tests/scenarios/README.md, tests/scenarios/tea_abandoned/, tests/scenarios/meds_normal/ and tasks/meds.yaml (or the meds task graph named in meds_normal/expected.yaml). Write steps.jsonl + expected.yaml only.
Acceptance:
- expected.yaml has `task:` set to the meds graph and the errors/flag the replay actually produces (run the replay and pin its output; comment on why)
- `scripts/e2e.sh tests/scenarios/meds_abandoned` prints PASS; `scripts/ci.sh` passes

### T202 — Scenario: medication slip corrected inside the window is not flagged
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/meds_self_corrected/
- owner: ian-claude-standard
- claimed: 2026-10-17T09:55Z
- pr: #197
- rating: 5/5 clear

What: meds counterpart of tea_self_corrected: a sequence slip the resident corrects within the self-correction window, so the reduced weight is pinned for the second task too.
Interface: read tests/scenarios/README.md, tests/scenarios/tea_self_corrected/ and tests/scenarios/meds_pill_before_water/. Write steps.jsonl + expected.yaml only.
Acceptance:
- expected.yaml pins `score:` and `flag: false`, with a comment saying what full weighting would score
- `scripts/e2e.sh tests/scenarios/meds_self_corrected` prints PASS; `scripts/ci.sh` passes

### T204 — Review: demo tour misstates the flag rule ("two sessions in a row")
- status: done
- class: light
- priority: 2
- kind: bug
- source: reviewer
- deps: —
- area: web/src/tour/steps.ts, web/src/tour/Tour.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T09:57Z
- pr: #196
- rating: 5/5 clear

What: the "Alert" step (T164, #186) says an alert appears "when two sessions in a row cross a resident's own threshold". The real rule (`pipeline/src/routine_watch/change_detection.py` `flag_change`) is at least `FLAG_MIN_SESSIONS` (2) sessions above threshold within a 48-hour window, consecutive or not. A presenter reading this card would misdescribe the product to judges. Reword to "when at least two sessions within 48 hours cross a resident's own threshold".
Interface: read only the area files.
Acceptance:
- Alert step copy names "within 48 hours", no "in a row"
- Tour test asserts the Alert step body contains "48 hours"
- `cd web && npm test -- Tour` and `scripts/ci.sh` pass

### T205 — Tour: Escape closes it, arrow keys step through
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/tour/Tour.tsx, web/src/tour/Tour.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T10:04Z
- pr: #200
- rating: 5/5 clear

What: The presenter drives the `?tour=1` cue card from a keyboard on stage; today only mouse clicks work. Add Escape = Close, ArrowRight = Next, ArrowLeft = Back (respecting first/last bounds).
Interface: `Tour` in web/src/tour/Tour.tsx adds one `keydown` listener on `window` in a `useEffect` (removed on unmount/close). No other files; do not edit steps.ts (T204 owns it).
Acceptance:
- Escape hides the card and calls `onClose`; ArrowRight/ArrowLeft move one step and never go past step 1 or the last step.
- New tests in Tour.test.tsx using `fireEvent.keyDown(window, { key: ... })`.
- `cd web && npm test -- --run src/tour` and `scripts/ci.sh` pass.

### T207 — Bug: skeleton view and evidence ghost replay show no skeleton, only object boxes
- status: done
- class: standard
- priority: 1
- kind: bug
- deps: —
- area: pipeline/src/routine_watch/live.py, pipeline/src/routine_watch/evidence.py, pipeline/tests/
- owner: ian-claude
- claimed: 2026-10-17T09:54Z
- pr: #205
- rating: 5/5 clear - repro, expected/actual and the acceptance checks all matched what I found; the only thing not spelled out was that the replay stand-ins are the tests/scenarios frames.jsonl files, which are outside the listed area, so the fix had to go in evidence.py rather than the recordings

What: Tester (main 355d6b1). Every stand-in frame the demo serves is built with `poses=[]` and `hands=[]` (`live._synthetic_frames`, and the recordings behind `/sessions/{id}/replay` and `/residents/{id}/normal_replay`), so the live "Skeleton view" and the alert's "Today / Usual" ghost replay draw only labelled object boxes, never a body skeleton or hands (SPEC §5 ghost replay, §10 step 3 "skeleton view").
Repro: `OFFLINE_MODE=true scripts/dev.sh up`; open the dashboard, wait for the live session to flag, click "Open alert", press Play under Evidence. `curl "localhost:8000/sessions/mrs-k-22/replay?t_start=40&t_end=60"` → every frame has `"poses": [], "hands": []`.
Expected: a simple stick-figure pose (and a hand near the active object) in each synthetic frame, moving between the objects of each step; Usual replay differs visibly from Today. Actual: boxes only.
Interface: `_synthetic_frames` (and whatever builds the replay stand-in frames) fill `poses`/`hands` with keypoints per the `contracts/` CaptureFrame schema (no contract change); see `contracts/examples/capture.jsonl` for the shape.
Acceptance:
- Pipeline test: synthetic live frames and `/sessions/{id}/replay` frames have ≥1 pose with keypoints in [0,1].
- No change to step/error/flag results: `scripts/e2e.sh` still 23/23.
- `scripts/ci.sh` passes.

### T118 — Pattern library page: what each pattern looks for and its source
- status: done
- class: standard
- priority: 3
- kind: feature
- deps: T084
- area: pipeline/src/routine_watch/api.py (add the route only), pipeline/tests/test_api_patterns.py (new), web/src/patterns/ (new), web/src/App.tsx (one nav entry)
- owner: ian-claude-standard
- claimed: 2026-10-17T10:23Z
- pr: #212
- source: proposed
- rating: 5/5 clear

What: Rationale: judges (Clarity, responsible design §12) can see every pattern's signals, rule-out checks and source citation, showing it is a cited rules library, not an LLM guess. Read-only screen, separate from the demo path.
Interface: `GET /patterns` → the library as JSON (id, name, signals, time profile, checks, urgency, source); `web/src/patterns/PatternLibrary.tsx` lists them with "consistent with" wording.
Acceptance:
- pytest: route returns every library entry with a non-empty source; vitest: renders each pattern, urgent one visually distinct, no "diagnos" text.
- `scripts/ci.sh` passes.

### T206 — Test: alerts.top_pattern_for edge cases
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_top_pattern_for.py
- owner: ian-claude-light-2
- claimed: 2026-10-17T10:23Z
- pr: #209
- rating: 5/5 clear

What: `top_pattern_for` (pipeline/src/routine_watch/alerts.py, added in T183) has only API-level coverage. Add unit tests for it directly.
Interface: read pipeline/src/routine_watch/alerts.py (`top_pattern_for`, `_patterns`), pipeline/src/routine_watch/demo.py (`demo_residents`), and pipeline/tests/test_api_residents.py for fixture style. New file only.
Acceptance:
- With `feedback=None`, for every resident from `demo_residents()` whose `top_pattern` is set, `top_pattern_for(resident)["pattern_id"] == resident["top_pattern"]["pattern_id"]`.
- Returned dict has exactly the keys `pattern_id`, `name`, `urgency`, and `urgency` is a plain string.
- A resident whose patterns all fall below threshold (build one by copying a demo resident and clearing its errors/sessions as needed) returns `None`.
- `cd pipeline && python -m pytest tests/test_top_pattern_for.py -q` and `scripts/ci.sh` pass.

### T208 — Bug: ghost replay "Today" caption is dark blue on the dark card, unreadable
- status: done
- class: light
- priority: 1
- kind: bug
- deps: —
- area: web/src/evidence/GhostReplay.tsx, web/src/evidence/
- owner: ian-claude-light-2
- claimed: 2026-10-17T09:47Z
- pr: #191
- rating: 5/5 clear

What: Tester (main 355d6b1). `web/src/evidence/GhostReplay.tsx:44` colours the caption with inline `color: 'blue'` / `'grey'`; on the dark evidence card "Today" is near-invisible. Use the colours the replay strokes use (CSS classes, no inline styles) so both labels are readable and match the lines they name.
Repro: `OFFLINE_MODE=true scripts/dev.sh up`, open alert-mrs-k, scroll to Evidence: caption under the replay.
Acceptance:
- No inline colour in the figcaption; "Today" and "Usual" each match their replay stroke colour and pass WCAG AA contrast on the card background.
- `cd web && npm test` and `scripts/ci.sh` pass.

### T209 — Refactor: move feature extraction out of patterns.py
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: pipeline/src/routine_watch/patterns.py, pipeline/src/routine_watch/pattern_features.py (new), docs/CODEMAP.md
- owner: ian-claude-standard-2
- claimed: 2026-10-17T09:58Z
- pr: #199
- rating: 5/5 clear

What: `patterns.py` is 786 lines mixing feature extraction from session history (`_score` … `extract_features`, ~lines 578–786) with signal scoring and evidence text. Move the extraction half into `pattern_features.py` so each module has one job. Behaviour must not change.
Interface: `pattern_features.extract_features` (+ its private helpers and `Features` if that keeps imports acyclic); `patterns` re-exports `extract_features` and `Features` so existing callers and tests keep working unchanged.
Acceptance:
- `patterns.py` under 550 lines; no existing test edited except import lines.
- `scripts/e2e.sh` still 23/23 (or current count), identical pattern rankings.
- CODEMAP note for the new module; `scripts/ci.sh` passes.

### T210 — Live screen: end-of-session summary against the resident's normal
- status: done
- class: standard
- priority: 2
- kind: feature
- source: proposed
- deps: —
- area: web/src/live/SessionSummary.tsx (new), web/src/live/SessionSummary.test.tsx (new), web/src/live/LiveSession.tsx, web/src/live/LiveSession.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T10:03Z
- pr: #204
- rating: 5/5 clear

What: Rationale: on demo day the live session just stops; a one-glance close ("Finished in 3m 40s, usually ~2m 50s · 2 errors, usually 0–1") makes the per-resident-baseline idea land for judges (Clarity). Shown when the `session_end` message arrives, above the existing flag/Open alert block.
Interface: `SessionSummary({durationS, errorCount, usualDurationS?, usualErrors?})`. Duration from the session_end payload if present, else first→last step event timestamps; the resident's normal from data the web already loads (`web/src/resident/api.ts`); omit the "usually" parts when unavailable. No pipeline or contract change.
Acceptance:
- Tests: renders with and without the baseline; plain wording, no "diagnos"; uses existing `web/src/ui` components/CSS classes, no inline styles.
- `cd web && npm test` and `scripts/ci.sh` pass.

### T211 — Test: alert "Copy summary" text keeps the safe wording
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/alert/alertText.test.ts
- owner: ian-claude-light-2
- claimed: 2026-10-17T10:00Z
- pr: #198
- rating: 4/5 clear, but acceptance criterion about display name required a small fix to alertText.ts beyond pure test-writing

What: T199 (#189) added `web/src/alert/alertText.ts`, the text a nurse pastes into the chart. Pin its wording rules with tests.
Interface: read only `web/src/alert/alertText.ts` and `web/src/alert/alertText.test.ts`; use the alert fixture the existing test uses.
Acceptance:
- New tests: the summary says "consistent with" for patterns, contains no "diagnos" and no "has <pattern>"; includes each error's time; names the resident by display name, not the raw id (e.g. not "mrs-k"); works with zero patterns.
- `cd web && npx vitest run src/alert/alertText.test.ts` passes.

### T213 — Alert view: heading order, focus on open, landmark
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/alert/AlertView.tsx, web/src/alert/AlertView.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T10:08Z
- pr: #202
- rating: 5/5 clear

What: The alert is the screen judges and nurses read most. Make it navigable by screen reader and keyboard: one `h1` (resident + "Flagged for review"), section `h2`s in reading order (What changed, Errors, Evidence, Patterns, Suggested checks, Feedback), the view wrapped in a labelled `main`/`section`, and focus moved to the `h1` when an alert opens.
Interface: markup-only changes in `AlertView.tsx`; keep existing class names and copy.
Acceptance:
- Tests: heading levels via `getAllByRole('heading')`, `h1` has focus after render, existing tests still pass unchanged in meaning.
- `cd web && npm test` and `scripts/ci.sh` pass.

### T214 — TaskMapLegend: CSS classes instead of inline styles
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/live/TaskMapLegend.tsx, web/src/live/taskMap.css, web/src/live/TaskMapLegend.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T10:08Z
- pr: #201
- rating: 5/5 clear

What: `TaskMapLegend.tsx` has three inline `style={{...}}` objects (list, item, swatch padding). Move them to classes in the existing `web/src/live/taskMap.css`, same pattern as T197/T200 (#193, #195). No visual change.
Interface: read only the area files plus `web/src/index.css` for the `--space-*` tokens. Class names `task-map-legend`, `task-map-legend__item`, `task-map-legend__swatch`.
Acceptance:
- `grep -c "style={{" web/src/live/TaskMapLegend.tsx` is 0
- existing TaskMapLegend tests still pass unchanged
- `cd web && npm test -- TaskMapLegend` and `scripts/ci.sh` pass

### T215 — DriftCard: CSS classes instead of inline styles
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/DriftCard.tsx, web/src/resident/driftCard.css, web/src/resident/DriftCard.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T10:13Z
- pr: #203
- rating: 5/5 clear

What: `DriftCard.tsx` sets text colour inline, including a `state === 'trending'` ternary. Move it to a new `web/src/resident/driftCard.css` keyed off the existing `data-state` attribute (`.drift-card[data-state="trending"] .drift-card__summary { color: var(--error-amber-text) }`). No visual change.
Interface: read only the area files and `web/src/resident/heatCalendar.css` as the example.
Acceptance:
- `grep -c "style={{" web/src/resident/DriftCard.tsx` is 0
- test asserts the trending summary has the `drift-card__summary` class and the card keeps `data-state="trending"`
- `cd web && npm test -- DriftCard` and `scripts/ci.sh` pass

### T216 — HeatCalendar grid and cells: CSS classes instead of inline styles
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/HeatCalendar.tsx, web/src/resident/heatCalendar.css, web/src/resident/HeatCalendar.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T10:17Z
- pr: #206
- rating: 5/5 clear

What: after T197 moved the legend to `heatCalendar.css`, the grid (line ~24) and day cells (~30, ~52) still use inline styles. Move static layout to classes (`heat-grid`, `heat-cell`). A per-cell colour that depends on the score may stay inline only as a single CSS custom property (e.g. `style={{ '--heat': ... }}`). No visual change.
Interface: read only the area files.
Acceptance:
- HeatCalendar.tsx has at most one inline style, and it only sets a CSS custom property
- existing HeatCalendar tests pass; one new test asserts cells have the `heat-cell` class
- `cd web && npm test -- HeatCalendar` and `scripts/ci.sh` pass

### T217 — Resident detail: heading order, landmark, focus on open
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/ResidentDetail.tsx, web/src/resident/ResidentDetail.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T10:17Z
- pr: #208
- rating: 5/5 clear

What: same accessibility pass as T213 does for the alert view, on the resident detail screen: one `h1` (the resident's display name), section headings as `h2` in visual order, the screen wrapped in `<main>` or a labelled region, and focus moved to the `h1` when the screen opens so a screen-reader user hears whose page it is.
Interface: ResidentDetail only; don't touch child components (BaselineChart, HeatCalendar, DriftCard, SessionList, ContextTimeline) beyond what ResidentDetail renders around them.
Acceptance:
- test: exactly one `heading` of level 1 with the resident's name; it has focus after render
- test: no heading level is skipped (h1 → h2)
- `cd web && npm test -- ResidentDetail` and `scripts/ci.sh` pass

### T194 — smoke.sh: seeded alert survives /demo/reset
- status: done
- class: light
- priority: 2
- kind: test
- deps: T178
- area: scripts/smoke.sh
- owner: ian-claude-light-2
- claimed: 2026-10-17T11:08Z
- pr: #220
- note: released: stale claim (max_API_light, 90+ min)
- rating: 3/5 ambiguous: a literal 'does the alert persist' check fails against real behavior since /demo/reset intentionally drops live-session alerts; had to add a replay step to make it meaningful

What: Reset must only drop live sessions and feedback, not the seeded demo history. After smoke.sh's POST /demo/reset, check GET /alerts still returns at least one alert.
Interface: read `scripts/smoke.sh` (the `/demo/reset` block at the end and the existing `/alerts` check).
Acceptance:
- New PASS/FAIL line "GET /alerts after reset" right after the reset check.
- `bash -n scripts/smoke.sh` and `scripts/ci.sh` pass; against `scripts/dev.sh up` all checks pass.

### T218 — Test: DemoBanner disables Reset while resetting and clears the error on retry
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/ui/DemoBanner.tsx, web/src/ui/DemoBanner.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T10:18Z
- pr: #207
- rating: 5/5 clear

What: the Reset demo button (T189, T200) is the presenter's recovery path, so pin its behaviour: the button is disabled while the reset promise is pending, and a "Couldn't reset the demo" error from a failed attempt disappears after a later successful reset. If the second case fails today, fix it in DemoBanner.tsx.
Interface: `DemoBanner({ onReset })` with an injected fake `onReset`; read only the area files.
Acceptance:
- test: pending reset → button disabled; resolved → enabled
- test: reject then resolve → `role="alert"` error gone
- `cd web && npm test -- DemoBanner` and `scripts/ci.sh` pass

### T219 — Bug: live session's final error list differs from replay for sequence scenarios
- status: done
- class: standard
- priority: 1
- kind: bug
- deps: —
- area: pipeline/src/routine_watch/live.py, pipeline/tests/test_live_matches_replay.py, pipeline/tests/test_live.py
- owner: ian-claude
- claimed: 2026-10-17T10:20Z
- pr: #211
- rating: 4/5 the interface was clear, but it does not mention that test_live_camera.py pins the camera path's session_end to live's message for message, so live_camera.py needs the same field in the same PR

What: Played live, `tea_sequence_error`, `tea_self_corrected`, `meds_pill_before_water` and `meds_self_corrected` stream a transient `omission` for a dependency that happens later, so the errors the demo ends on are not the ones `expected.yaml` checks (xfailed in `test_live_matches_replay.py`, noted again in T202/#197). Keep streaming errors as now, but make `session_end` carry the healed final list so the screen can settle on the right answer.
Interface: the `session_end` message gains `errors` = the `final` `classify_errors(..., ended=True)` result `live.py` already computes, serialised like the `error` message's `error`. The `live.py` docstring says streamed errors are provisional and `session_end.errors` is authoritative. No change to `contracts.py`.
Acceptance:
* `test_live_matches_replay.py` compares `session_end["errors"]` against `expected.yaml` for every scenario; the `_SEQUENCE_HEALS_FROM_A_TRANSIENT_OMISSION` xfail set is removed and all scenarios pass.
* Existing live tests still pass; `scripts/ci.sh` passes.

### T220 — Live screen: settle on session_end's final error list
- status: done
- class: light
- priority: 1
- kind: bug
- deps: T219
- area: web/src/live/useLiveSession.ts, web/src/live/mockLiveStream.ts, web/src/live/useLiveSession.test.ts
- owner: ian-claude-light-2
- claimed: 2026-10-17T10:35Z
- pr: #213
- rating: 5/5 clear

What: After T219 the `session_end` WebSocket message carries `errors`, the session's final (healed) error list. The live screen should replace its streamed error list with it, so a step reported missed mid-session but done later no longer shows as missed once the session ends.
Interface: read `web/src/live/useLiveSession.ts` (message union and reducer, `case 'session_end'`), `web/src/live/mockLiveStream.ts`, and the `session_end` part of the module docstring in `pipeline/src/routine_watch/live.py`. Add optional `errors` to the `session_end` message type (same shape as the `error` message's `error`); on `session_end` with `errors`, set the state's errors to it; without `errors` (older server), keep the streamed list. Add `errors` to the mock's `session_end`.
Acceptance:
* test: a streamed omission followed by a `session_end` whose `errors` lack it leaves only the final errors
* test: a `session_end` without `errors` keeps the streamed list
* `cd web && npm test` and `scripts/ci.sh` pass

### T221 — Copy summary uses the resident's real name, not one guessed from the id
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/alert/alertText.ts, web/src/alert/alertText.test.ts, web/src/alert/AlertView.tsx
- owner: ian-claude
- claimed: 2026-10-17T10:35Z
- pr: #214
- note: released by ian-claude-standard-2: run ended without progress; partial work on branch task/T221-wip-1031: start from it (git switch task/T221-wip-1031 && git merge origin/main)
- rating: 4/5 clear on the interface, but it didn't mention AlertView's h1 also calls residentDisplayName, so deleting it changes the heading too

What: T211 (#198) added `residentDisplayName` in `alertText.ts`, which builds "Mrs. K" from the id `mrs-k`, while the rest of the app (`App.tsx` ~line 50) shows `resident.name` from the API, so the two can disagree for other residents. Pass the real name in instead.
Interface: read `web/src/alert/alertText.ts`, `web/src/alert/alertText.test.ts`, `web/src/alert/AlertView.tsx` (it already calls `fetchResident(alert.resident_id)`). Change to `alertText(alert: Alert, residentName?: string)` using `residentName ?? alert.resident_id`; delete `residentDisplayName` and `TITLES`. In `AlertView.tsx`, keep the fetched resident's `name` in state next to the care records and pass it to `alertText`.
Acceptance:
* test: with a name, the first line is `Resident: <name>`; without, it falls back to the id; existing wording tests still pass
* `cd web && npm test` and `scripts/ci.sh` pass

### T149 — API: GET /monitoring and PUT /rooms/{room}/monitoring
- status: done
- class: standard
- priority: 3
- kind: feature
- deps: T148
- area: pipeline/src/routine_watch/api.py, pipeline/tests/test_api_monitoring.py (new)
- source: proposed
- owner: ian-claude-standard
- claimed: 2026-10-17T11:25Z
- pr: #226
- note: released by ian-claude-standard-2: run ended without progress; partial work on branch task/T149-wip-1051: start from it (git switch task/T149-wip-1051 && git merge origin/main)
- rating: 4/5 clear, except the WIP branch noted in the task had drifted far from main (unrelated demo.py/web diffs) and needed re-applying just the api.py/test slice onto fresh main

What: Expose the T148 store so the dashboard's pause switch is real. While a room is paused, `/ws/live` for a scenario whose resident is in that room sends one `{"type": "paused", "room": ...}` message and closes instead of streaming frames (no camera data processed).
Interface: `GET /monitoring` → `{"paused_rooms": [...]}`; `PUT /rooms/{room}/monitoring` body `{"on": bool}` → `{"room": str, "on": bool}`; uses `monitoring.get_monitoring_store()`. Room→resident comes from `demo.demo_residents()`; unknown room → 404.
Acceptance:
- tests: default empty, pause/resume round trip, 404 for unknown room, paused live session gets the `paused` message and no frames (TestClient websocket); store reset between tests.
- `scripts/ci.sh` passes.

### T222 — Review: Copy summary says "Change flagged" for slow-trend alerts
- status: done
- class: light
- priority: 1
- kind: bug
- deps: T221
- area: web/src/alert/alertText.ts, web/src/alert/alertText.test.ts
- owner: ian-claude
- claimed: 2026-10-17T10:48Z
- pr: #217
- source: reviewer
- rating: 5/5 clear - the task named the exact file, the exact conditional and the two test assertions

What: `alertText` (T199/T211, #189/#198) always writes the line `Change flagged for review`, but `Alert.kind` can be `'trend'`, which the overview labels `Slow trend for review` (`web/src/App.tsx` ~line 112). A nurse pasting a trend alert into the chart records the wrong kind of finding.
Interface: read `web/src/alert/alertText.ts`, `web/src/alert/alertText.test.ts`, and `AlertKind` in `web/src/contracts.ts`. Replace the fixed string with `alert.kind === 'trend' ? 'Slow trend for review' : 'Change flagged for review'`.
Acceptance:
* test: a `kind: 'trend'` alert's copied text contains `Slow trend for review` and not `Change flagged`; a change alert keeps `Change flagged for review`
* `cd web && npm test` passes

### T223 — SessionSummary: CSS file instead of inline <style>, reuse formatDuration
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/live/SessionSummary.tsx, web/src/live/sessionSummary.css, web/src/live/SessionSummary.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T10:27Z
- pr: #210
- rating: 5/5 clear

What: `SessionSummary.tsx` (from PR #204) injects a `<style>` block, against the CSS-class cleanup done in T214/T215 (see `web/src/resident/driftCard.css` for the pattern), and re-implements `formatDuration` that `web/src/resident/format.ts` already exports.
Interface: move the two rules into `web/src/live/sessionSummary.css` imported by the component; use `formatDuration` from `../resident/format.ts` only if its output matches the current strings in `SessionSummary.test.tsx`, otherwise keep the local one and add a one-line comment why.
Acceptance:
- no `<style>` element left in `SessionSummary.tsx`; rendered text unchanged
- existing SessionSummary tests pass unchanged (only add, don't loosen)
- `cd web && npx vitest run src/live/SessionSummary.test.tsx` and `scripts/ci.sh` pass

### T192 — /demo/reset also resumes paused room monitoring
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: T149
- area: pipeline/src/routine_watch/api.py (demo_reset only), pipeline/tests/test_api_demo_reset.py
- owner: ian-claude-light-2
- claimed: 2026-10-17T11:34Z
- pr: #229
- rating: 5/5 clear

What: After T149 a rehearsal can pause a room, and `/demo/reset` leaves it paused. Make reset also call the monitoring store's `reset()`.
Interface: read `pipeline/src/routine_watch/api.py` (`demo_reset`), `pipeline/src/routine_watch/monitoring.py` (`get_monitoring_store`, `MonitoringStore.reset`), `pipeline/tests/test_api_demo_reset.py`.
Acceptance:
- Test: PUT a room to paused, POST /demo/reset, GET /monitoring shows no paused rooms.
- `cd pipeline && pytest tests/test_api_demo_reset.py` and `scripts/ci.sh` pass.

### T224 — LiveScreen: CSS file instead of inline <style>
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/live/LiveScreen.tsx, web/src/live/liveScreen.css
- owner: ian-claude-light-2
- claimed: 2026-10-17T10:40Z
- pr: #216
- rating: 5/5 clear

What: `web/src/live/LiveScreen.tsx` (line ~31) injects a `<style>` block; move it to a CSS file like `web/src/resident/driftCard.css` (T215).
Interface: new `web/src/live/liveScreen.css` imported by `LiveScreen.tsx`; same class names, same rules.
Acceptance:
- no `<style>` element left in `LiveScreen.tsx`; no visual or text change
- `cd web && npx vitest run src/live` and `scripts/ci.sh` pass

### T226 — Ghost replay: say the figure is a stand-in for demo recordings
- status: done
- class: light
- priority: 2
- kind: feature
- deps: —
- area: web/src/evidence/GhostReplay.tsx, web/src/evidence/GhostReplay.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T11:17Z
- pr: #221
- note: released by ian-claude-standard: run ended without progress; partial work on branch task/T226-wip-1052: start from it (git switch task/T226-wip-1052 && git merge origin/main)
- rating: 4/5 clear, but task was already mostly implemented on the WIP branch handed to me

What: Since T207 (PR #205) the demo's recordings get a made-up body (`pipeline/src/routine_watch/stick_figure.py`) so the ghost replay has something to draw. A judge or nurse should not mistake it for tracked motion, so add a small muted caption under the replay: "Demo recording: the body is drawn as a stand-in; the hand follows the tracked hand box."
Interface: read `web/src/evidence/GhostReplay.tsx` and its test only. Caption is plain text under the existing canvas/caption row, using existing muted text tokens (`var(--muted)`), readable on the dark card (see T208 for the contrast bug to avoid).
Acceptance:
- caption renders under the ghost replay; test asserts the text
- `cd web && npx vitest run src/evidence` and `scripts/ci.sh` pass

### T227 — Test: stand-in skeleton never changes what the recogniser reads
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_stick_figure.py
- owner: ian-claude-light-2
- claimed: 2026-10-17T11:22Z
- pr: #224
- note: released by ian-claude-light-2: run ended without progress; partial work on branch task/T227-wip-1053: start from it (git switch task/T227-wip-1053 && git merge origin/main)
- rating: 5/5 clear

What: `evidence._with_skeleton` adds poses/hands to box-only frames and promises "a frame read by the recogniser still says exactly what it did before". Pin that promise for every frame-level scenario.
Interface: read `pipeline/src/routine_watch/evidence.py` (`_with_skeleton`), `pipeline/src/routine_watch/stick_figure.py`, `pipeline/src/routine_watch/replay.py` (`load_scenario`, `SCENARIOS_DIR`). For each scenario dir under `tests/scenarios/` with a `frames.jsonl`, assert the recogniser's step/error output on the original frames equals the output on `_with_skeleton`-mapped frames (use whatever function `replay.py` already uses to turn frames into errors).
Acceptance:
- parametrized over all frame scenarios; fails if a stand-in landmark changes any error
- `cd pipeline && python -m pytest tests/test_stick_figure.py -q` and `scripts/ci.sh` pass

### T228 — Bug: flaky "moves focus to the h1" tests turn main CI red
- status: done
- class: light
- priority: 0
- kind: bug
- deps: —
- area: web/src/alert/AlertView.test.tsx, web/src/resident/ResidentDetail.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T10:39Z
- pr: #215
- rating: 5/5 clear

What: `main` CI failed on f679686 and 495a460 (and a rerun) in `AlertView.test.tsx > moves focus to the h1 once the alert loads` (T213, #202); the same race shows locally in `ResidentDetail.test.tsx > moves focus to the h1 once the resident loads` (T217, #208). The tests check `document.activeElement` right after `findByRole('heading')` resolves, but focus is set in an effect that can land a tick later under CI load. Also seen once: `shows a loading state for the evidence card…` timing out on `findByText('No replay available')` at the 1 s default.
Interface: read only the two test files. In both focus tests, replace the bare `expect(document.activeElement).toBe(heading)` with `await waitFor(() => expect(document.activeElement).toBe(heading))`. In AlertView's evidence loading-state test, wrap `releases.forEach(...)` in `await act(async () => { ... })` before the `findByText`. Do not change component code or loosen any other assertion.
Acceptance:
- `cd web && for i in 1 2 3 4 5; do npx vitest run || break; done` passes all 5 full runs
- `scripts/ci.sh` passes

### T230 — Review: live summary's "usually ~" averages the resident's whole history, drift included
- status: done
- class: standard
- priority: 1
- kind: bug
- source: reviewer
- deps: T220
- area: pipeline/src/routine_watch/demo.py, pipeline/src/routine_watch/api.py, web/src/live/LiveSession.tsx, web/src/resident/types.ts
- owner: ian-claude
- claimed: 2026-10-17T11:02Z
- pr: #222
- rating: 5/5 clear - the interface named the exact fields and where to compute them; only thing not mentioned was alerts.py's Baseline(**resident['baseline']) splat, which breaks when the payload grows

What: `useResidentBaseline` in `web/src/live/LiveSession.tsx` averages `duration_s` and error totals over *every* non-assisted session of mrs-k, including the recent bad days that triggered her flag. So the end-of-session "usually ~Xs / ~N errors" is inflated by exactly the change we're flagging, and disagrees with the pipeline's baseline, which is anchored to the earliest `BASELINE_DAYS` (demo.py, SPEC §8 beat 6). It also re-implements baseline logic in the web.
Interface: in `demo.py`, where the resident baseline is built from the early window, also compute `usual_duration_s` and `usual_errors` (mean over the same early, non-assisted sessions) and serve them inside `baseline` from `GET /residents/{id}`. Add both as optional fields to `Baseline` in `web/src/resident/types.ts`; have `LiveSession.tsx` read them instead of averaging `sessions`, and delete `average`/`sessionErrorTotal`.
Acceptance:
- pytest: mrs-k's `baseline.usual_errors` equals the mean over her first `BASELINE_DAYS` own sessions, and is lower than the whole-history mean
- `LiveSession.test.tsx` shows the "usually" values from the mocked `baseline`, not from `sessions`
- `scripts/ci.sh` passes

### T232 — Bug: alert feedback buttons (Confirmed / False alarm / cause) render unstyled
- status: done
- class: light
- priority: 1
- kind: bug
- deps: —
- area: web/src/alert/FeedbackButtons.tsx, web/src/alert/alert.css, web/src/alert/FeedbackButtons.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T11:06Z
- pr: #218
- source: tester
- rating: 5/5 clear

What: On the alert view (main 13032a4), the Feedback section's "Confirmed" / "False alarm" and the "What was it?" cause buttons show as tiny browser-default buttons (white border, small text), unlike every other button on the dashboard. "Confirmed" is the demo's closing click (SPEC §10) and is easy to miss. `.feedback-button` only has an `[aria-pressed='true']` rule in `alert.css`; there is no base style.
Repro: `OFFLINE_MODE=true scripts/dev.sh up`, open http://localhost:5173, let the live tea session finish, click "Open alert", scroll to Feedback.
Expected: buttons use the shared `Button` from `web/src/ui/Button.tsx` (or the `.btn` / `.btn--secondary` classes in `index.css`) at normal size, pressed state still visible. Actual: unstyled default buttons.
Interface: in `FeedbackButtons.tsx` render the buttons with `ui/Button` (or add `btn btn--secondary` classes); keep `aria-pressed` and the existing pressed-state rule.
Acceptance:
- Confirmed / False alarm / cause buttons share the dashboard button look; pressed one stays visibly distinct (not colour alone)
- existing FeedbackButtons tests pass; `scripts/ci.sh` passes

### T225 — LiveSession: CSS file instead of inline <style>
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: T220
- area: web/src/live/LiveSession.tsx, web/src/live/liveSession.css
- owner: ian-claude-light-2
- claimed: 2026-10-17T12:02Z
- pr: #236
- note: released by ian-claude-light-2: run ended without progress; partial work on branch task/T225-wip-1147: start from it (git switch task/T225-wip-1147 && git merge origin/main)
- rating: 5/5 clear

What: `web/src/live/LiveSession.tsx` (line ~140) injects a `<style>` block; move it to a CSS file like `web/src/resident/driftCard.css` (T215). Waits for T220, which edits the same file.
Interface: new `web/src/live/liveSession.css` imported by `LiveSession.tsx`; same class names, same rules.
Acceptance:
- no `<style>` element left in `LiveSession.tsx`; no visual or text change
- `cd web && npx vitest run src/live` and `scripts/ci.sh` pass

### T233 — Test: de-flake DemoBanner reset test under load
- status: done
- class: light
- priority: 1
- kind: test
- deps: —
- area: web/src/ui/DemoBanner.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T11:07Z
- pr: #219
- rating: 5/5 clear

What: PR #217 reported `DemoBanner.test.tsx` (reset cases from T218) failing intermittently in full `scripts/ci.sh` runs while passing alone. Make its async assertions wait instead of checking state right after a click/findBy.
Interface: read `web/src/ui/DemoBanner.tsx` and `web/src/ui/DemoBanner.test.tsx` only. Wrap post-click assertions (disabled state, error text appearing/disappearing) in `await waitFor(...)` or use `findBy*`/`waitForElementToBeRemoved`; resolve fake `onReset` promises inside `act`.
Acceptance:
- No behaviour change in DemoBanner.tsx.
- `cd web && for i in 1 2 3 4 5; do npm test -- --run DemoBanner || exit 1; done` passes, and `scripts/ci.sh` passes.

### T234 — Unit overview: usable at phone width (375 px)
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/index.css (overview rules only: .unit-filter*, .resident-list, .resident-row, .resident-open*, .resident-identity/name/room/status/pattern), web/src/overview/overview.css (new), web/src/overview/UnitOverview.tsx, web/src/overview/UnitOverview.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T11:12Z
- pr: #225
- rating: 5/5 clear

What: Nurses check the board on a phone on the floor, but there are no responsive rules anywhere in web/ (no `@media` except reduced-motion). Move the overview's rules out of index.css into `overview/overview.css` (imported by UnitOverview.tsx) and add a `@media (max-width: 480px)` block so each resident row stacks name/room, status chip + top pattern, and sparkline without horizontal scroll.
Interface: `web/src/overview/overview.css`; UnitOverview.tsx adds `import './overview.css'`. No markup or class name changes beyond what the stacking needs.
Acceptance:
- No horizontal scroll on the overview at 375 px wide; filter buttons wrap and stay ≥44 px tall tap targets.
- Desktop layout unchanged (same rules, just moved).
- Existing UnitOverview tests still pass; `scripts/ci.sh` passes.
- PR body notes the viewport widths checked.

### T235 — Live screen and task map: usable at phone width (375 px)
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/live/liveScreen.css, web/src/live/taskMap.css
- owner: ian-claude-standard
- claimed: 2026-10-17T11:16Z
- pr: #223
- rating: 5/5 clear

What: The live session view (routine picker, task map of steps, skeleton panel) has no responsive rules. Add `@media (max-width: 480px)` blocks to the two CSS files so the routine picker wraps, the task-map steps stack in one column and the skeleton panel scales to the screen width, so a nurse can follow a live session on a phone.
Interface: CSS only, in the two listed files. Don't touch LiveSession.tsx / liveSession.css (T225, T230 work there).
Acceptance:
- No horizontal scroll on the live screen at 375 px; step labels and error times stay readable (no text below var(--text-sm)).
- Desktop layout unchanged.
- `scripts/ci.sh` passes; PR body notes the viewport widths checked.

### T236 — Review: live session_end flag/alert_id can disagree with the resident's real status (alert 404)
- status: done
- class: standard
- priority: 1
- kind: bug
- source: reviewer
- deps: —
- area: pipeline/src/routine_watch/live.py, pipeline/tests/test_live.py
- owner: ian-claude
- claimed: 2026-10-17T11:24Z
- pr: #228
- rating: 5/5 clear - exact repro, the fix was the interface note verbatim; only unstated bit was that two sibling test files (test_live_matches_replay.py, test_live_camera.py) assert the old per-recording flag and had to be updated too

What: `session_messages` (live.py ~L282-305) sends `flag` from `score_session`, which judges against the *scenario's* `expected.history`, and sets `alert_id = f"alert-{resident_id}"` whenever that flag is true. But `/alerts` only has an alert when the resident (mrs-k) is flagged over her own history (`_resident_flagged`). Reproduced with `session_log.reset()` + one live run for mrs-k: `tea_kettle_twice` → `flag: True, alert_id: alert-mrs-k`, resident status `watch`, `GET /alerts/alert-mrs-k` → 404 ("View alert" dead-ends). `tea_no_kettle` → `flag: False` while she is `flagged` on the dashboard. The two demo picks (tea_skip_teabag_pour_twice, meds_skip_water) happen to agree, so this bites any other scenario or the camera path.
Interface: after `_record(...)`, compute `resident_name = _resident_flagged(resident_id)` once (reuse it for the push check) and send `flag = resident_name is not None` and `alert_id = f"alert-{resident_id}" if resident_name else None`, so the live screen says what the dashboard says. Keep the per-recording score as-is. Update the module docstring note about `flag` (~L75).
Acceptance:
- New test in `pipeline/tests/test_live.py`: for mrs-k after reset, `tea_kettle_twice` and `tea_no_kettle` each end with `alert_id` non-null iff `GET /alerts/{alert_id}` returns 200 (TestClient), and `flag` equals the resident's status == flagged.
- Existing live/notify tests still pass; `scripts/ci.sh` passes.

### T237 — Test: de-flake AlertView "loading state for the evidence card" test under load
- status: done
- class: light
- priority: 1
- kind: test
- deps: —
- area: web/src/alert/AlertView.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T11:27Z
- pr: #227
- rating: 5/5 clear

What: `AlertView > shows a loading state for the evidence card before the replay resolves` fails intermittently under full-suite parallelism (PR #221 CI run 39028279950, and earlier per LESSONS): `findByText('No replay available')` times out at the default 1000 ms after the deferred replay fetch is released. Make it deterministic without changing app code.
Interface: read only `web/src/alert/AlertView.test.tsx` and `web/src/evidence/ReplayPlayer.tsx` (renders `No replay available` when frames are empty). Fix the test only, e.g. release inside `act` then `await waitFor(() => expect(screen.getByText('No replay available')).toBeTruthy(), { timeout: 3000 })`, and make sure any other `/sessions/` fetches the view makes also resolve (inspect `fetchMock.mock.calls`).
Acceptance:
- No app code changed; only AlertView.test.tsx.
- `cd web && for i in 1 2 3 4 5; do npx vitest run --pool=threads --maxWorkers=1 src/alert/AlertView.test.tsx || exit 1; done` passes, and `scripts/ci.sh` passes.

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

### T229 — Test: PatternList fixtures use unique pattern ids (no duplicate-key warning)
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/alert/PatternList.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T12:31Z
- pr: #247
- note: released by ian-claude-light-2: run ended without progress; partial work on branch task/T229-wip-1210: start from it (git switch task/T229-wip-1210 && git merge origin/main)
- rating: 5/5 clear

What: `PatternList.test.tsx > never uses diagnostic wording` renders two `pattern()` fixtures that both have `pattern_id: 'delirium'`, so React logs "Encountered two children with the same key" in every CI run, hiding real warnings.
Interface: read `web/src/alert/PatternList.test.tsx` only. Give the second fixture a different `pattern_id` (e.g. `pattern({ pattern_id: 'infection', urgency: 'urgent' })`); fix any other test in the file that renders duplicate ids the same way.
Acceptance:
- `cd web && npx vitest run src/alert/PatternList.test.tsx 2>&1 | grep -c "same key"` prints 0; all tests pass
- `scripts/ci.sh` passes

### T231 — Test: integration.sh dashboard check retries instead of failing on a cold Vite start
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: scripts/integration.sh
- owner: ian-claude-light-2
- claimed: 2026-10-17T12:39Z
- pr: #249
- source: integration
- rating: 5/5 clear

What: The integration run on main @ 60dce5a failed with "dashboard did not render (no 'Routine Watch' in DOM)", but the orchestrator reran `scripts/integration.sh` on the same sha at 10:52 UTC and it passed, so it is a flake (likely the headless-Chrome DOM dump racing Vite's first compile). Make the check robust, not looser.
Interface: in `scripts/integration.sh`, the "Rendered dashboard" block (around line 45): retry the `--dump-dom` up to 3 times with a 3 s sleep between attempts before calling `fail`; keep both existing grep checks unchanged.
Acceptance:
- a slow first render no longer fails the run; a dashboard that never renders still fails with the same message
- `scripts/integration.sh` prints OK and `scripts/ci.sh` passes

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

### T241 — Test: no user-facing web copy says "diagnose" or "has <condition>"
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/wording.test.ts (new)
- owner: ian-claude-light-2
- claimed: 2026-10-17T12:45Z
- pr: #250
- rating: 5/5 clear

What: The wording rule (AGENTS.md: the product flags a change for review, lists patterns it is "consistent with", never "diagnoses") is only checked per component. Add one guard test that scans every non-test `web/src/**/*.ts(x)` file's string literals and JSX text for `diagnos` (case-insensitive) and fails with the file and line.
Interface: `web/src/wording.test.ts` using `import.meta.glob('./**/*.{ts,tsx}', { query: '?raw', import: 'default', eager: true })`, skipping `*.test.*` and `contracts.ts`. Strip `//` and `/* */` comments before matching (LiveSession.tsx and PatternList.tsx mention "never diagnoses" in comments, which is fine).
Acceptance:
- Test passes on current main; temporarily adding `'Diagnosed with X'` to any component makes it fail with that file named (say so in the PR body).
- `scripts/ci.sh` passes.

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

### T245 — Smoke: check GET /monitoring and a PUT round-trip
- status: done
- class: light
- priority: 2
- kind: test
- deps: T192
- area: scripts/smoke.sh
- owner: ian-claude-standard
- claimed: 2026-10-17T12:58Z
- pr: #255
- rating: 5/5 clear

What: `scripts/smoke.sh` doesn't exercise the monitoring endpoints added in T149 (#226). Add checks so the tester catches a broken pause switch.
Interface: read `scripts/smoke.sh` (copy the `curl "${CURL_OPTS[@]}"` + `pass`/`fail` pattern) and `pipeline/src/routine_watch/api.py` (search `monitoring`). Before the final `/demo/reset` block: GET `/monitoring` returns JSON with `paused_rooms`; PUT pause on the demo resident's room, GET shows it paused, PUT resume, GET shows it gone; PUT on an unknown room returns 404. Always resume the room even if a check fails.
Acceptance:
- `scripts/dev.sh up && scripts/smoke.sh` passes with the new checks; `scripts/dev.sh down`
- `bash -n scripts/smoke.sh` and `scripts/ci.sh` pass

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
- status: done
- class: heavy
- priority: 2
- kind: improvement
- source: reviewer
- deps: T250, T251
- area: contracts/resident.schema.json, contracts/handoff.schema.json, contracts/README.md, pipeline/tests/test_api_payload_contracts.py
- owner: ian-claude
- claimed: 2026-10-17T12:18Z
- pr: #246
- rating: 4/5 the area listed only contracts/*.schema.json + a test, but those files are generated from pipeline/src/routine_watch/contracts.py, so the source model had to change too; and GET /residents returns a projection (api._SUMMARY_FIELDS), not the detail, so it needs its own schema - three files, not two

What: REVIEW.md noted the resident and handoff payloads have no `contracts/` schema and web types are hand-mirrored (`web/src/overview/types.ts`, `web/src/handoff/types.ts`), which is how fields drift. Add schemas describing today's shapes (incl. `top_pattern`, `monitoring_paused`/`paused` from T251).
Interface: Read `api.py` `list_residents`/`get_resident`/`shift_handoff`, `handoff.py`, `demo.py`, and the two web type files. Schemas only plus a test; don't change payload shapes. If a web type disagrees with the API, note it in the PR and file nothing else in this PR.
Acceptance:
- pytest validates `GET /residents`, `GET /residents/{id}` for every demo resident, and `GET /handoff` against the schemas (fakes only).
- `contracts/README.md` lists both; `scripts/ci.sh` passes.

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

### T253 — Shift handoff screen: show the rooms whose monitoring is paused
- status: done
- class: light
- priority: 2
- kind: feature
- deps: T251
- area: web/src/handoff/types.ts, web/src/handoff/mockHandoff.ts, web/src/handoff/Handoff.tsx, web/src/handoff/Handoff.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T13:06Z
- pr: #259
- rating: 5/5 clear

What: Show T251's new `paused` list on the handoff screen so the incoming nurse sees which rooms weren't watched.
Interface: Read `web/src/handoff/types.ts`, `Handoff.tsx`, `mockHandoff.ts` and T251's docstring in `pipeline/src/routine_watch/handoff.py`. Add `paused: { room: string; resident_id: string; name: string }[]` to the `Handoff` type (treat missing as `[]` for older APIs) and `monitoring_paused?: boolean` to `HandoffResident`. When non-empty, render one line above the rows: "Monitoring paused: <name> (room <room>), ..." and a "Monitoring paused" chip on those residents' rows. Include the line in `handoffText`. Mock gets `paused: []`.
Acceptance:
- Tests: no line when `paused` is empty or missing; line + chip when one room is paused; `handoffText` includes it.
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

### T248 — Test: live session_end flag matches /residents for every scenario
- status: done
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
- status: done
- class: heavy
- priority: 2
- kind: improvement
- deps: T257
- area: contracts/, pipeline/src/routine_watch/contracts.py, pipeline/tests/test_contracts.py, web/src/contracts.ts
- owner: ian-claude
- claimed: 2026-10-17T12:59Z
- pr: #260
- rating: 4/5 the area left out pipeline/src/routine_watch/api_alerts.py (where the feedback POST body is actually defined) and pipeline/tests/test_api_payload_contracts.py (where T257 put the 'real route vs schema' tests), and named web/src/contracts.ts, which is generated and ended up unchanged - the real hand-mirror is web/src/alert/api.ts

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

### T255 — Resident detail: show who consented to monitoring
- status: done
- class: light
- priority: 2
- kind: feature
- source: proposed
- deps: T254
- area: web/src/overview/types.ts, web/src/mock/residents.ts, web/src/mock/residentDetail.ts, web/src/resident/ResidentDetail.tsx, web/src/resident/ResidentDetail.test.tsx, web/src/resident/resident.css
- owner: ian-claude-light-2
- claimed: 2026-10-17T13:43Z
- pr: #266
- note: released by ian-claude-light-2: run ended without progress
- rating: 5/5 clear

What: Show T254's consent record under the monitoring switch: "Consent: Substitute decision-maker (daughter), 2026-09-28". Small grey text, nothing when the field is missing (older API / mock without it).
Interface: Read `web/src/overview/types.ts` (resident type), `web/src/resident/ResidentDetail.tsx` (header with `MonitoringToggle`), and `pipeline/src/routine_watch/demo.py` (T254's `consent: {given_by, on}`). Add optional `consent?: { given_by: string; on: string }` to the resident type; give the three mock residents in `web/src/mock/residents.ts` a consent record.
Acceptance:
- Tests in `ResidentDetail.test.tsx`: consent line renders with given_by and date; no line when `consent` is absent.
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
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_handoff_window.py (new)
- owner: ian-claude-light-2
- claimed: 2026-10-17T13:53Z
- pr: #270
- rating: 5/5 clear

What: `GET /handoff?hours=` is declared `Query(ge=1, le=168)` in pipeline/src/routine_watch/api.py (read `shift_handoff`), but nothing tests the bounds.
Interface: new pytest file using `fastapi.testclient.TestClient(routine_watch.api.app)`; read pipeline/tests/test_handoff.py for fixtures and fakes.
Acceptance:
- hours=1 and hours=168 → 200 with `window_hours` echoed; hours=0 and hours=169 → 422.
- the summary never contains "diagnos".
- `scripts/ci.sh` passes.

### T269 — Contracts: JSON Schema for GET/PUT /monitoring payloads
- status: done
- class: heavy
- priority: 2
- kind: improvement
- deps: T263, T262
- area: contracts/, pipeline/src/routine_watch/contracts.py, pipeline/tests/test_contracts.py, web/src/contracts.ts
- owner: ian-claude
- claimed: 2026-10-17T13:37Z
- pr: #267
- rating: 4/5 the Interface named one schema file (contracts/monitoring.schema.json) but the three monitoring routes answer three shapes, and the acceptance pointed at web/src/contracts.ts, which is generated and gets no payload types - the hand-mirrored copy is web/src/about/monitoringApi.ts. Area also left out test_api_payload_contracts.py, where every other payload's route test lives.

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

### T273 — CI: run the first-load bundle budget check after the web build
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: scripts/ci.sh
- owner: ian-claude
- claimed: 2026-10-17T14:12Z
- pr: #280
- rating: 5/5 clear

What: T260 (#251) added `npm run check:bundle` in web/ but nothing runs it, so the budget never fails a PR. Wire it into CI right after the build.
Interface: in `scripts/ci.sh`, the node loop line `(cd "$d" && npm ci ... && npm run build --if-present)`: append `&& npm run check:bundle --if-present` so it only runs for packages that define it. Read only `scripts/ci.sh` and `web/package.json`. Touch nothing else.
Acceptance:
- `scripts/ci.sh` passes and its output includes the "First-load JS (gzipped):" and "Budget:" lines from web/scripts/check-bundle.mjs.

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

### T179 — Docs: CODEMAP note that handoff reuses the alert's errors
- status: done
- class: light
- priority: 3
- kind: docs
- deps: —
- area: docs/CODEMAP.md
- owner: ian-claude-standard
- claimed: 2026-10-17T14:57Z
- pr: #290
- rating: 5/5 clear

What: T166 (PR #159) made `alerts.session_id_for`, `task_errors`, `distinct_clauses` and `normal_error_rate` public so `handoff.py` writes its summary from the same evidence as the alert, against that resident's own baseline. CODEMAP notes don't say so.
Interface: Read only `docs/CODEMAP.md`, `git show e4f8fe1 --stat` and the module docstrings of `pipeline/src/routine_watch/alerts.py` and `handoff.py`. Edit notes only, not the generated file list.
Acceptance:
* 2-4 line note next to the existing handoff/alert notes naming the four shared functions and why (same steps, same times, same baseline).
* Also one line that handoff rows open the resident's alert by looking up the id in `GET /alerts` (T152, `web/src/handoff/Handoff.tsx` `alertByResident`).
* No other file changed.

### T283 — Resident detail: "What nurses said" — past feedback answers and the pattern ranking they changed
- status: done
- class: heavy
- priority: 2
- kind: feature
- deps: T278
- area: pipeline/src/routine_watch/feedback.py, pipeline/src/routine_watch/api_residents.py, pipeline/tests/test_feedback_history.py, web/src/resident/FeedbackHistory.tsx, web/src/resident/FeedbackHistory.test.tsx, web/src/resident/feedbackHistory.css, web/src/resident/ResidentDetail.tsx, web/src/resident/api.ts, web/src/resident/types.ts
- source: proposed
- owner: ian-claude
- claimed: 2026-10-17T14:36Z
- pr: #287
- rating: 4/5 clear on the interface and the acceptance; it didn't say where the pattern *name* for the card's copy comes from (the store returns a cause id, so the route needed a pattern_names map), and the demo only ever has one alert per resident, so 'answers' can only hold one row per resident today

What: Rationale: the feedback loop (T130, Nice-to-have 8) re-weights patterns silently; judges and nurses can't see the AI learning. Expose a resident's recorded answers and current pattern weights and show them as a small card on the resident detail screen.
Interface: `FeedbackStore.history(resident_id) -> list[{alert_id, verdict, cause, at}]` (newest first) plus existing `pattern_weights()`; route `GET /residents/{id}/feedback` → `{"answers": [...], "pattern_weights": {pattern_id: float}}` (404 for unknown resident) in the residents routes module from T278. Web: `fetchFeedbackHistory(id)` in resident/api.ts, `<FeedbackHistory>` card under the session list: "Confirmed · consistent with <pattern name> · 13:40" rows and "Ranking now favours: <pattern>" when weights exist; empty state "No nurse answers yet". Don't add a contracts/ schema here (contracts/ is busy with T269/T280); note it in the PR for a follow-up.
Acceptance:
- pytest: answers recorded via the feedback POST appear newest-first; `/demo/reset` empties them; unknown resident → 404.
- Vitest: rows, empty state, fetch error state ("Couldn't load feedback"); copy uses "consistent with", never "diagnos".
- `scripts/ci.sh` passes.

### T284 — Review: move shared API state out of api.py to end the `from . import api` cycle
- status: done
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
- status: done
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
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/about/PrivacyPanel.tsx, web/src/about/PrivacyPanel.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T14:23Z
- pr: #279
- rating: 5/5 clear

What: The privacy panel's opt-in bullet predates the consent record (T255) and the audit trail (T262). Make it concrete in nurse-readable words.
Interface: In `web/src/about/PrivacyPanel.tsx`, replace only the last bullet with two: "Residents or their decision-maker opt in; who consented and when is shown on each resident's page." and "Monitoring can be paused per room; every pause and resume is logged with who and when."
Acceptance:
  * `PrivacyPanel.test.tsx` asserts both bullets render
  * `cd web && npm test -- PrivacyPanel` and `scripts/ci.sh` pass

### T287 — Test: alert feedback works keyboard-only
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/alert/FeedbackButtons.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T14:30Z
- pr: #281
- rating: 5/5 clear

What: Nurses on a shared workstation may use only the keyboard; prove the feedback flow (verdict, then cause) needs no mouse.
Interface: Read `web/src/alert/FeedbackButtons.tsx` and its test. With `@testing-library/user-event`: Tab to "Confirmed", press Enter, check `aria-pressed="true"` and the polite status text; Tab into the cause group, press Space on a cause, check its `aria-pressed`. Test-only: if a real keyboard bug shows up, describe it in the PR body instead of fixing it.
Acceptance:
  * New test(s) in `FeedbackButtons.test.tsx` using only keyboard events
  * `cd web && npm test -- FeedbackButtons` and `scripts/ci.sh` pass

### T288 — Smoke: validate /monitoring, room history and the first /ws/live message against contracts/
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: scripts/smoke.sh
- owner: ian-claude-standard
- claimed: 2026-10-17T14:21Z
- pr: #278
- rating: 5/5 clear

What: T279 schema-checks four bodies in smoke.sh; the monitoring and live endpoints (pipeline/src/routine_watch/api_live.py) still get spot checks or none, so contract drift there is only caught by unit tests.
Interface: reuse `check_schema` in scripts/smoke.sh. Add: GET /monitoring vs contracts/monitoring.schema.json; GET /rooms/<demo_room>/monitoring/history vs contracts/room_monitoring_history.schema.json (SKIP if demo_room is empty); the first message from /ws/live?scenario=tea_skip_teabag_pour_twice&speed=20 vs contracts/live_message.schema.json (pipeline venv Python with a websocket client already in pipeline deps, 5 s timeout; SKIP if none importable). Read-only: no PUTs.
Acceptance:
- `scripts/dev.sh up && scripts/smoke.sh` prints PASS for the three new checks on a fresh stack; then `scripts/dev.sh down`.
- Breaking a field by hand in one schema makes the matching check FAIL (say so in the PR, don't commit it).
- `scripts/ci.sh` passes.

### T289 — Alert view: print-friendly layout
- status: done
- class: standard
- priority: 3
- kind: improvement
- deps: —
- area: web/src/alert/alert.css, web/src/alert/AlertView.tsx, web/src/alert/AlertView.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T14:25Z
- pr: #283
- rating: 5/5 clear

What: nurses bring flagged alerts to care conferences on paper; printing the alert today includes nav, feedback buttons and the dark replay card. Add a `@media print` layout so the page shows resident, errors, "consistent with" patterns, rule-outs and suggested checks in black on white.
Interface: `@media print` rules in alert.css; hide feedback buttons and the replay player via a `no-print` class; wording unchanged. Optional "Print" button calling `window.print()`.
Acceptance:
- AlertView.test.tsx: elements that must not print carry `no-print`; the Print button (if added) calls `window.print`.
- PR notes a Chrome print-preview check of the Mrs. K alert: 1–2 pages, no dark backgrounds.
- `cd web && npm test && npm run build` and `scripts/ci.sh` pass.

### T291 — Web: drift, pattern-library and replay types generated from contracts.py
- status: done
- class: heavy
- priority: 2
- kind: improvement
- deps: —
- area: pipeline/src/routine_watch/contracts.py, web/src/contracts.ts, web/src/resident/api.ts, web/src/patterns/types.ts, web/src/evidence/api.ts, pipeline/tests/test_contracts.py, contracts/
- owner: ian-claude
- claimed: 2026-10-17T14:57Z
- pr: #292
- rating: 5/5 clear — the interface named the three consumers and offered re-export vs replace, which was the only open question

What: Follow-up from T280 (PR #273): the web still mirrors `ResidentDrift`, `PatternLibraryEntry` and the replay payloads by hand, guarded only by field-name tests. Emit them into the generated `web/src/contracts.ts` and make the consumers import them, so a contract change breaks the web build instead of a string-match test.
Interface: `python -m routine_watch.contracts` also writes TS types for the drift/pattern/replay models in `PAYLOADS` (or promotes them to `CONTRACTS`); `web/src/resident/api.ts` drops its hand-written `ResidentDrift`; `web/src/patterns/types.ts` re-exports or is replaced by the generated type; `web/src/evidence/api.ts` reads `SessionReplay`/`NormalReplay` instead of an inline cast. Replace the now-redundant field-name tests in test_contracts.py (drift type, pattern entry, replay cast) with the generated-file-up-to-date check.
Acceptance:
- No hand-written duplicate of these three payload shapes left in web/src; `test_generated_files_are_up_to_date` covers the new TS output.
- No behaviour change: existing web tests pass with only import changes.
- `scripts/ci.sh` passes.

### T292 — Review: generate web resident/handoff/monitoring types from contracts.py
- status: done
- class: standard
- priority: 2
- kind: improvement
- source: reviewer
- deps: T291
- area: pipeline/src/routine_watch/contracts.py, web/src/contracts.ts, web/src/overview/types.ts, web/src/handoff/types.ts, web/src/about/monitoringApi.ts, pipeline/tests/test_contracts.py
- owner: ian-claude-standard
- claimed: 2026-10-17T15:14Z
- pr: #297
- rating: 5/5 clear, required judgment on Handoff's always-optional fields but task scope was well-defined

What: T269/T280 added JSON Schemas for `ResidentSummary`/`Resident`, `Handoff` and room monitoring, but the web still hand-mirrors them (`web/src/overview/types.ts` ResidentSummary/TopPattern/consent, `web/src/handoff/types.ts` Handoff/HandoffResident/PausedRoom, `web/src/about/monitoringApi.ts` MonitoringChange). T291 only covers drift/patterns/replay. Same fix, after T291 lands: emit these models into the generated `web/src/contracts.ts` and have those files re-export the generated types.
Acceptance:
- The listed web files re-export (or are replaced by) generated types; no hand-written copy of these shapes left.
- `test_generated_files_are_up_to_date` covers them; existing web tests pass with import-only changes.
- `scripts/ci.sh` passes.

### T293 — Test: api_state.reset() clears feedback without replacing the store
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_api_state.py
- owner: ian-claude-light-2
- claimed: 2026-10-17T14:31Z
- pr: #282
- rating: 5/5 clear

What: T284 moved the feedback store to `api_state.py`; routers import `_feedback_store` at load time, so `reset()` must clear it in place. Pin that with a direct unit test.
Interface: Read `pipeline/src/routine_watch/api_state.py` and `pipeline/tests/test_api_feedback.py` (for how feedback is recorded). New file `pipeline/tests/test_api_state.py`: keep a reference `store = api_state._feedback_store`, record one feedback answer, call `api_state.reset()`, assert `api_state._feedback_store is store` and the answer is gone; also assert `_flagged_residents()` returns only residents whose raw `status` is "flagged". Test-only.
Acceptance: `cd pipeline && python -m pytest tests/test_api_state.py -q` passes; `scripts/ci.sh` passes.

### T294 — Test: shift handoff works keyboard-only
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/handoff/Handoff.test.tsx
- owner: ian-claude
- claimed: 2026-10-17T15:14Z
- pr: #285
- rating: 4/5 clear, but the task didn't say the handoff screen already had a user-event-free copy test to match, and 'fix CI on PR #285' hid that the failure was tsc in npm run build, not vitest

What: Nurses at a shared workstation may use only the keyboard; prove the handoff screen's "Copy summary" and back button need no mouse.
Interface: Read `web/src/handoff/Handoff.tsx` and its test. With `@testing-library/user-event`: Tab to "Copy summary", press Enter, check the status text ("Copied" with a mocked `navigator.clipboard.writeText`); Tab to the back button, press Enter, check `onBack` was called. Test-only: if a real keyboard bug shows up, describe it in the PR body instead of fixing it.
Acceptance: `cd web && npx vitest run src/handoff/Handoff.test.tsx` passes; `scripts/ci.sh` passes.

### T295 — Test: unit overview opens a resident keyboard-only
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/overview/UnitOverview.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T14:48Z
- pr: #288
- rating: 5/5 clear

What: The first demo step is opening Mrs. K from the unit overview; prove a keyboard user can do it.
Interface: Read `web/src/overview/UnitOverview.tsx` and its test. With `@testing-library/user-event`: Tab until a resident row's control is focused, press Enter, assert the select/open callback fires with that resident's id; also Tab to a status filter and activate it with Space. Test-only: if a real keyboard bug shows up, describe it in the PR body instead of fixing it.
Acceptance: `cd web && npx vitest run src/overview/UnitOverview.test.tsx` passes; `scripts/ci.sh` passes.

### T296 — Scenarios: meds_unclear_not_error and meds_bad_sessions_far_apart
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/meds_unclear_not_error/, tests/scenarios/meds_bad_sessions_far_apart/
- owner: ian-claude-standard
- claimed: 2026-10-17T14:39Z
- pr: #284
- rating: 5/5 clear

What: The meds routine lacks the two "must not flag" scenarios the tea routine has. Mirror `tests/scenarios/tea_unclear_not_error` and `tests/scenarios/tea_bad_sessions_far_apart` for meds (step names from the meds task graph and the existing `meds_*` scenarios), so a low-confidence meds moment is never counted as an error and two isolated bad meds sessions do not raise a flag.
Interface: two new scenario dirs, each `expected.yaml` + `steps.jsonl` (format in `tests/scenarios/README.md`). No pipeline code changes; if a scenario exposes a pipeline bug, say so in the PR and leave the expectation matching SPEC §7.
Acceptance:
- `scripts/e2e.sh tests/scenarios/meds_unclear_not_error` and `scripts/e2e.sh tests/scenarios/meds_bad_sessions_far_apart` PASS; `scripts/e2e.sh` all PASS.
- `scripts/ci.sh` passes.

### T297 — Web: page title names the screen and resident
- status: done
- class: standard
- priority: 3
- kind: improvement
- deps: —
- area: web/src/ui/useDocumentTitle.ts, web/src/ui/useDocumentTitle.test.ts, web/src/App.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T14:45Z
- pr: #286
- rating: 5/5 clear

What: Every tab reads "Routine Watch", so a nurse with several tabs open (or a screen reader announcing the page) can't tell the overview from Mrs. K's alert. Add a small `useDocumentTitle(title)` hook and set it once per route in `App.tsx`: "Unit overview — Routine Watch", "<resident> — Routine Watch", "Alert · <resident> — Routine Watch", "Shift handoff — Routine Watch", etc. (use names already available at the route level; fall back to the screen name).
Interface: `export function useDocumentTitle(title: string): void` in `web/src/ui/useDocumentTitle.ts` (sets `document.title`, restores the previous title on unmount).
Acceptance:
- Vitest test for the hook: sets the title, updates on change, restores on unmount.
- No changes to screen components outside `App.tsx`; `scripts/ci.sh` passes.

### T298 — Test: pattern library works keyboard-only
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/patterns/PatternLibrary.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T14:54Z
- pr: #289
- rating: 5/5 clear

What: Add a test that the pattern library screen is usable with the keyboard alone, like T287 did for alert feedback (see `web/src/alert/FeedbackButtons.test.tsx` for the style).
Interface: read `web/src/patterns/PatternLibrary.tsx`, `web/src/patterns/PatternLibrary.test.tsx`, `web/src/alert/FeedbackButtons.test.tsx`. Only edit `web/src/patterns/PatternLibrary.test.tsx`.
Acceptance:
- Test tabs to the Back button with `@testing-library/user-event` (or `fireEvent.keyDown` if user-event isn't installed), presses Enter, and asserts `onBack` was called once.
- Test asserts every pattern name is an `h3` under the page's heading (heading order intact for screen readers).
- `cd web && npx vitest run src/patterns` and `scripts/ci.sh` pass.

### T299 — Scenarios: meds_single_bad_no_flag and meds_pill_three_times
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/meds_single_bad_no_flag/, tests/scenarios/meds_pill_three_times/
- owner: ian-claude-standard-2
- claimed: 2026-10-17T14:55Z
- pr: #291
- rating: 5/5 clear

What: The meds routine has fewer scenarios than tea. Mirror `tea_single_bad_no_flag` (one bad session among normal ones must not flag) and `tea_teabag_three_times` (a step repeated three times) for the meds routine, so the tester's e2e covers both routines equally.
Interface: new dirs `tests/scenarios/<name>/{steps.jsonl,expected.yaml}` in the same format as `tests/scenarios/tea_single_bad_no_flag/` and `tests/scenarios/meds_pill_twice/`. No pipeline code changes; if a scenario exposes a pipeline bug, keep the expected (correct) behaviour, mark it as known-failing the way tests/scenarios/README.md describes (or note it in the PR) and say so in the PR.
Acceptance:
- Both scenarios run in `scripts/e2e.sh` and pass.
- `meds_single_bad_no_flag` expects no flag; `meds_pill_three_times` expects the repeated-step error type used by `meds_pill_twice`.
- `scripts/ci.sh` and `scripts/e2e.sh` pass.

### T300 — Pattern library: filter by urgency
- status: done
- class: standard
- priority: 3
- kind: feature
- source: proposed
- deps: —
- area: web/src/patterns/PatternLibrary.tsx, web/src/patterns/PatternLibrary.test.tsx, web/src/patterns/urgencyFilter.css
- owner: ian-claude-standard
- claimed: 2026-10-17T15:04Z
- pr: #293
- rating: 5/5 clear

What: Rationale: the library lists every pattern in one long column; a nurse wants to see "what needs checking this shift" first. Add a row of filter buttons (All / Urgent / Check this shift / Check next round / Routine) above the list.
Interface: `PatternLibrary` keeps fetching the same data; filter state is local (`useState`), buttons use `aria-pressed`, labels come from the existing `URGENCY_LABELS`. Put new styles in the new `urgencyFilter.css` (don't touch `PatternLibrary.css`, T240 owns it). Separate screen, not on the demo path.
Acceptance:
- Default is All; picking a level shows only those patterns; a level with no patterns shows an `EmptyState` ("No patterns at this level."), not an error.
- Buttons are reachable and togglable by keyboard; test covers filtering and the empty case.
- `cd web && npx vitest run src/patterns` and `scripts/ci.sh` pass.

### T301 — Review: contract schema + smoke check for GET /residents/{id}/feedback
- status: done
- class: heavy
- priority: 1
- kind: improvement
- source: reviewer
- deps: T291
- area: pipeline/src/routine_watch/contracts.py, contracts/resident_feedback.schema.json, contracts/README.md, web/src/contracts.ts, web/src/resident/types.ts, pipeline/tests/test_api_payload_contracts.py, scripts/smoke.sh
- owner: ian-claude
- claimed: 2026-10-17T16:03Z
- pr: #308
- note: released by ian-claude: run ended without progress; partial work on branch task/T301-wip-1548: start from it (git switch task/T301-wip-1548 && git merge origin/main)
- rating: 4/5 clear; the task didn't mention that pattern_names being a map of strings trips test_contracts.py's privacy sweep (maps had to be numbers or closed enums), which needed a bounded PatternName and a loosened rule

What: T283 added `GET /residents/{id}/feedback` (`api_residents.resident_feedback`) returning `{resident_id, answers[{alert_id, verdict, cause, at}], pattern_weights, pattern_names}`, but there is no model in `contracts.py`/schema in `contracts/`, and `web/src/resident/types.ts` hand-writes `FeedbackAnswer`/`ResidentFeedback` (already missing `resident_id`). Same drift class as T250/T292. Fix: add `ResidentFeedback` (+ `FeedbackAnswer`) pydantic models in `contracts.py`, generate `contracts/resident_feedback.schema.json` and the TS type into `web/src/contracts.ts`, make `types.ts` re-export it, validate the route body in `test_api_payload_contracts.py`, and add a `check_schema` for `GET /residents/mrs-k/feedback` in `scripts/smoke.sh`.
Acceptance:
- Route body validates against the new schema in a pipeline test (empty, and with one answer + cause).
- `web/src/resident/types.ts` has no hand-written copy of these shapes; `test_generated_files_are_up_to_date` covers it.
- `scripts/ci.sh` passes.

### T302 — Test: alert view works keyboard-only
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/alert/AlertView.keyboard.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T15:06Z
- pr: #294
- rating: 5/5 clear

What: Like T295 (`web/src/overview/UnitOverview.test.tsx`, keyboard section), prove a nurse can work Mrs. K's alert with Tab/Enter/Space only.
Interface: read `web/src/alert/AlertView.tsx`, `web/src/alert/AlertView.test.tsx` (for fixtures/mocks) and `web/src/alert/FeedbackButtons.test.tsx`. New file only; use `@testing-library/user-event` `user.tab()` / `user.keyboard('{Enter}')`.
Acceptance:
- Test tabs from the top of the alert to each feedback button and confirms one with the keyboard; the confirmation text appears; no element in the tab order lacks an accessible name.
- If a real keyboard trap is found, don't fix it: note it in the PR body.
- `cd web && npx vitest run src/alert` and `scripts/ci.sh` pass.

### T303 — Test: resident detail works keyboard-only
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/resident/ResidentDetail.keyboard.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T15:18Z
- pr: #295
- rating: 5/5 clear

What: Prove a nurse can move through Mrs. K's resident page (drift card, heat calendar, feedback history, back button) with keyboard only.
Interface: read `web/src/resident/ResidentDetail.tsx` and `web/src/resident/ResidentDetail.test.tsx` (copy its fetch mocks). New file only; `user-event` `user.tab()`.
Acceptance:
- Test reaches the back control and every interactive element on the page by Tab, each has an accessible name, and Enter on back calls the back handler.
- Real keyboard bugs are noted in the PR body, not fixed here.
- `cd web && npx vitest run src/resident` and `scripts/ci.sh` pass.

### T304 — Test: demo reset clears feedback history
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_feedback_reset.py
- owner: ian-claude
- claimed: 2026-10-17T15:24Z
- pr: #298
- rating: 4/5 the acceptance it spells out was already covered by test_feedback_history.py::test_demo_reset_empties_what_nurses_said; the new file's value is the second-demo-run angle (weights/threshold counted from scratch, fresh alert unanswered), which the task only hints at in its 'What'

What: `GET /residents/{id}/feedback` (T283) must be empty again after `/demo/reset`, or a second demo run shows the first run's answers.
Interface: read `pipeline/src/routine_watch/api_state.py` (`reset`), `pipeline/src/routine_watch/feedback.py` (`history`, `reset`), and `pipeline/tests/test_feedback_history.py` for the client fixture. New file only.
Acceptance:
- Test posts a feedback answer for an alert, sees it in `/residents/{id}/feedback`, calls `/demo/reset`, then sees `answers == []` and `pattern_weights == {}`.
- `cd pipeline && python -m pytest tests/test_feedback_reset.py` and `scripts/ci.sh` pass.

### T306 — Test: live screen works keyboard-only
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: web/src/live/LiveScreen.keyboard.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T15:16Z
- pr: #296
- rating: 5/5 clear

What: The demo path runs through the live screen, but only the other screens have keyboard-only tests (T287, T295, T298). Prove a nurse can pick a routine, start the session and open its alert using only Tab/Enter/Space, with the mock live stream.
Interface: new `web/src/live/LiveScreen.keyboard.test.tsx` only; render `LiveScreen` with the existing mock stream (`mockLiveStream.ts`, fake timers) as `LiveScreen.test.tsx` does; drive with `@testing-library/user-event` keyboard/tab only (no `click`).
Acceptance:
- Tab reaches the routine picker, arrow/Enter selects a routine, Tab+Enter starts the session; the task map and session summary render.
- When the mock session ends with a flag, the link/button to the alert is reachable by Tab and activates with Enter.
- Every focused control has an accessible name (`getByRole(..., { name })`).
- No production files changed. `cd web && npm test -- LiveScreen.keyboard` and `scripts/ci.sh` pass.

### T307 — Test: replay player works keyboard-only
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/evidence/ReplayPlayer.keyboard.test.tsx
- owner: max_API_light
- claimed: 2026-10-17T15:44Z
- pr: #310
- note: released by ian-claude-light-2: run ended without progress; partial work on branch task/T307-wip-1531: start from it (git switch task/T307-wip-1531 && git merge origin/main)

What: Prove the evidence replay player (play/pause, scrub, ghost toggle) is usable with Tab/Enter/Space/arrow keys only.
Interface: new test file only; read web/src/evidence/ReplayPlayer.tsx, web/src/evidence/ReplayPlayer.test.tsx and web/src/alert/AlertView.keyboard.test.tsx (copy its style).
Acceptance:
- Test tabs to each control, operates it by keyboard, asserts the visible state changes; no mouse events used.
- If a control is unreachable, mark that case `it.todo` and say so in the PR (don't change ReplayPlayer.tsx).
- `scripts/ci.sh` passes.

### T308 — Test: privacy panel and monitoring toggle work keyboard-only
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/about/PrivacyPanel.keyboard.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T15:46Z
- pr: #302
- rating: 5/5 clear

What: Prove the privacy panel opens/closes and the room monitoring pause/resume toggle works with keyboard only (Tab, Enter/Space, Escape).
Interface: new test file only; read web/src/about/PrivacyPanel.tsx, web/src/about/MonitoringToggle.tsx, their .test.tsx files, and web/src/alert/AlertView.keyboard.test.tsx for style. Mock the API as the existing tests do.
Acceptance:
- Keyboard-only: open panel, reach the toggle, pause then resume a room, focus is not lost after each action.
- No production code changes. `scripts/ci.sh` passes.

### T309 — Monitoring history card: usable at phone width (375 px)
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/MonitoringHistory.tsx, web/src/resident/monitoringHistory.css, web/src/resident/MonitoringHistory.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T15:36Z
- pr: #299
- rating: 5/5 clear

What: The resident page's monitoring audit trail (who paused/resumed, when) should read cleanly at 375 px, matching how T239 made resident detail work on phones.
Interface: CSS media query in monitoringHistory.css; markup changes only if needed for wrapping.
Acceptance:
- At 375 px: no horizontal scroll, rows wrap to two lines (who/action, then time), text >= 14 px.
- Test asserts the wrapping class/structure is present; `scripts/ci.sh` passes.

### T310 — Test: pattern library urgency filter (every option, reset, empty state)
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/patterns/PatternLibrary.filters.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T15:57Z
- pr: #304
- note: rewritten by orchestrator: the library has one filter (urgency); there is no level filter. Test that one axis only.
- rating: 5/5 clear

What: The pattern library has a single urgency filter (T300). Test each option narrows the list to matching patterns, "All" restores the full list, and an urgency with no matching patterns shows the empty state.
Interface: new test file only. Read web/src/patterns/PatternLibrary.tsx and web/src/patterns/PatternLibrary.test.tsx (copy its fetch mock). Do not change PatternLibrary.tsx.
Acceptance:
- Covers: every urgency button, "All" reset, exactly one button has aria-pressed="true", empty state when a mocked list has no pattern of the chosen urgency.
- At least one case operates the filter by keyboard (Tab + Enter/Space).
- `scripts/ci.sh` passes.

### T311 — Test: handoff payload without `paused` / `monitoring_paused` still validates and renders
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_handoff_defaults.py, web/src/handoff/Handoff.defaults.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T15:42Z
- pr: #300
- rating: 5/5 clear

What: T292 (#297) made `Handoff.paused` and `HandoffResident.monitoring_paused` optional with defaults (false / []); lock that in on both sides so an older or trimmed payload never breaks the shift handoff.
Interface: new test files only; read pipeline/src/routine_watch/contracts.py (Handoff, HandoffResident, PausedRoom), web/src/handoff/Handoff.tsx, web/src/handoff/mockHandoff.ts.
Acceptance:
- Pipeline: a Handoff dict without `paused` and residents without `monitoring_paused` validates; defaults are `[]` / `False`; round-trips through `model_dump`.
- Web: Handoff renders a payload missing both fields with no crash, no paused-rooms section, and no "paused" label on any row.
- `scripts/ci.sh` passes.

### T312 — Test: resident detail feedback history after reset shows the empty state
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: web/src/resident/ResidentDetail.reset.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T15:47Z
- pr: #301
- rating: 5/5 clear

What: T304 (#298) proved the API clears feedback on demo reset; add the dashboard side: after a reset the resident detail "What nurses said" card shows "No nurse answers yet" instead of stale answers.
Interface: new test file only; read web/src/resident/ResidentDetail.tsx and its existing tests for how the feedback API is mocked; pipeline/tests/test_feedback_reset.py for the reset behaviour.
Acceptance:
- Mock feedback API returns one answer, then an empty list after a reset; the card updates to the empty-state text on re-fetch/re-mount.
- No raw video or real API calls; fakes only.
- `scripts/ci.sh` passes.

### T313 — Scenarios: meds_two_errors_one_session and meds_pill_substitution
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/meds_two_errors_one_session/, tests/scenarios/meds_pill_substitution/, tests/scenarios/README.md
- owner: ian-claude-standard-2
- claimed: 2026-10-17T15:56Z
- pr: #305
- rating: 5/5 clear

What: Meds still lacks two cases tea has. Add a meds session with two different errors in one session (e.g. skipped water plus pill taken twice), and a substitution case mirroring `tea_substitution` if the meds graph (pipeline/src/routine_watch/tasks/meds.yaml) allows one; otherwise pick another error type tea covers and meds doesn't, and say which in the PR.
Interface: new dirs `tests/scenarios/<name>/{steps.jsonl,expected.yaml}` in the format of `tests/scenarios/meds_pill_twice/` and `tests/scenarios/tea_substitution/`; add both to the README list. No pipeline code changes; if a scenario exposes a pipeline bug, keep the correct expected behaviour, mark it known-failing as tests/scenarios/README.md describes, and say so in the PR.
Acceptance:
- Both scenarios run in `scripts/e2e.sh`; the two-error one expects both error types.
- `scripts/ci.sh` and `scripts/e2e.sh` pass.

### T314 — Scenarios: tea_two_errors_one_session and tea_long_pause_not_error
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/tea_two_errors_one_session/, tests/scenarios/tea_long_pause_not_error/, tests/scenarios/README.md
- owner: ian-claude-standard-2
- claimed: 2026-10-17T16:19Z
- pr: #303
- rating: 5/5 clear task, well-specified acceptance criteria and known README conflict called out in advance
- note: fix CI on PR #303: T313 has merged; on branch task/T314-tea-scenarios, git merge origin/main, then add rows for tea_two_errors_one_session and tea_long_pause_not_error to tests/scenarios/README.md (now in area)

What: Add a tea session with two different errors in one session, and a correct session with one unusually long gap between steps that must produce no task error (long gaps are hesitations from `hesitation.py`, not errors) and no flag.
Interface: new dirs `tests/scenarios/<name>/{steps.jsonl,expected.yaml}` in the format of `tests/scenarios/tea_normal/` and `tests/scenarios/tea_sequence_error/`. Read pipeline/src/routine_watch/hesitation.py. Don't edit tests/scenarios/README.md (T313 owns it); list the two names in the PR body. If the README-lists-every-scenario test then fails, add a deps-free follow-up note in the PR rather than widening scope. No pipeline code changes; bugs found → known-failing + PR note.
Acceptance:
- Both run in `scripts/e2e.sh`; the long-pause one expects zero errors and no flag.
- `scripts/ci.sh` and `scripts/e2e.sh` pass.

### T290 — Alert: errors by time of day (morning / afternoon / evening)
- status: done
- class: heavy
- priority: 3
- kind: feature
- source: proposed
- deps: T284
- area: web/src/alert/TimeOfDayStrip.tsx, web/src/alert/TimeOfDayStrip.test.tsx, web/src/alert/AlertView.tsx, pipeline/src/routine_watch/api_alerts.py, pipeline/tests/test_time_of_day.py, contracts/alert_detail.schema.json, web/src/contracts.ts
- owner: ian-claude
- claimed: 2026-10-17T16:19Z
- pr: #319
- rating: 4/5 clear on the interface and acceptance; the bucket cut at 17:00 differs from pattern_features.EVENING_HOUR (16:00) that the strip is evidence for, and the field had to land on the Alert record (not only AlertDetail) for web/src/contracts.ts to carry it, since AlertDetail is not in WEB_PAYLOADS

What: Rationale: evening-only worsening (SPEC §7.5, already in pipeline/src/routine_watch/patterns.py) appears on the alert as text only; a nurse can't see why. Show a small strip of errors per session bucketed morning/afternoon/evening over the last 14 days, as visible evidence for that pattern.
Interface: optional alert-detail field `errors_by_time_of_day: [{bucket: "morning"|"afternoon"|"evening", sessions: int, errors: int}]` (buckets <12:00, 12:00–17:00, ≥17:00 local); contracts change, so regenerate alert_detail.schema.json and update web/src/contracts.ts and every consumer in this PR. `<TimeOfDayStrip>` under the error list, caption "Errors by time of day, last 14 days"; hidden when the field is absent. No "diagnos" wording.
Acceptance:
- pytest: buckets from mrs-k demo history; summed errors equal the 14-day total; payload validates against the schema.
- Vitest: three buckets with text labels (not colour only); hidden when absent.
- `scripts/ci.sh` and `scripts/e2e.sh` pass.

### T315 — Refactor: shared fake WebSocket helper for live tests
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/live/testWebSocket.ts, web/src/live/LiveSession.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T16:03Z
- pr: #306
- rating: 5/5 clear

What: web/src/live/LiveSession.test.tsx is 625 lines, much of it hand-rolled WebSocket mocking. Move the fake socket and message helpers into `web/src/live/testWebSocket.ts` and use them from LiveSession.test.tsx, with no change to what is tested.
Interface: `testWebSocket.ts` exports a fake socket class/installer and a helper to push server messages; test-only (never imported by app code).
Acceptance:
- Same number of test cases before and after (state both counts in the PR); LiveSession.test.tsx at least 100 lines shorter.
- No app code changes. `scripts/ci.sh` passes.

### T316 — Test: every scenario uses real task-graph step ids
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_scenario_step_ids.py
- owner: ian-claude-standard-2
- claimed: 2026-10-17T16:07Z
- pr: #309
- rating: 5/5 clear

What: A typo in a scenario's step id silently makes it test nothing. Add a pipeline test that loads every `tests/scenarios/*/` scenario and checks each step id it references (steps.jsonl and expected.yaml errors) exists in that scenario's task graph.
Interface: use `routine_watch.replay.load_scenario` and `routine_watch.tasks.load_task`; read pipeline/src/routine_watch/replay.py and tasks/graph.py. Parametrise over scenario folders.
Acceptance:
- Failure message names the scenario and the bad id (show it once locally, note in PR).
- An existing scenario with a bad id is not fixed here: mark that case xfail with the reason and note it in the PR.
- `scripts/ci.sh` passes.

### T318 — Unit overview: sort residents by most recent change
- status: done
- class: standard
- priority: 3
- kind: feature
- source: proposed
- deps: —
- area: web/src/overview/ResidentSort.tsx, web/src/overview/ResidentSort.test.tsx, web/src/overview/UnitOverview.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T16:22Z
- pr: #313
- rating: 5/5 clear

What: Rationale: on a busy unit the nurse wants the newest flags first. Add a small sort control ("Default order" / "Most recent change first") to the unit overview; the default keeps today's order so the demo path is unchanged.
Interface: `ResidentSort.tsx` exports the control and a pure `sortResidents(residents, mode)`; UnitOverview uses it. Read web/src/overview/UnitOverview.tsx for the resident fields (use the latest flag/alert time it already has; if none exists, sort by status urgency and say so in the PR). No API or contract changes.
Acceptance:
- Unit tests for `sortResidents` (both modes, stable ties) and one UI test switching the control by keyboard.
- Default order identical to before (existing UnitOverview tests untouched and passing).
- `scripts/ci.sh` passes.

### T319 — Bug: integration check failing on main
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
- note: orch: scripts/integration.sh passes on main dc9a6ef (OK integration); transient at 08ab990

What: `scripts/integration.sh` (stack up offline → API endpoints → dashboard render → live WebSocket) fails on main @ 08ab990:
  FAIL dashboard did not render (no 'Routine Watch' in DOM)
Interface: reproduce with `scripts/integration.sh`; logs in `.dev/api.log` / `.dev/web.log`. Fix the cause (not the check) unless the check itself is wrong.
Acceptance:
- `scripts/integration.sh` prints OK; `scripts/ci.sh` passes.

### T320 — Test: unit overview works keyboard-only
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/overview/UnitOverview.keyboard.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T16:05Z
- pr: #307
- rating: 5/5 clear

What: Add a keyboard-only test for the unit overview, mirroring `web/src/about/PrivacyPanel.keyboard.test.tsx` and `web/src/alert/AlertView.keyboard.test.tsx`.
Interface: read `web/src/overview/UnitOverview.tsx`, `web/src/overview/UnitOverview.test.tsx` (mocks/fixtures) and one existing `*.keyboard.test.tsx`. Create only `web/src/overview/UnitOverview.keyboard.test.tsx`.
Acceptance:
* Tab reaches every resident card/link in DOM order; Enter on a card opens that resident (assert the callback/route the existing tests use).
* Every focusable element has an accessible name.
* If a real bug is found, don't fix it; note it in the PR body.
* `cd web && npm test -- UnitOverview.keyboard` passes; `scripts/ci.sh` passes.

### T321 — Test: shift handoff works keyboard-only
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/handoff/Handoff.keyboard.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T16:16Z
- pr: #311
- rating: 5/5 clear

What: Add a keyboard-only test for the shift handoff screen, mirroring `web/src/alert/AlertView.keyboard.test.tsx`.
Interface: read `web/src/handoff/Handoff.tsx`, `web/src/handoff/Handoff.test.tsx`, `web/src/handoff/mockHandoff.ts` and one existing `*.keyboard.test.tsx`. Create only `web/src/handoff/Handoff.keyboard.test.tsx`.
Acceptance:
* Tab reaches each resident entry and each open-alert link/button in DOM order; Enter activates it (assert the callback/route the existing tests use).
* Every focusable element has an accessible name.
* If a real bug is found, don't fix it; note it in the PR body.
* `cd web && npm test -- Handoff.keyboard` passes; `scripts/ci.sh` passes.

### T322 — Drift card: usable at phone width (375 px)
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/driftCard.css, web/src/resident/DriftCard.mobile.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T16:23Z
- pr: #312
- rating: 5/5 clear

What: The resident drift card has no small-screen rules; at 375 px it must not scroll sideways and its rows should stack.
Interface: read `web/src/resident/DriftCard.tsx`, `web/src/resident/driftCard.css` and `web/src/resident/resident.css` (copy its `@media (max-width: 480px)` approach). CSS only; no behaviour change. New test `DriftCard.mobile.test.tsx` asserts the card renders with its existing class names (smoke-level, like other `*.mobile.test.tsx` files if any exist).
Acceptance:
- a `@media (max-width: 480px)` block in `driftCard.css`; no fixed widths over 375 px
- `cd web && npm test` and `scripts/ci.sh` pass

### T323 — Live session summary: usable at phone width (375 px)
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/live/sessionSummary.css, web/src/live/liveSession.css
- owner: max_API_light
- claimed: 2026-10-17T16:23Z
- pr: #317

What: `liveScreen.css` and `taskMap.css` already have phone-width rules, but the session summary and live session panels don't; at 375 px they must not scroll sideways and buttons are at least 44 px tall.
Interface: read `web/src/live/SessionSummary.tsx`, `web/src/live/LiveSession.tsx`, the two CSS files, and `web/src/live/liveScreen.css` (copy its `@media (max-width: 480px)` approach). CSS only; no behaviour change.
Acceptance:
- a `@media (max-width: 480px)` block in each of the two CSS files; no fixed widths over 375 px
- existing live tests still pass; `cd web && npm test` and `scripts/ci.sh` pass

### T324 — Shift handoff: "compared with the previous shift" per resident
- status: done
- class: heavy
- priority: 3
- kind: feature
- source: proposed
- deps: —
- area: pipeline/src/routine_watch/handoff.py, pipeline/tests/test_handoff_previous.py, pipeline/src/routine_watch/contracts.py, contracts/handoff.schema.json, contracts/examples/, web/src/handoff/HandoffDelta.tsx, web/src/handoff/HandoffDelta.test.tsx, web/src/handoff/types.ts, web/src/contracts.ts
- owner: ian-claude
- claimed: 2026-10-17T16:46Z
- pr: #324
- rating: 5/5 clear

What: Rationale: a nurse coming on shift wants to know if things are getting better or worse, not just counts. Add each resident's `flags` for the previous window of the same length (`previous_flags`) to `/handoff`, and a small "up / down / same vs previous shift" indicator component.
Interface: `build_handoff(now, hours)` adds `previous_flags: int` per resident (window `[now-2h, now-h)`); update `handoff.schema.json`, contracts.py and generated web types; new `HandoffDelta({flags, previousFlags})` component renders e.g. "2 more than last shift" / "same as last shift" with an accessible text (not colour only). Wiring it into `Handoff.tsx` is a follow-up task (keeps this off the files T203/T247 own). Wording: describes counts only, never a diagnosis.
Acceptance:
- pytest covers previous window bounds (session exactly at `now-h` counts in the current window only) and the demo data
- schema + example validate; smoke/contract tests pass
- `HandoffDelta.test.tsx` covers more/fewer/same/zero
- `scripts/ci.sh` passes

### T325 — Test: monitoring toggle works keyboard-only
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/about/MonitoringToggle.keyboard.test.tsx
- owner: Max_codex_light
- claimed: 2026-10-17T16:23Z
- pr: #315
- rating: 5/5 clear

What: The privacy monitoring switch is a key trust control; prove a nurse can pause and resume it with the keyboard alone.
Interface: read `web/src/about/MonitoringToggle.tsx`, `web/src/about/MonitoringToggle.test.tsx` and `web/src/about/PrivacyPanel.keyboard.test.tsx` (copy its user-event keyboard style). New test file only; no component changes (if a bug is found, mark the case `it.fails` and note it in the PR).
Acceptance:
- Tab reaches the switch; Space and Enter each call `onChange` with the flipped value; `aria-checked` matches `on`
- when paused, the "No camera data is processed while paused." text is shown
- `cd web && npm test` and `scripts/ci.sh` pass

### T326 — Test: unit tests for session_log
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_session_log.py
- owner: ian-claude-light-2
- claimed: 2026-10-17T16:30Z
- pr: #316
- rating: 5/5 clear

What: `pipeline/src/routine_watch/session_log.py` (the in-process log that makes a live session count for the demo) has no direct unit test.
Interface: read `pipeline/src/routine_watch/session_log.py`, `pipeline/tests/conftest.py`, and how `pipeline/tests/test_api_demo_reset.py` builds a Session/TaskError. New test file only; use a fixture that calls `session_log.reset()` before and after each test.
Acceptance:
- covers: record then sessions_for (oldest first), errors_for by session id, unknown resident/session gives an empty list, two residents stay separate, reset() clears everything
- `cd pipeline && python -m pytest tests/test_session_log.py` and `scripts/ci.sh` pass

### T327 — Test: unit tests for pattern_features.extract_features
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_pattern_features.py
- owner: ian-claude-standard-2
- claimed: 2026-10-17T16:26Z
- pr: #314
- rating: 5/5 clear

What: `pipeline/src/routine_watch/pattern_features.py` (378 lines; turns sessions + care records into the features the pattern library ranks on) is only tested indirectly through alerts; direct tests make a regression point at the right file.
Interface: read `pattern_features.py`, `patterns_library.py`, and the `pattern_*` scenarios under `tests/scenarios/` for realistic inputs. New test file only; no source changes (bugs found: `pytest.mark.xfail(strict=True)` + PR note).
Acceptance:
- covers at least: flat history (no drift); slow downward trend; sudden change; evening-only worsening; a sedating care record inside its window appears in the context and an old one doesn't; empty sessions don't crash
- deterministic (fixed `now`, no wall clock)
- `cd pipeline && python -m pytest tests/test_pattern_features.py` and `scripts/ci.sh` pass

### T328 — Test: /ws/live WebSocket routes in api_live.py
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_api_live_ws.py
- owner: Max_codex_light
- claimed: 2026-10-17T16:41Z
- pr: #321
- note: GitHub CI passed; local CI hit known App.test.tsx undici WebSocket environment error despite all tests passing.
- rating: 5/5 clear

What: `api_live.py` has no direct test file. Add WebSocket tests with FastAPI `TestClient` for the live route.
Interface: read `pipeline/src/routine_watch/api_live.py`, `pipeline/src/routine_watch/api_state.py`, `pipeline/src/routine_watch/monitoring.py` and one existing API test in `pipeline/tests/` for the client fixture. Call `api_state.reset()` before each test.
Acceptance:
- covers: a normal run sends at least one message then a session-end message; a paused room gets the "paused" message and no step events; an unknown scenario/room gets a clear error or close (whatever the code does today, asserted)
- offline only, no LIVE_API calls
- `scripts/ci.sh` passes

### T329 — Test: resident routes return 404 for an unknown resident
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_api_residents_404.py
- owner: ian-claude-light-2
- claimed: 2026-10-17T16:42Z
- pr: #323
- rating: 5/5 clear

What: Every `/residents/{id}/...` route in `api_residents.py` should answer an unknown id with 404, not 500 or an empty 200.
Interface: read `pipeline/src/routine_watch/api_residents.py` and `pipeline/src/routine_watch/api.py` (router wiring). Parametrise over every GET route under `/residents/{id}` found in `api_residents.py`.
Acceptance:
- one parametrised pytest; each route with id `nobody` returns 404 with a JSON `detail`
- if a route returns something else, don't change product code: mark that case `xfail(strict=True)` with reason and mention it in the PR body
- `scripts/ci.sh` passes

### T331 — Test: heat calendar cells have accessible names
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/resident/HeatCalendar.a11y.test.tsx
- owner: Max_codex_light
- claimed: 2026-10-17T16:56Z
- pr: #327
- rating: 5/5 clear

What: Colour alone must not carry meaning. Assert each heat calendar cell exposes its date and error count to screen readers.
Interface: read `web/src/resident/HeatCalendar.tsx` and `web/src/resident/HeatCalendar.test.tsx` (fixture). Use Testing Library `getAllByRole`/`getByLabelText`.
Acceptance:
- every rendered day cell has an accessible name containing the date and the count (e.g. "17 Oct: 2 errors"); zero-error days say "no errors"
- if the component lacks this today, mark the test `it.fails` and say so in the PR body (no product change in this task)
- `scripts/ci.sh` passes

### T332 — Replay and ghost replay respect prefers-reduced-motion
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/evidence/ReplayPlayer.tsx, web/src/evidence/GhostReplay.tsx, web/src/evidence/reducedMotion.ts, web/src/evidence/reducedMotion.test.ts, web/src/evidence/ReplayPlayer.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T16:36Z
- pr: #318
- rating: 4/5 task assumed GhostReplay autoplays on its own but it is a static render driven by AlertView's fixed t prop; nothing to gate there

What: Accessibility: when the OS asks for reduced motion, replays must not autoplay; they show the first (or flagged) frame and wait for Play.
Interface: `prefersReducedMotion(): boolean` in `reducedMotion.ts` (matchMedia, safe when matchMedia is missing); ReplayPlayer and GhostReplay read it on mount. Manual Play still animates.
Acceptance:
- tests mock `matchMedia` both ways: autoplay unchanged when false; no autoplay + Play button focused-able when true
- existing ReplayPlayer keyboard tests still pass
- `scripts/ci.sh` passes

### T333 — Resident detail: print-friendly layout
- status: done
- class: standard
- priority: 3
- kind: feature
- source: proposed
- deps: —
- area: web/src/resident/residentPrint.css, web/src/resident/ResidentDetail.tsx, web/src/resident/ResidentDetail.print.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T17:06Z
- pr: #329
- rating: 5/5 clear

What: Rationale: nurses bring a resident's summary to care conferences/family meetings; matches the alert (T289) and handoff (T203) print layouts. Add a Print button and `@media print` styles for resident detail.
Interface: `residentPrint.css` imported by `ResidentDetail.tsx`; a "Print" button calling `window.print()`; print hides nav, buttons and the replay, shows name, consent line, baseline chart, heat calendar, drift card and feedback history on white. Follow the approach of `web/src/alert/alert.css` print rules.
Acceptance:
- test: Print button exists, is keyboard reachable, calls `window.print` (mocked)
- no new wording that diagnoses; screen layout unchanged
- `scripts/ci.sh` passes

### T330 — Heat calendar: usable at phone width (375 px)
- status: done
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
- status: done
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
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/patterns/PatternLibrary.keyboard.test.tsx
- owner: max_API_light
- claimed: 2026-10-17T17:31Z
- pr: #342

What: Add a keyboard-only test for the pattern library, like `web/src/overview/UnitOverview.keyboard.test.tsx` (read it first as the template). Read `web/src/patterns/PatternLibrary.tsx` and `web/src/patterns/PatternLibrary.filters.test.tsx` for how it is rendered with mock data.
Interface: new file only; uses @testing-library/user-event `tab()` and `keyboard('{Enter}')` / `keyboard(' ')`.
Acceptance:
- Tabbing reaches the back button and every urgency filter button (role group "Filter by urgency").
- Pressing Enter or Space on a filter sets its `aria-pressed="true"` and narrows the list; the back button fires `onBack` on Enter.
- `cd web && npx vitest run src/patterns` and `scripts/ci.sh` pass.

### T187 — Test: App shows the live routine picker with tea selected
- status: done
- class: light
- priority: 3
- kind: test
- deps: —
- area: web/src/App.test.tsx
- owner: Max_codex_light
- claimed: 2026-10-17T17:47Z
- pr: #345
- note: released by ian-claude-light-2: run ended without progress; partial work on branch task/T187-wip-1503: start from it (git switch task/T187-wip-1503 && git merge origin/main)
- rating: 5/5 clear

What: T161 swapped `LiveSession` for `LiveScreen` in `App.tsx`; nothing at app level checks the picker is there. Add one test.
Interface: Read only `web/src/App.tsx`, `web/src/App.test.tsx`, `web/src/live/LiveScreen.tsx`. Reuse App.test's existing fetch/websocket mocks.
Acceptance:
* Test: the "Routine to watch" group renders with "Making tea" pressed and "Medication with water" not pressed.
* `scripts/ci.sh` passes.

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
- status: done
- class: light
- priority: 3
- kind: docs
- deps: —
- area: docs/DEMO.md
- owner: Max_codex_light
- claimed: 2026-10-17T18:12Z
- pr: #352
- rating: 5/5 clear

What: Since T152 (PR #177), each handoff row with an alert pending review has an "Open alert" button. The runbook's handoff step doesn't say so.
Interface: Read only `docs/DEMO.md` and `web/src/handoff/Handoff.tsx` (the `Open alert` button). Add 1-3 lines to the handoff step.
Acceptance:
* DEMO.md says the presenter can click "Open alert" on Mrs. K's handoff row to reach her alert.
* Wording says "flags a change for review"; no "diagnose". No other file changed.

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

### T203 — Shift handoff: print-friendly layout
- status: done
- class: light
- priority: 3
- kind: feature
- source: proposed
- deps: —
- area: web/src/handoff/handoff.css, web/src/handoff/Handoff.tsx, web/src/handoff/Handoff.test.tsx
- owner: ian-claude
- claimed: —
- pr: #353
- rating: 4/5 acceptance asked for the .no-print rule inside handoff.css, but T353 already moved it to the shared print.css; the area also left out vite.config.ts's test.css.include, which a ?raw CSS assertion needs
- note: merge conflict with main on PR #353: check out its branch, merge origin/main, fix, push

What: nurses hand off on paper; a "Print" button plus `@media print` rules (hide nav/banner/buttons, black on white, no row breaks across pages) make the handoff usable as a printout.
Interface: read only the three area files. Button calls `window.print()`.
Acceptance:
- "Print handoff" button; test mocks window.print and asserts it's called on click
- handoff.css has an `@media print` block hiding `.no-print` elements and `break-inside: avoid` on rows
- `cd web && npm test -- Handoff` passes; `scripts/ci.sh` passes

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

### T347 — Unit overview: show how many residents each filter holds
- status: done
- class: standard
- priority: 3
- kind: feature
- source: proposed
- deps: —
- area: web/src/overview/UnitOverview.tsx, web/src/overview/overview.css, web/src/overview/UnitOverview.counts.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T18:30Z
- pr: #356
- rating: 5/5 clear

What: Rationale: a charge nurse should see "Flagged (1) · Watch (4) · Paused (0)" at a glance before clicking. Add the count to each filter button label in the unit overview, computed from the loaded residents and paused rooms the component already holds.
Interface: `UnitOverview.tsx` only (+ css). Accessible name stays clear, e.g. "Flagged, 1 resident".
Acceptance:
- counts match the residents each filter would show (incl. Paused) and update after a reset/refresh
- existing overview tests (`UnitOverview*.test.tsx`) still pass unchanged or with label-matcher updates only
- `cd web && npx vitest run src/overview` and `scripts/ci.sh` pass

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

### T247 — Shift handoff: usable at phone width (375 px)
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: T203
- area: web/src/handoff/handoff.css, web/src/handoff/Handoff.tsx, web/src/handoff/Handoff.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T18:46Z
- pr: #359
- rating: 5/5 clear

What: Same treatment T234/T235 gave the overview and live screen: at 375 px the handoff page has no horizontal scroll, rows stack, and buttons are at least 44 px tall.
Interface: read `web/src/handoff/Handoff.tsx`, `web/src/handoff/handoff.css`, and `web/src/overview/overview.css` (copy its `@media (max-width: 480px)` approach). CSS plus at most class-name changes in `Handoff.tsx`; no behaviour change.
Acceptance:
- a `@media (max-width: 480px)` block in `handoff.css`; no fixed widths over 375 px
- existing Handoff tests still pass; `cd web && npm test` and `scripts/ci.sh` pass

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
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/evidence/
- owner: ian-claude-standard
- claimed: 2026-10-17T17:43Z
- pr: #350
- rating: 5/5 clear

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
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/tour/
- owner: max_API_light
- claimed: 2026-10-17T18:04Z
- pr: #358

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

### T356 — Live camera on the dashboard: one command, laptop webcam → /ws/live
- status: done
- class: heavy
- priority: 0
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/api_live.py, pipeline/src/routine_watch/live_camera.py, pipeline/src/routine_watch/capture.py, scripts/camera.sh, pipeline/tests/test_api_live_camera.py, docs/DEMO.md
- owner: ian-claude
- claimed: 2026-10-17T18:41Z
- pr: #366
- note: released by ian-claude: run ended without progress
- rating: 4/5 clear on the interface and the acceptance cases; it didn't say how 'waiting for object detector' should reach the screen (a new live message would be a contract change, so I inferred it from frames with no object boxes), nor that scripts/camera.sh installing the capture extra breaks test_capture's CLI-stderr assertion

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

### T364 — Scenario: meds_late_start_normal (long idle before the first step is not an error)
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/meds_late_start_normal/, pipeline/tests/test_scenarios_meds_late_start.py
- owner: ian-claude-standard-2
- claimed: 2026-10-17T18:12Z
- pr: #351
- rating: 5/5 clear

What: Medication twin of T362: a resident idles a long time before picking up the pill bottle, then completes the routine correctly; must produce zero errors and no flag.
Interface: copy the layout of `tests/scenarios/meds_normal/` (`steps.jsonl`, `expected.yaml`) and the test style of `pipeline/tests/test_scenarios_meds_unclear.py` (`load_scenario`, `replay`). Pipeline code is out of scope: if it fails, set the task blocked with the failing output.
Acceptance:
- new pytest passes; `scripts/e2e.sh` runs the scenario: zero errors, `flag: false`.
- one line added to `tests/scenarios/README.md`.
- `scripts/ci.sh` passes.

### T365 — Test: live session summary has accessible names
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/live/SessionSummary.a11y.test.tsx, web/src/live/SessionSummary.tsx
- owner: Max_codex_light
- claimed: 2026-10-17T18:05Z
- pr: #355
- rating: 4/5 clear except quality is not rendered by this component

What: The end-of-session summary on the live screen must be readable by a screen reader: a heading, and each figure (duration, errors, quality) with a text label, not only an icon or colour.
Interface: read `web/src/live/SessionSummary.tsx` and `web/src/live/SessionSummary.test.tsx`. Add `SessionSummary.a11y.test.tsx` using `getByRole('heading')` and `getByText`/`getByLabelText`. Only if a figure has no accessible name, add an `aria-label` in `SessionSummary.tsx` (no visual change).
Acceptance:
- new test passes; `cd web && npx vitest run src/live/SessionSummary` green.
- `scripts/ci.sh` passes.

### T351 — Review: time-of-day strip and evening pattern use different "evening" cut-offs
- status: done
- class: light
- priority: 2
- kind: bug
- source: reviewer
- deps: T368
- area: pipeline/src/routine_watch/api_alerts.py, pipeline/tests/test_time_of_day.py
- rating: 4/5 clear, prior worker's unpushed-commit note couldn't be reused since the commit wasn't findable in git history
- owner: ian-claude-light-2
- claimed: 2026-10-17T19:11Z
- note: orch: local ci.sh failed only on the known undici WebSocket flake (fixed by T368, now a dep). A fix exists unpushed as c881255 on task/T351-evening-cutoff in Max's worktree; reuse it if available, else redo (tiny). Leave the contracts TimeOfDay docstring alone.
- pr: #368

What: `pattern_features.EVENING_HOUR = 16` decides the evening-only pattern, but `api_alerts.EVENING_START_HOUR = 17` buckets the strip shown as its evidence. A session at 16:xx counts as "evening" for the pattern and "afternoon" on the strip, so an alert "consistent with evening worsening" can show its errors under afternoon. The code comment admits it only holds because no demo session starts 16:00–17:00.
Interface: in `api_alerts.py`, set `EVENING_START_HOUR = pattern_features.EVENING_HOUR` (import it, drop the hard-coded 17) and update the comment. The `TimeOfDay` docstring in `contracts.py`/schemas says "until 17:00": contracts are heavy-only, so don't touch them; note the stale docstring in the PR for a follow-up.
Acceptance:
- new test in `test_time_of_day.py`: a session at 16:30 buckets as `evening`, matching `pattern_features`' late-day rule
- `scripts/ci.sh` passes

### T366 — Test: unit overview error and empty states use the shared ui components
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/overview/UnitOverview.states.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T18:08Z
- pr: #349
- rating: 3/5 task assumed ErrorState is wired into UnitOverview but it isn't; fetchResidents swallows errors and falls back to mock data

What: Guard the overview's failure paths: when the residents API rejects, the screen shows the shared ErrorState with a retry button; when it returns no residents, it shows the shared EmptyState with nurse-readable copy.
Interface: read `web/src/overview/UnitOverview.tsx`, `web/src/overview/api.ts`, `web/src/ui/ErrorState.tsx`, `web/src/ui/EmptyState.tsx` and the mocking style in `web/src/overview/UnitOverview.test.tsx`. Test only; if a state is missing, note it in the PR instead of changing the component.
Acceptance:
- `cd web && npx vitest run src/overview/UnitOverview.states` green.
- `scripts/ci.sh` passes.

### T368 — Test infra: every web test gets a fake WebSocket by default
- status: done
- class: light
- priority: 1
- kind: improvement
- deps: —
- area: web/vite.config.ts, web/src/testSetup.ts, web/src/App.test.tsx
- owner: Max_codex_light
- claimed: 2026-10-17T18:37Z
- pr: #354
- rating: 5/5 clear
- note: merge conflict with main on PR #354: check out its branch, merge origin/main, fix, push

What: Local `scripts/ci.sh` keeps failing with an undici `ERR_INVALID_ARG_TYPE` WebSocket error (blocked T351, LESSONS lines 28 and 42) because some web tests render screens that open a real socket to localhost:8000. Stub it once for the whole suite.
Interface: new `web/src/testSetup.ts` that, in a global `beforeEach`, does `vi.stubGlobal('WebSocket', FakeWebSocket)` using the existing helper in `web/src/live/testWebSocket.ts` (read it first), and registers it as `test.setupFiles: ['src/testSetup.ts']` in `web/vite.config.ts`. Tests that already stub WebSocket keep working (their own stub wins). Drop the now-redundant stub in `App.test.tsx` only if it stays green.
Acceptance:
- with a local `uvicorn` listening on :8000 (or not), `cd web && npx vitest run` exits 0 with no uncaught exception
- `scripts/ci.sh` passes

### T369 — Privacy panel: usable at phone width (375 px)
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/about/PrivacyPanel.tsx, web/src/about/privacyPanel.css, web/src/about/PrivacyPanel.mobile.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T18:30Z
- pr: #357
- rating: 5/5 clear

What: Make the privacy panel readable at 375 px (no horizontal scroll, controls stack, text wraps), like the other phone-width tasks.
Interface: read `web/src/about/PrivacyPanel.tsx` and the pattern in `web/src/resident/DriftCard.mobile.test.tsx` + `web/src/resident/driftCard.css`. Add a `@media (max-width: 480px)` block in a new `privacyPanel.css` imported by the panel; keep existing class names.
Acceptance:
- new `PrivacyPanel.mobile.test.tsx` renders at 375 px and checks the stacked class names exist
- `scripts/ci.sh` passes

### T343 — Live: session_end says when a session was too unclear to score
- status: done
- class: heavy
- priority: 1
- kind: feature
- deps: T342
- area: pipeline/src/routine_watch/contracts.py, contracts/live_message.schema.json, pipeline/src/routine_watch/live.py, pipeline/src/routine_watch/live_camera.py, web/src/contracts.ts, web/src/live/SessionSummary.tsx, web/src/live/SessionSummary.test.tsx, web/src/live/mockLiveStream.ts, pipeline/tests/test_live_quality.py
- owner: ian-claude
- claimed: 2026-10-17T19:21Z
- pr: #373
- rating: 4/5 area list left out web/src/live/useLiveSession.ts and LiveSession.tsx (the field cannot reach SessionSummary without them) and listed web/src/contracts.ts, which the live protocol never generates into

What: SPEC §12 says low-confidence capture (walker, bad lighting) is "unclear", never an error. Today the nurse just sees score 0 with no explanation. Add `quality: "ok" | "unclear"` to `LiveSessionEnd`, send it from both `live.py` and `live_camera.py` (`session_quality(events)`), and have `SessionSummary` show "Capture unclear — this session wasn't scored" with one line on why (lighting, view blocked, walker) instead of the score.
Interface: `LiveSessionEnd.quality: Quality` (required; regenerate `contracts/live_message.schema.json` the way the repo does it and update web types + mock stream in the same PR).
Acceptance:
- pipeline test: unclear session → `session_end.quality == "unclear"`, clean → `"ok"`, for both `live` and `live_camera` paths; schema validates
- web test: SessionSummary renders the unclear copy and no score for `quality: "unclear"`; unchanged for `"ok"`; no diagnosis wording
- `scripts/ci.sh` passes

### T370 — Alert time-of-day strip: usable at phone width (375 px)
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/alert/TimeOfDayStrip.css, web/src/alert/TimeOfDayStrip.mobile.test.tsx
- owner: max_API_light
- claimed: 2026-10-17T18:48Z
- pr: #364

What: The morning/afternoon/evening strip on the alert view must fit 375 px: the three buckets stay readable (stack or shrink), labels never truncate.
Interface: read `web/src/alert/TimeOfDayStrip.tsx` and `TimeOfDayStrip.css`; follow `web/src/resident/DriftCard.mobile.test.tsx`. CSS-only change plus the test; don't change the component's props.
Acceptance:
- new `TimeOfDayStrip.mobile.test.tsx` renders at 375 px and finds all three bucket labels
- `scripts/ci.sh` passes

### T371 — Test: error list and suggested checks have accessible names
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/alert/ErrorList.a11y.test.tsx, web/src/alert/SuggestedChecks.a11y.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T18:58Z
- pr: #363
- rating: 4/5 clear; SuggestedChecks' li items have no ARIA name-from-content for listitem role, so the 'each item's name' acceptance only fully holds for ErrorList

What: Screen-reader check for the two alert evidence lists: each is a labelled list/region and every item's name includes its time and step (errors) or check text (suggested checks).
Interface: read `web/src/alert/ErrorList.tsx`, `SuggestedChecks.tsx` and the style of `web/src/alert/TimeOfDayStrip.a11y.test.tsx`. Tests only; if a name is missing, note it in the PR instead of changing the component.
Acceptance:
- two new test files using `getByRole(..., { name })` queries
- `scripts/ci.sh` passes

### T372 — Test: every error type and pattern is covered by a recorded scenario
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_scenario_coverage.py
- owner: ian-claude-standard-2
- claimed: 2026-10-17T18:46Z
- pr: #361
- note: released by ian-claude-standard: run ended without progress; partial work on branch task/T372-wip-1833: start from it (git switch task/T372-wip-1833 && git merge origin/main)
- rating: 5/5 clear

What: Guard against scenario rot: a pipeline test that loads every `tests/scenarios/*/expected.yaml` and asserts each `ErrorType` (contracts.py) appears in at least one scenario's `errors`, each task (tea, meds) has a `*_normal` and an `*_abandoned` scenario, and each pattern in the pattern library has a `pattern_*` scenario (or is listed in an explicit, commented allow-list).
Interface: read-only use of `routine_watch.contracts.ErrorType`, the pattern library module, and the scenario folder; no new scenarios.
Acceptance:
- `pytest pipeline/tests/test_scenario_coverage.py` passes; removing a scenario's error makes it fail with a message naming the missing type
- `scripts/ci.sh` passes


### T212 — Docs: CODEMAP note that alerts read live session errors
- status: parked
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
- note: PARKED by Ian (cutting low-priority work). Don't revive unless Ian asks.

### T240 — Pattern library: usable at phone width (375 px)
- status: parked
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
- note: PARKED by Ian (cutting low-priority work). Don't revive unless Ian asks.

### T305 — Feedback history card: usable at phone width (375 px)
- status: parked
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
- note: PARKED by Ian (cutting low-priority work). Don't revive unless Ian asks.

### T317 — Test: each screen sets its page title
- status: parked
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
- note: PARKED by Ian (cutting low-priority work). Don't revive unless Ian asks.

### T348 — Docs: CODEMAP note that unclear sessions are never scored
- status: parked
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
- note: PARKED by Ian (cutting low-priority work). Don't revive unless Ian asks.

### T363 — Test: task map legend has accessible names for every step state
- status: parked
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
- note: PARKED by Ian (cutting low-priority work). Don't revive unless Ian asks.

### T373 — Docs: CODEMAP note that web tests share one default WebSocket stub
- status: parked
- class: light
- priority: 3
- kind: docs
- deps: T368
- area: docs/CODEMAP.md
- owner: —
- claimed: —
- pr: —

What: One-line note in the web section of `docs/CODEMAP.md` (notes only, not the generated list) that `web/src/testSetup.ts` stubs WebSocket for every test and tests needing a socket use `web/src/live/testWebSocket.ts`.
Acceptance:
- note added; `scripts/ci.sh` passes
- note: PARKED by Ian (cutting low-priority work). Don't revive unless Ian asks.

### T380 — Dashboard: dark theme for night shift (prefers-color-scheme)
- status: parked
- class: standard
- priority: 3
- kind: feature
- source: proposed
- deps: —
- area: web/src/index.css, web/src/ui/, web/src/theme.test.ts
- owner: —
- claimed: —
- pr: —

What: Nurses check the dashboard on dim night-shift units; follow the OS dark setting so it isn't a bright glare. Rationale: Usefulness + Execution polish, no behaviour change.
Interface: a `@media (prefers-color-scheme: dark)` block in web/src/index.css overriding the existing CSS custom properties only (no per-component colours); ui/ components must use those variables (fix any hard-coded colours in web/src/ui/*.css|tsx). Print stays light (print.css untouched).
Acceptance:
- New web/src/theme.test.ts: every custom property set in `:root` is also set in the dark block; text/background pairs in the dark block meet contrast ≥ 4.5:1 (compute from the hex values).
- Look at overview + alert view with dark emulation in a browser; describe what you checked in the PR.
- `scripts/ci.sh` passes.
- note: PARKED by Ian (cutting low-priority work). Don't revive unless Ian asks.

### T385 — Docs: CODEMAP notes for overview filter counts and remembered prefs
- status: parked
- class: light
- priority: 3
- kind: docs
- deps: —
- area: docs/CODEMAP.md
- owner: —
- claimed: —
- pr: —

What: T347 (filter buttons show counts), T337 (filter/sort remembered for the session) and T318 (sort by most recent change) aren't in CODEMAP's overview notes.
Interface: read only docs/CODEMAP.md, web/src/overview/UnitOverview.tsx and web/src/overview/overviewPrefs.ts. Edit only the notes, not the generated file list.
Acceptance:
- 2–4 lines under the overview section naming `countForFilter`, `overviewPrefs.ts` (sessionStorage) and the sort modes.
- `scripts/ci.sh` passes.
- note: PARKED by Ian (cutting low-priority work). Don't revive unless Ian asks.

### T390 — Docs: CODEMAP note for scripts/preflight.sh
- status: parked
- class: light
- priority: 2
- kind: docs
- deps: —
- area: docs/CODEMAP.md
- owner: —
- claimed: —
- pr: —

What: PR #365 added `scripts/preflight.sh` (the one-command "ready to demo" check) but docs/CODEMAP.md notes don't mention it.
Interface: Read scripts/preflight.sh (header comment) and docs/DEMO.md "Before you start". Add a 1-3 line note in the scripts section of docs/CODEMAP.md notes: what it runs (dev.sh up, smoke.sh, e2e.sh, demo reset check), that it refuses LIVE_API=1, and `--dry-run`. Don't touch the generated file list.
Acceptance:
- docs/CODEMAP.md notes mention scripts/preflight.sh and --dry-run.
- `scripts/ci.sh` passes.
- note: PARKED by Ian (cutting low-priority work). Don't revive unless Ian asks.

### T391 — Preflight: write step logs to a temp dir, not fixed /tmp paths
- status: parked
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: scripts/preflight.sh, tests/test_preflight.py
- owner: —
- claimed: —
- pr: —

What: scripts/preflight.sh writes to fixed `/tmp/preflight-dev-up.log` and `/tmp/preflight-reset.log`, which collide when two people (or a worker and the tester) run it on one host.
Interface: Read only scripts/preflight.sh and tests/test_preflight.py. Use `LOG_DIR=$(mktemp -d)` (respect $TMPDIR) for both logs, print the log path in the ✗ fix hint, keep all ✓/✗ output and exit codes the same.
Acceptance:
- `grep -n '/tmp/preflight' scripts/preflight.sh` finds nothing.
- tests/test_preflight.py still passes (`uv run --with pytest --no-project python -m pytest -q tests/test_preflight.py`); `scripts/ci.sh` passes.
- note: PARKED by Ian (cutting low-priority work). Don't revive unless Ian asks.

### T393 — Landing page: usable at phone width (375 px)
- status: parked
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/landing/landing.css, web/src/landing/Landing.test.tsx
- owner: —
- claimed: —
- pr: —

What: Judges may open the public landing page (T378) on a phone. Make the flow strip, pattern cards and CTA stack in one column at ≤ 480 px with no horizontal scroll.
Interface: read only web/src/landing/Landing.tsx, web/src/landing/landing.css, web/src/index.css (tokens). CSS-only change in landing.css (a `@media (max-width: 480px)` block); don't change copy or Landing.tsx.
Acceptance:
- grids in landing.css collapse to one column at ≤ 480 px; no fixed widths wider than 375 px
- Landing.test.tsx gains a test that the stylesheet contains the phone media query for the flow/pattern grids (Vitest can't lay out; assert on the CSS text like other phone-width tests)
- `cd web && npm test` and `scripts/ci.sh` pass
- note: PARKED by Ian (cutting low-priority work). Don't revive unless Ian asks.

### T395 — Docs: CODEMAP note for live camera source and scripts/camera.sh
- status: parked
- class: light
- priority: 3
- kind: docs
- deps: —
- area: docs/CODEMAP.md
- owner: —
- claimed: —
- pr: —

What: Check docs/CODEMAP.md notes describe T356: `/ws/live?source=camera` (`api_live._session`), `capture.camera_frames`/`frame_stream`/`recorded`, `live_camera.py`, `scripts/camera.sh`, and `CAMERA_RECORD`. Add or fix one short note per item that is missing or wrong.
Interface: read pipeline/src/routine_watch/api_live.py, capture.py, live_camera.py, scripts/camera.sh headers only. Edit only notes, not the generated file list.
Acceptance:
- notes match the code; no file-list edits
- `scripts/ci.sh` passes
- note: PARKED by Ian (cutting low-priority work). Don't revive unless Ian asks.

### T396 — Flag outcomes: unit-wide confirmed vs false-alarm counts per pattern
- status: parked
- class: heavy
- priority: 2
- kind: feature
- source: proposed
- deps: —
- area: pipeline/src/routine_watch/feedback.py, pipeline/src/routine_watch/api_alerts.py, pipeline/src/routine_watch/contracts.py, contracts/, pipeline/tests/test_feedback_summary.py, web/src/contracts.ts, web/src/outcomes/, web/src/App.tsx, docs/CODEMAP.md
- owner: —
- claimed: —
- pr: —

What: Rationale: judges (Execution, Use of AI) and nurses want to see how often flags turned out to be real. Add a small read-only "Flag outcomes" screen listing, per pattern, how many flagged alerts nurses marked confirmed vs false alarm and the most common "what was it?" answer, from the existing FeedbackStore.
Interface: `FeedbackStore.summary()`; `GET /feedback/summary` returning `{patterns: [{pattern_id, confirmed, false_alarm, unanswered, top_cause}]}`; Pydantic model + JSON Schema in contracts/ + type in web/src/contracts.ts; `web/src/outcomes/OutcomesScreen.tsx` reached from a link in the app header (follow App.tsx's existing screen switch, no router). Wording: "flags reviewed", never diagnosis accuracy.
Acceptance:
- Pipeline test covers empty store, mixed answers, and reset via api_state.reset().
- Web test renders counts and the empty state ("No flags reviewed yet") with shared ui components.
- `scripts/ci.sh` passes.
- note: PARKED by Ian (cutting low-priority work). Don't revive unless Ian asks.

### T398 — Test: landing page works keyboard-only
- status: parked
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/landing/Landing.keyboard.test.tsx
- owner: —
- claimed: —
- pr: —

What: the public landing page (T378) has no keyboard test; judges may tab through it.
Interface: new file `web/src/landing/Landing.keyboard.test.tsx` only. Read `web/src/landing/Landing.tsx` and copy the style of `web/src/alert/AlertView.keyboard.test.tsx` (uses `@testing-library/user-event` `tab()`).
Acceptance:
- Render `<Landing />`; tabbing reaches, in order, the "Open the dashboard" link (href `/`), the "#how-it-works" link, the `/?tour=1` tour link, and the GitHub source link; each is focusable and has an accessible name.
- Every `h2` section has an `id` so the in-page link target exists (assert `#how-it-works` resolves to an element).
- `cd web && npx vitest run src/landing` passes; `scripts/ci.sh` passes.
- note: PARKED by Ian (cutting low-priority work). Don't revive unless Ian asks.

### T400 — Docs: DEMO.md points judges at the landing page
- status: parked
- class: light
- priority: 3
- kind: docs
- deps: —
- area: docs/DEMO.md
- owner: —
- claimed: —
- pr: —

What: DEMO.md never mentions the public landing page at `/landing.html` (T378), which is the judges' first impression and links into the dashboard and guided tour.
Interface: in `docs/DEMO.md`, add one line to the setup/"before you start" section: open `http://localhost:5173/landing.html` (or the deployed URL) on a second tab to hand to judges; its "Open the dashboard" button goes to `/`, the tour link to `/?tour=1`. Read only `docs/DEMO.md` and `web/src/landing/Landing.tsx`. No other file.
Acceptance:
- One short addition, matching the existing bullet style; no change to the run order.
- `scripts/ci.sh` passes.
- note: PARKED by Ian (cutting low-priority work). Don't revive unless Ian asks.

### T374 — Test infra: load every web stylesheet in Vitest so tasks stop editing vite.config.ts
- status: done
- class: light
- priority: 1
- kind: improvement
- deps: T368
- area: web/vite.config.ts
- owner: ian-claude-heavy-2
- claimed: 2026-10-17T19:22Z
- pr: #372
- rating: 5/5 clear - the interface named the exact pattern; only wrinkle worth noting is that the pattern must stay unanchored because ?raw ids carry a query suffix

What: every phone-width / print task appends a folder to `test.css.include` in `web/vite.config.ts`, so sibling PRs conflict on that one line (T203's PR #353 is conflicting now; LESSONS.md line 19). Replace the per-folder list with one pattern that matches all `src/**/*.css`.
Interface: read `web/vite.config.ts` only. Set `css: { include: [/src\/.*\.css/] }` (or equivalent) and shorten the comment to say why: `?raw` CSS assertions need it and no task should have to edit this line again.
Acceptance:
- `cd web && npm test` passes with no other file changed (if a test becomes slower or breaks because its CSS is now loaded, say so in the PR rather than widening scope)
- `scripts/ci.sh` passes

### T375 — Unit overview: say when it is showing demo data because the API is unreachable
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/overview/api.ts, web/src/overview/UnitOverview.tsx, web/src/overview/UnitOverview.states.test.tsx, web/src/overview/overview.css
- owner: ian-claude-standard
- claimed: 2026-10-17T18:48Z
- pr: #362
- rating: 5/5 clear

What: `fetchResidents()` silently falls back to `mockResidents` when `/residents` fails (T366 rating), so a nurse or judge can't tell live data from demo data. Keep the fallback (demo robustness) but surface it as a one-line notice above the list.
Interface: `fetchResidents()` returns `{ residents: ResidentSummary[], source: 'api' | 'demo' }` via a new `fetchResidentsWithSource()` (keep `fetchResidents()` returning the array so `web/src/App.tsx` is untouched). UnitOverview renders `<p role="status" class="overview__demo-notice">Showing demo residents: the Routine Watch service isn't reachable.</p>` when `source === 'demo'`, nothing otherwise.
Acceptance:
- tests in `UnitOverview.states.test.tsx`: API rejects → notice shown and mock residents listed; API non-OK → notice shown; API OK → no notice
- `cd web && npm test` and `scripts/ci.sh` pass

### T376 — Review: live "Open alert" CTA uses ui/Button and sits outside the status live region
- status: done
- class: light
- priority: 1
- kind: improvement
- source: reviewer
- deps: —
- area: web/src/live/LiveSession.tsx, web/src/live/liveSession.css, web/src/live/LiveSession.test.tsx
- owner: ian-claude-heavy-2
- claimed: 2026-10-17T18:43Z
- pr: #360
- rating: 5/5 clear - the interface named the exact component, class name and the live-region problem; only unstated detail was that LiveSession.test.tsx asserts summary.nextElementSibling has role=status, so the banner-row wrapper has to be conditional on the CTA

What: the demo's key click (SPEC §10, DEMO.md "Alert" beat) is a raw unstyled `<button>` nested inside `<p role="status">` in `LiveSession.tsx` (~line 216). It ignores `web/src/ui/Button.tsx` and, inside a live region, screen readers re-announce the button text with the banner.
Interface: keep the `<p role="status">` for the banner text only; render `<Button onClick={() => onOpenAlert(ended.alert_id)}>Open alert</Button>` (from `../ui/Button.tsx`) as a sibling right after it, wrapped in a `div.live-session__banner-row` if layout needs it (CSS in `liveSession.css`, use existing CSS vars, no hex colours).
Acceptance:
- test: flagged session_end with alert_id → `getByRole('button', {name: 'Open alert'})` exists and is not inside `getByRole('status')`; clicking calls `onOpenAlert` with the id
- `cd web && npm test` and `scripts/ci.sh` pass

### T377 — Review: DEMO.md shift-handoff step is after "Close" (out of run order)
- status: done
- class: light
- priority: 2
- kind: docs
- source: reviewer
- deps: —
- area: docs/DEMO.md
- owner: ian-claude-light-2
- claimed: 2026-10-17T19:29Z
- pr: #371
- rating: 5/5 clear

What: the "Shift handoff" bullet added in the last merge sits after the "Close" bullet, separated by a blank line, so the presenter reads it after closing.
Interface: move it into the run list between "Why / not just delirium" and "Close", reword to match the other bullets (bold beat name, what to click, what appears). No other file.
Acceptance:
- `docs/DEMO.md` beat list is one contiguous list ending with "Close"
- `scripts/ci.sh` passes

### T378 — Landing page (public, judges' first impression)
- status: done
- class: heavy
- priority: 1
- kind: feature
- deps: —
- area: web/landing.html, web/src/landing/, web/vite.config.ts, docs/CODEMAP.md
- owner: ian-claude-heavy-2
- claimed: 2026-10-17T19:02Z
- pr: #367
- rating: 4/5 clear; the one ambiguity was the hero's 'Watch the demo' anchor (no video exists, so it points at the How it works section, which links the guided tour) and the section name 'consistent with, not a diagnosis' colliding with the no-'diagnos' copy rule

What: A one-page public site for the demo URL (and the GoDaddy domain later): what Routine Watch is, why it matters, how it works, and a button into the live dashboard. Separate from the nurse dashboard so it can't break the demo path.
Interface:
- Second Vite entry `web/landing.html` + `web/src/landing/` (React, plain CSS using the design tokens from `web/src/index.css` / `web/src/ui/`). Build output `dist/landing.html`; dashboard stays at `/`. Add the entry to `vite.config.ts` `build.rollupOptions.input`.
- Sections, in order: hero (one-liner from SPEC §1 + "Open the dashboard" button to `/` and "Watch the demo" anchor) → problem (SPEC §2, 3 short points) → how it works (camera → skeleton only → task graph → personal baseline → patterns → nurse, as a simple visual strip; reuse `docs/routine-watch-flow.png` ideas, not the image) → "consistent with, not a diagnosis" pattern examples (sudden change, slow drift, evening worsening) → privacy (no video stored, skeletons only, per-room off switch) → built with (Gemini, Tiger Data, Vultr, Claude, Roboflow; text only, no logos needed) → footer (Hack the Valley 11, GitHub link placeholder).
- Copy: plain, confident, no hype words, never "diagnose". Under ~350 words total.
- Responsive (mobile first), accessible (landmarks, headings in order, contrast ≥ 4.5:1, keyboard), loads fast (no new runtime deps, no web fonts beyond what the dashboard uses).
Acceptance:
- `cd web && npm run build` produces `dist/landing.html`; Vitest test renders the landing page and checks every section heading and the dashboard link.
- `wording.test.ts`-style check: no "diagnos" in landing copy.
- Look at it (dev server `/landing.html`, desktop + 390 px wide); describe what you checked in the PR.

### T355 — Shift handoff: say when a room's capture was too unclear to score this shift
- status: done
- class: heavy
- priority: 2
- kind: feature
- source: proposed
- deps: T343
- area: pipeline/src/routine_watch/contracts.py, contracts/, pipeline/src/routine_watch/live.py, pipeline/src/routine_watch/handoff.py, pipeline/src/routine_watch/store.py, pipeline/tests/test_handoff_unclear.py, web/src/contracts.ts, web/src/handoff/HandoffRow.tsx, web/src/handoff/mockHandoff.ts
- owner: ian-claude
- claimed: 2026-10-17T19:50Z
- pr: #381
- rating: 4/5 clear on the interface and acceptance; the area named store.py, whose get_store() returns a fresh MemoryStore per call so it cannot hold process state, and web/src/handoff/HandoffRow.tsx, which does not exist

What: Rationale: since T342 unclear sessions are dropped from history, so repeated bad lighting or a blocked camera goes unnoticed; the incoming nurse should see "2 sessions too unclear to score — check the camera view" for that room. Keep a per-room count of unclear sessions (timestamps only, never frames, never in the resident's scored history) and surface it as `HandoffResident.unclear_sessions: int` for the window.
Interface: `HandoffResident.unclear_sessions: int` (default 0; regenerate schema and web types the repo's way, update every consumer and mock in the same PR); the handoff row shows the line only when > 0. Wording is about the capture, never the resident.
Acceptance:
- pytest: two unclear live sessions in the window → `unclear_sessions == 2`, resident's history and flag unchanged; outside the window → 0
- web test: row shows the camera line when > 0 and nothing when 0
- `scripts/ci.sh` passes

### T367 — Bug: integration check failing on main
- status: done
- class: standard
- priority: 0
- kind: bug
- deps: —
- area: scripts/integration.sh, scripts/dev.sh
- owner: ian-claude-heavy-3
- claimed: 2026-10-17T19:59Z
- pr: #384
- source: integration
- note: area narrowed (was web/src/, which overlapped claims and kept this P0 from being handed out). T388 (#370) stopped integration.sh sharing/killing a running dev stack, a likely cause; first re-run scripts/integration.sh on main twice and, if both print OK, mark done with a note. If it is Vite cold-start timing, make integration.sh wait for Vite readiness. If the render itself is broken, note the file and set blocked so a web task can be filed.
- rating: 4/5 the note's two hypotheses (dev-stack sharing, Vite cold start) were both wrong - the cause was the check's own 'echo | grep -q' + pipefail SIGPIPE race, so 'first re-run it twice and mark done if both print OK' would have closed a real, ~50%-flaky bug

What: `scripts/integration.sh` (stack up offline → API endpoints → dashboard render → live WebSocket) fails on main @ c332a28:
  FAIL dashboard did not render (no 'Routine Watch' in DOM)
Interface: reproduce with `scripts/integration.sh`; logs in `.dev/api.log` / `.dev/web.log`. Fix the cause (not the check) unless the check itself is wrong.
Acceptance:
- `scripts/integration.sh` prints OK; `scripts/ci.sh` passes.

### T379 — Test: shift handoff Print button works keyboard-only
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/handoff/Handoff.keyboard.test.tsx
- owner: max_API_light
- claimed: 2026-10-17T19:36Z
- pr: #377

What: T203 added a "Print handoff" button; the keyboard-only test (T294/T321) predates it. Cover it so a nurse without a mouse can print.
Interface: read only web/src/handoff/Handoff.keyboard.test.tsx, web/src/handoff/Handoff.tsx and the 'Print handoff' test near line 171 of web/src/handoff/Handoff.test.tsx (stub `window.print` the same way). No production code changes.
Acceptance:
- Tabbing from "Copy summary" reaches "Print handoff"; Enter and Space each call `window.print` once.
- `cd web && npx vitest run src/handoff/Handoff.keyboard.test.tsx` passes; `scripts/ci.sh` passes.

### T381 — scripts/preflight.sh: one command that says "ready to demo"
- status: done
- class: standard
- priority: 1
- kind: improvement
- deps: —
- area: scripts/preflight.sh, docs/DEMO.md, tests/test_preflight.py
- owner: ian-claude-standard-2
- claimed: 2026-10-17T19:05Z
- pr: #365
- rating: 5/5 clear

What: Before judging, one command should confirm the demo path works offline (SPEC §10 fallback, §13 risks) instead of someone remembering five scripts.
Interface: `scripts/preflight.sh` runs in order and prints a ✓/✗ checklist: LIVE_API unset and OFFLINE_MODE=true; `scripts/dev.sh up` (if not already up); `scripts/smoke.sh`; `scripts/e2e.sh` (scenario count); POST /demo/reset then GET /residents shows the demo resident on watch. Exits non-zero on the first ✗ with the fix hint. Never calls paid APIs.
Acceptance:
- tests/test_preflight.py runs `scripts/preflight.sh --dry-run` and checks it lists every step and refuses to run when `LIVE_API=1`.
- docs/DEMO.md "Before you start" says to run it.
- Run it for real against `scripts/dev.sh up`, paste the checklist in the PR, then `scripts/dev.sh down`. `scripts/ci.sh` passes.

### T382 — Refactor: move scenario loading out of replay.py into scenario.py
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: pipeline/src/routine_watch/replay.py, pipeline/src/routine_watch/scenario.py, docs/CODEMAP.md
- owner: ian-claude-standard
- claimed: 2026-10-17T19:06Z
- pr: #369
- rating: 5/5 clear

What: replay.py (500 lines) mixes the scenario file format (pydantic models + JSONL loading) with running/comparing a replay. Split them so each is readable on its own; no behaviour change.
Interface: new `routine_watch/scenario.py` with `ReplayError`, `_Strict`, `ExpectedError`, `HistorySession`, `Expected`, `Scenario`, `load_scenario`, `_load_jsonl`, `scenario_dirs`, `SCENARIOS_DIR`. replay.py re-exports them (`from .scenario import ...`) so every existing import and test keeps working.
Acceptance:
- No test file changes needed; `cd pipeline && uv run pytest -q` and `scripts/e2e.sh` pass unchanged.
- replay.py under ~330 lines; CODEMAP note for scenario.py. `scripts/ci.sh` passes.

### T383 — Care-record context timeline: usable at phone width (375 px)
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/ContextTimeline.tsx, web/src/resident/contextTimeline.css, web/src/resident/ContextTimeline.mobile.test.tsx
- owner: Max_codex_light
- claimed: 2026-10-17T19:36Z
- pr: #379
- rating: 5/5 clear

What: Same treatment as the other phone-width tasks (e.g. T345 session list): the care-record timeline on resident detail must not overflow at 375 px.
Interface: read only web/src/resident/ContextTimeline.tsx, web/src/resident/SessionList.mobile.test.tsx and web/src/resident/sessionList.css (copy their approach). Add a `contextTimeline.css` imported by the component; wrap long labels, stack date above text under 480 px.
Acceptance:
- New ContextTimeline.mobile.test.tsx in the style of SessionList.mobile.test.tsx.
- `cd web && npx vitest run src/resident/ContextTimeline` passes; `scripts/ci.sh` passes.


### T402 — Redesign 2/6: chart kit in Fey style + restyle existing charts
- status: parked
- class: heavy
- priority: 1
- kind: improvement
- deps: T401
- area: web/src/ui/charts/, web/src/overview/Sparkline.tsx, web/src/resident/BaselineChart.tsx, web/src/resident/HeatCalendar.tsx, web/src/resident/*Drift*.tsx, web/src/resident/*.test.tsx
- owner: —
- claimed: —
- pr: —

What: The graphs are what Ian likes most in Fey. Build a small, dependency-free SVG chart kit following `docs/DESIGN.md` and move our charts onto it. Study the chart references in T401 with the mobbin MCP first.
Interface (`web/src/ui/charts/`):
- `LineChart`: thin (1.25–1.5px) primary line, no heavy area fill (at most a very faint gradient), hairline or dashed gridlines only at a few ticks, tiny muted axis labels, **end-of-line value tag** (pill at the right edge with the latest value), optional **personal-baseline band** (mean ± threshold as a soft band) and optional dotted comparison series, hover/focus crosshair with a small tooltip, keyboard focus over points.
- `BarChart`: slim rounded bars, paired series (e.g. this week vs baseline) with the second series muted/outlined, callout pill above a highlighted bar ("2.4× baseline").
- `MicroBars`: row of thin vertical ticks (like Fey's sector rows) for a resident's last 14 days, coloured by status.
- `RangeSelector`: uses `SegmentedControl` (7D 14D 30D).
- Restyle: `Sparkline` → MicroBars or mini LineChart; `BaselineChart` → LineChart with baseline band + end tag + range selector; HeatCalendar → muted Fey palette (tinted cells, hairline gaps); drift card → LineChart with dotted trend.
Acceptance:
- Every chart has an accessible name and a text alternative (summary line or table) for screen readers.
- Unit tests for scales/ticks and that the end tag shows the latest value; existing chart tests still pass (update selectors, not behaviour).
- Before/after screenshots of Mrs. K's detail in the PR.
- note: PARKED: split into T417, T418, T419, T420, T421, T422 so the chart kit runs in parallel (Ian).

### T384 — Ghost replay: aria-label says what is being compared
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/evidence/GhostReplay.tsx, web/src/evidence/GhostReplay.test.tsx
- owner: ian-claude-heavy-2
- claimed: 2026-10-17T19:41Z
- pr: #375
- rating: 5/5 clear

What: The ghost replay SVG's label is the fixed "Today and usual skeleton replay"; a screen-reader user gets no information. Describe the comparison in words.
Interface: read only web/src/evidence/GhostReplay.tsx and its test. Build the label from the props already passed (e.g. "Today's routine drawn over the usual routine, frame 12 of 40"); if a prop you'd need doesn't exist, keep to what's there. No new props from other files.
Acceptance:
- Test asserts the label changes with the frame and never contains "diagnos".
- `cd web && npx vitest run src/evidence/GhostReplay` passes; `scripts/ci.sh` passes.

### T386 — Test: demo banner reset works keyboard-only
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/ui/DemoBanner.keyboard.test.tsx
- owner: max_API_light
- claimed: 2026-10-17T19:56Z
- pr: #382

What: The presenter resets the demo from the banner; it must work without a mouse like every other screen's keyboard test.
Interface: read only web/src/ui/DemoBanner.tsx, web/src/ui/DemoBanner.test.tsx (reuse its fetch stub) and web/src/about/PrivacyPanel.keyboard.test.tsx (style). No production code changes.
Acceptance:
- Tab reaches the reset button; Enter and Space each trigger one reset request; focus stays visible on the button afterwards.
- `cd web && npx vitest run src/ui/DemoBanner` passes; `scripts/ci.sh` passes.

### T387 — Test: guided tour works keyboard-only
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/tour/Tour.keyboard.test.tsx
- owner: ian-claude-heavy-2
- claimed: 2026-10-17T20:01Z
- pr: #380
- rating: 5/5 clear

What: The `?tour=1` presenter card (T360 just made it phone-width) has no keyboard test.
Interface: read only web/src/tour/Tour.tsx, web/src/tour/steps.ts, web/src/tour/Tour.test.tsx and web/src/about/PrivacyPanel.keyboard.test.tsx (style). No production code changes.
Acceptance:
- Tab reaches Next/Back/Close in a sensible order; Enter advances a step; the last step's control closes or finishes the tour as the component defines.
- `cd web && npx vitest run src/tour` passes; `scripts/ci.sh` passes.

### T388 — Bug: integration.sh can't run next to a dev stack and kills it
- status: done
- class: standard
- priority: 1
- kind: bug
- deps: —
- area: scripts/integration.sh, scripts/dev.sh
- owner: ian-claude-standard-2
- claimed: 2026-10-17T19:19Z
- pr: #370
- source: tester
- rating: 5/5 clear

What: `scripts/integration.sh` says it "uses its own ports (API 8100, dashboard 5273) so it can run next to a dev stack", but `dev.sh` keys "already running" off the shared `.dev/api.pid` / `.dev/web.pid`, so with `scripts/dev.sh up` already running it skips starting anything, then times out on :8100; its EXIT trap then runs `scripts/dev.sh down`, which stops the developer's :8000/:5173 stack too.
Repro (main @ 8c81e18): `scripts/dev.sh up && scripts/integration.sh` → `FAIL dev.sh up: API already running (pid N) dashboard already running (pid M) timed out waiting for API at http://localhost:8100/health`; afterwards `curl localhost:5173` refuses.
Interface: make dev.sh's pid/log files port-scoped (or let integration.sh set a separate `DEV_DIR`), so integration's up/down only touch its own processes.
Acceptance:
- With `scripts/dev.sh up` running, `scripts/integration.sh` prints OK and the :8000/:5173 stack still answers afterwards.
- `scripts/integration.sh` alone still prints OK; `scripts/dev.sh down` still stops the default stack; `scripts/ci.sh` passes.

### T389 — Review: PrivacyPanel phone-width test checks nothing about phone layout
- status: done
- class: light
- priority: 2
- kind: test
- source: reviewer
- deps: —
- area: web/src/about/PrivacyPanel.mobile.test.tsx
- owner: max_API_standard
- claimed: 2026-10-17T20:02Z
- pr: #385
- rating: 5/5 clear

What: the T369 test sets `window.innerWidth = 375` and only asserts class names exist; jsdom ignores innerWidth and `privacyPanel.css` is stubbed in Vitest, so deleting the whole `@media (max-width: 480px)` block still passes.
Interface: read `src/about/privacyPanel.css` with `vi.importActual('node:fs').readFileSync` (same as `web/src/tour/Tour.test.tsx`) and assert the `@media (max-width: 480px)` block contains `.privacy-panel__list` with `word-break: break-word`; drop the innerWidth line (and don't leave it mutated for other tests). Only this test file.
Acceptance:
- Removing the @media block from `privacyPanel.css` makes the test fail
- `cd web && npm test` and `scripts/ci.sh` pass

### T392 — Test: scripts/camera.sh argument handling (no camera needed)
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_camera_script.py
- owner: max_API_standard
- claimed: 2026-10-17T19:39Z
- pr: #376
- note: released by ian-claude-standard: run ended without progress; partial work on branch task/T392-wip-1934: start from it (git switch task/T392-wip-1934 && git merge origin/main)
- rating: 5/5 clear

What: scripts/camera.sh (T356) has no tests. Cover the parts that run before any install or camera: `--help` prints the header usage, unknown args and a non-numeric `--camera` exit 2 with a message, missing values for `--camera`/`--record` fail.
Interface: new pytest file running `bash scripts/camera.sh ...` via subprocess with a short timeout; must never reach the pip install / camera / dev.sh steps (only invoke paths that exit during argument parsing).
Acceptance:
- tests for --help (exit 0, usage text), unknown arg (exit 2), `--camera abc` (exit 2), `--camera` with no value (non-zero)
- no network, no camera, no stack started
- `scripts/ci.sh` passes

### T394 — Live: tell the nurse when the camera could not be opened (close code 4503)
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/live/useLiveSession.ts, web/src/live/useLiveSession.test.ts, web/src/live/LiveSession.tsx, web/src/live/LiveSession.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T19:50Z
- pr: #378
- note: partial work pushed on branch task/T394-camera-unavailable (worker retired mid-task): start from it: git switch task/T394-camera-unavailable && git merge origin/main
- rating: 5/5 clear

What: `/ws/live?source=camera` closes with 4503 (`live_camera.CAMERA_UNAVAILABLE`) when no camera can be read (T356). Make sure the Live screen shows a plain, specific message for that code ("No camera could be opened on this machine — run scripts/camera.sh, or watch a recorded session") with a button back to the recorded scenario, distinct from "API unreachable" and 4404.
Interface: map close code 4503 to its own state in useLiveSession; render via the shared ui ErrorState/Button. If this already exists, tighten tests only.
Acceptance:
- unit test with the fake WebSocket closing 4503 shows the camera message and a working "watch a recorded session" button
- 4404 and network-error messages unchanged (existing tests pass)
- `cd web && npm test` and `scripts/ci.sh` pass

### T397 — Test: live WebSocket path and offline replay flag the same scenario the same way
- status: done
- class: heavy
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_live_replay_parity.py
- owner: ian-claude-heavy-3
- claimed: 2026-10-17T19:38Z
- pr: #374
- rating: 4/5 the flag half of the ask compares two different questions (session_end's flag is the resident's over their own history; replay.run's is the recording's over expected.yaml's, and 17 of 38 scenarios differ by design, T236), so it is restated as the recording's flag on both sides rather than xfailed; also test_live.py::test_live_session_says_what_the_replay_says already compared the errors coarsely

What: The live screen comes from live.py and the alert view from replay.py; nothing checks they agree. For every single-session scenario under tests/scenarios/, compare the errors and change flag in live `session_messages(...)`'s session_end message with `replay.run(load_scenario(...))`.
Interface: read pipeline/src/routine_watch/live.py (session_messages, as_json), replay.py (run), scenario.py (load_scenario). Test only: if a scenario disagrees, mark it `xfail(strict=True)` with the reason and list it in the PR body; don't change pipeline code.
Acceptance:
- `cd pipeline && pytest tests/test_live_replay_parity.py` passes quickly (fake clock, no real sleeps).
- `scripts/ci.sh` passes.

### T399 — Smoke: check the landing page is served
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: scripts/smoke.sh
- owner: ian-claude-standard
- claimed: 2026-10-17T20:02Z
- pr: #383
- rating: 5/5 clear

What: `scripts/smoke.sh` checks the dashboard at `/` returns HTML but not the public landing page `/landing.html` (T378, second Vite entry in `web/vite.config.ts`), so a broken landing build would go unnoticed before the demo.
Interface: add one check next to the existing `GET $DASHBOARD_URL -> HTML` block (~line 233): `GET $DASHBOARD_URL/landing.html` must return HTML containing `Routine Watch`; use the existing `get`/`pass`/`fail` helpers. Update the header comment listing what it checks.
Acceptance:
- With `scripts/dev.sh up`, `scripts/smoke.sh` passes and prints the new pass line; with the landing entry removed from the build it fails with a readable message.
- `bash -n scripts/smoke.sh` and `scripts/ci.sh` pass.

### T401 — Redesign 1/6: Fey-inspired design system (DESIGN.md + tokens + ui primitives)
- status: done
- class: heavy
- priority: 0
- kind: improvement
- deps: —
- area: docs/DESIGN.md, web/src/index.css, web/src/ui/
- owner: ian-claude-heavy-3
- claimed: 2026-10-17T20:21Z
- pr: #387
- rating: 4/5 clear brief and good starting observations; the only gap was where before/after screenshots should live on a private repo (raw links don't render), so I committed them under docs/design/ which is just outside the stated area

What: Ian wants the dashboard to look like Fey (finance app): quiet, premium, dark, data-first. This task sets the visual language every other redesign task builds on. Use the mobbin MCP (`search_screens` "Fey dashboard", "Fey stock chart", "Fey earnings", "Fey portfolio") to study the references; borrow structure, density and chart style, never Fey's branding or logo. Don't commit Mobbin images; link them.
References: https://mobbin.com/screens/8487cb92-3969-4f21-a847-26177466cf9a (home), https://mobbin.com/screens/7599e963-22f6-428c-b03e-f0438e2c3291 (watchlist vs markets), https://mobbin.com/screens/d70bd977-1898-4979-a799-bd2dcb94ab25 (financials charts), https://mobbin.com/screens/f7d60fde-c660-4041-8c28-e381512275dd (bar charts), https://mobbin.com/screens/729ec564-7ed7-453d-a3f2-86f51b34c96a (comparison).
What we observed (starting point, verify against the refs):
- Near-black page (~#0b0b0d) with a faint warm radial vignette on detail pages; cards one step lighter (~#141416) with 1px hairline borders (white ~6–8% alpha), radius ~12px, generous padding, few shadows.
- Type: neutral sans, small sizes (12–14px body, 15–16px card titles, semibold), muted grey secondary text, tabular numerals, numbers right-aligned.
- Colour is rare and meaningful: positive green and negative red shown as small tinted pills (text colour on ~15% alpha background); a secondary series in soft purple; dotted lines for "expected/forecast" series.
- Lists: dense rows with hairline separators, value pill on the right.
- Controls: segmented time-range pills (1M 3M YTD 1Y) with the active one on a grey chip; floating rounded "dock" navigation.
Interface:
- `docs/DESIGN.md`: the brief: principles, tokens table, chart rules (see T402), status mapping, do/don't, reference links. Short (≤150 lines).
- Tokens in `web/src/index.css`: surfaces (page, card, raised, hairline), text (primary, secondary, muted), accent + status (normal = neutral/green, watch = amber, flagged = red/pink) each with a tinted-background variant, chart palette (primary line, comparison purple, baseline band, forecast dotted), radii, spacing scale, type scale, `font-variant-numeric: tabular-nums` utility.
- `web/src/ui/`: update Card, StatusChip (tinted pill), Button, SectionHeader; add `Pill` (value/delta pill), `SegmentedControl` (time range), `Row` (dense list row with hairline). Keep existing exports working so screens don't break before their own redesign task.
Acceptance:
- Text contrast ≥ 4.5:1 on its surface for every text token (nurses, not traders: Fey's faintest greys are too light; keep the look but meet contrast). Never colour alone for status.
- Vitest tests for new primitives; `cd web && npm run lint && npm test && npm run build`; `scripts/ci.sh` passes.
- Before/after screenshots of the overview in the PR (dev server), labelled.

### T405 — Redesign 5/6: alert / evidence view
- status: done
- class: standard
- priority: 0
- kind: improvement
- deps: T401
- area: web/src/alert/, web/src/evidence/, web/src/patterns/
- owner: ian-claude-heavy-3
- claimed: 2026-10-17T20:48Z
- pr: #395
- rating: 4/5 clear on what to build; the chart-kit caveat didn't say whether the time-of-day strip counts as a chart (kept it, restyled its container), and 'tests updated for structure only' left the h2 reading order and the baseline/threshold wording open — both had to change to follow SPEC section 9's order

What: (Starts after T401; if the chart kit (T417–T419) hasn't merged yet, keep existing chart components and only restyle their containers; a follow-up swaps the charts.) The "why" screen judges score most. Summary as a Fey "daily recap" card (short bold summary, muted detail); "Possible patterns" as ranked cards with confidence bars and rule-out checks; errors as dense timestamped rows with type pills (red/amber/grey); replay and ghost replay in a dark media card; Confirm / False alarm as clear buttons. Keep "consistent with", never "diagnosis".
Acceptance: readable in 10 s (one glance: what changed, how sure, what to check); tests updated for structure only; before/after screenshot; `scripts/ci.sh` passes.

### T408 — Roles: role chooser, role-aware shell, mock people/linking API
- status: done
- class: heavy
- priority: 0
- kind: feature
- source: ian
- deps: —
- area: web/src/people/, web/src/App.tsx, web/src/App.test.tsx, web/src/mock/people.ts
- owner: —
- claimed: —
- pr: #388
- rating: 4/5 clear on the API and routing; didn't say who the supervisor 'I' am (Nurse Ana with the whole unit, or Lena with one) - that choice decides whether the existing nurse flow stays the default, and Mr. D/Sam have no pipeline data so their detail screen is empty
- note: merge conflict with main on PR #388: check out its branch, merge origin/main, fix, push

What: Ian's pivot (SPEC §3, §17): the app is for anyone, not just nurses. Two roles: **person** (watches themselves) and **supervisor** (family, carer or nurse). Frontend only; no pairing backend.
Interface:
- `web/src/people/api.ts`: `getRole()/setRole('person'|'supervisor')`, `currentPerson()`, `supervisorsOf(personId)`, `peopleISupport()`, `createInvite(personId) -> {code, link}`, `acceptInvite(code)`, `unlink(personId, supervisorId)`. Backed by localStorage + `web/src/mock/people.ts` (Mrs. K ← Nurse Ana; Mr. D ← his daughter Lena; Sam self-monitoring, no supervisor). Keep it an interface so a real API can replace it.
- First-open **role chooser** ("I'm setting this up for myself" / "I'm supporting someone"), remembered; a role switcher in the shell; "Reset demo" clears it.
- Routing in `App.tsx`: person → `MyRoutine` placeholder (T409 fills it); supervisor → existing overview, but with exactly one supported person it opens straight into their detail.
Acceptance:
- Vitest: chooser shows on first open and not after; switching roles changes the home screen; invite create/accept/unlink round-trips through the mock.
- Existing nurse/care-home flow still works as the supervisor-with-many case; `scripts/ci.sh` passes.

### T412 — Replay store: keep skeleton replays of every session with errors
- status: done
- class: heavy
- priority: 0
- kind: feature
- source: ian
- deps: —
- area: pipeline/src/routine_watch/replays.py, pipeline/src/routine_watch/session_log.py, pipeline/src/routine_watch/live.py, pipeline/src/routine_watch/live_camera.py, pipeline/src/routine_watch/api_residents.py, pipeline/src/routine_watch/evidence.py, pipeline/src/routine_watch/demo.py, pipeline/tests/test_replays.py
- owner: ian-claude
- claimed: 2026-10-17T20:18Z
- pr: #392
- rating: 4/5 clear on what to build and the privacy rules; it didn't say which clock retention is measured against (demo sessions sit on DEMO_NOW, in the past, so a wall clock prunes the whole library), nor where the 'most recent normal' comparison is reachable from once list() excludes it - the route needed an envelope contract the interface didn't name

What: Ian wants supervisors (and the person) to look back at failed attempts and judge for themselves (SPEC §17). Today replays exist only inside an alert and come from two canned recordings; live sessions keep steps and errors but not frames. Store a replay for every session that had at least one error (and keep the person's most recent normal session as the comparison). Skeletons, hand landmarks, object boxes and timestamps only, downsampled (~10 fps); never video (SPEC §8).
Interface:
- `replays.py`: `ReplayStore` interface with in-memory default and an on-disk JSONL.gz implementation (`REPLAY_DIR`, default `.data/replays/`); `save(session, frames, errors)`, `list(person_id, since=None, error_type=None) -> [ReplaySummary]`, `get(session_id) -> Replay` (frames + error markers with t_start/t_end/type/step), `delete(session_id)`, retention `REPLAY_RETENTION_DAYS` (default 30) pruned on save. Shape as contracts (`ReplaySummary`, `Replay`, `ReplayMarker`) and regenerate TS.
- Live and camera sessions save on `session_end` when errors > 0; demo/synthetic people get generated replays for their bad sessions (reuse `stick_figure` where no landmarks), so the library isn't empty in the demo.
- API: `GET /people/{person_id}/replays?type=&since=`, `GET /replays/{session_id}` (frames + markers, supersedes the alert-only path; keep `/sessions/{id}/replay` working), `DELETE /replays/{session_id}`.
Acceptance:
- Tests: a session with errors is saved and listed, a clean session is not; markers line up with the error timestamps; retention prunes; delete works; no image/video fields can be stored (privacy test).
- `scripts/ci.sh` + `scripts/e2e.sh` pass.

### T414 — Bug: resident detail still shows the old threshold after "Confirmed" changes it
- status: done
- class: light
- priority: 1
- kind: bug
- source: tester
- deps: —
- area: pipeline/src/routine_watch/api_state.py, pipeline/tests/test_api_feedback_threshold.py
- owner: ian-claude-standard
- claimed: 2026-10-17T20:22Z
- pr: #386
- rating: 5/5 clear

What: After a nurse clicks "Confirmed" on Mrs. K's alert, the alert view shows "Current threshold: 2.3" (was 2.4), but going back to Mrs. K's resident detail the baseline chart still says "flag threshold 2.4". `api_state._tuned()` recomputes `status`/`top_pattern` against the feedback-tuned threshold but returns `baseline.threshold` unchanged, so `/residents` and `/residents/{id}` disagree with the alert payload (SPEC MVP 7: threshold visibly changes).
Repro (OFFLINE_MODE=true): `scripts/dev.sh up` → dashboard → let the Making tea live replay finish → Open alert → Confirmed (shows 2.3) → reload, open Mrs. K → chart aria-label "Baseline chart: ... flag threshold 2.4".
Expected: resident detail/overview show the same tuned threshold as the alert (2.3). Actual: raw baseline threshold 2.4.
Interface: `_tuned()` also returns `baseline: {**resident["baseline"], "threshold": <tuned>}`; no contract change.
Acceptance:
- pytest: after confirm feedback via the API, `GET /residents/mrs-k` `baseline.threshold` equals the alert's threshold; with no feedback it is unchanged
- `scripts/ci.sh` passes

### T415 — Deploy: Docker images + compose for API and dashboard (Vultr-ready)
- status: done
- class: standard
- priority: 1
- kind: feature
- deps: —
- area: deploy/, docs/DEPLOY.md, .dockerignore
- owner: max_API_standard
- claimed: 2026-10-17T20:35Z
- pr: #391
- rating: 4/5 Clear deployment interface; worker lacks Docker, so acceptance ran on an isolated GitHub Actions Linux runner.

What: SPEC §5/§16-C says the backend (FastAPI + dashboard) is hosted on Vultr, but the repo has no container or deploy setup, so the judges' demo URL can't be stood up quickly. Add a reproducible container build that a human can run on any Docker host (Vultr VM) with one command. Don't provision cloud resources or buy domains; humans do that.
Interface:
- `deploy/api.Dockerfile`: Python image, `uv sync` of `pipeline/` (no `capture` extra), runs `uvicorn routine_watch.api:app --host 0.0.0.0 --port 8000`; non-root user; healthcheck on an existing GET route.
- `deploy/web.Dockerfile`: multi-stage, `npm ci && npm run build` in `web/` with build arg `VITE_API_URL`, served by nginx (both `/` and `/landing.html`), SPA fallback to `index.html`.
- `deploy/docker-compose.yml`: `api` + `web` (+ optional `db` timescale service under a `tsdb` profile, used only when `DATABASE_URL` points at it); env from `.env` (`env_file`), defaults `OFFLINE_MODE=true`, `LIVE_API=0`; `CORS_ORIGINS` set to the web origin; replay/data dirs on a named volume.
- `docs/DEPLOY.md` (≤60 lines): build/run commands, which `.env` vars matter in prod, how to point a domain + TLS (Caddy or similar, described not committed), and the privacy rule (no video stored).
- `.dockerignore`: excludes node_modules, .venv, .cache, .data, .dev, .env, models/.
Acceptance:
- `docker compose -f deploy/docker-compose.yml up -d --build` then `DASHBOARD_URL=http://localhost:<web port> API_URL=http://localhost:8000 scripts/smoke.sh` passes (paste the output in the PR); `docker compose ... down` cleans up.
- No secrets in images (`.env` not copied); `scripts/ci.sh` passes.
- If you add a module or script, add a CODEMAP note in this PR.

### T403 — Redesign 3/6: unit overview + app shell
- status: done
- class: standard
- priority: 0
- kind: improvement
- deps: T401
- area: web/src/overview/, web/src/App.tsx, web/src/App.test.tsx
- owner: ian-claude-standard-3
- claimed: 2026-10-17T21:01Z
- pr: #404
- rating: 4/5 clear task, but it landed just as T408 (role chooser / role-aware shell) merged into main and also rewrote App.tsx's header, which the task description didn't anticipate; had to merge origin/main mid-task and hand-reconcile the two shells

What: (Starts after T401; if the chart kit (T417–T419) hasn't merged yet, keep existing chart components and only restyle their containers; a follow-up swaps the charts.) Make the overview read like Fey's watchlist: one card, dense resident rows (name + room, status pill, top pattern in muted text, MicroBars trend, score pill right-aligned), sort/filter as small segmented pills. App shell: compact top bar (product name, unit, offline/demo indicator) and a floating rounded nav dock for the main screens, following `docs/DESIGN.md`. Check Fey refs via the mobbin MCP (watchlist, home).
Acceptance: keyboard nav and existing behaviour unchanged (tests updated for structure only); flagged resident still understood in 10 s; before/after screenshot in PR; `scripts/ci.sh` passes.

### T416 — Local camera preview: real video + skeleton overlay, this device only
- status: done
- class: heavy
- priority: 0
- kind: feature
- source: ian
- deps: T424
- area: pipeline/src/routine_watch/capture.py, pipeline/src/routine_watch/preview.py, pipeline/tests/test_preview.py, scripts/camera.sh, web/src/live/LiveSession.tsx, web/src/live/LiveSession.test.tsx, docs/DEMO.md, SPEC.md
- owner: ian-claude-heavy-2
- claimed: 2026-10-17T21:04Z
- pr: #399
- rating: 4/5 clear: the only gap was that the split left the T424 component's video layout cropping the picture (object-fit: cover), so 'aligned to the same coordinates' needed a 3-line CSS fix outside the listed area; also worth saying the preview server starts with the camera, so the web probe has to wait for the first frame

What: Ian wants to see the actual camera picture during a live session, not just the skeleton. Keep the privacy promise: video never leaves the capture machine, is never stored, never reaches the API or a remote supervisor.
Why: the demo is far more convincing with the real kitchen and the skeleton tracking on top, and it helps frame the camera for Roboflow training clips.
Interface:
- `preview.py`: an MJPEG endpoint served by the **capture process itself**, bound to `127.0.0.1` only (`PREVIEW_PORT`, default 8765), off unless `CAMERA_PREVIEW=1` / `scripts/camera.sh --preview`. Frames come from the same capture loop (one camera handle; Windows can't open the webcam twice), downscaled (≤640 px, ~10 fps), held in memory for the current frame only, never written to disk. Refuses non-loopback clients.
- Web (`web/src/live/`): "Show camera preview (this device only)" toggle on the Live screen, shown only when the page is on localhost and the preview responds. Video underneath, the existing skeleton + boxes canvas on top, aligned to the same coordinates; a visible "Preview · not recorded · this device only" badge. Falls back to skeleton-only everywhere else, quietly.
- `scripts/camera.sh --preview` turns it on and prints the URL; `docs/DEMO.md` explains it; SPEC §12/§16 gets one line: optional local preview, loopback only, never stored or transmitted.
Split (orch): the web toggle/overlay component is T424 (`web/src/live/CameraPreview.tsx`). This task serves `GET /preview.mjpg` and `GET /health` → `{"ok": true}` with `Access-Control-Allow-Origin: *` on the loopback server, and wires `<CameraPreview>` around the existing `<SkeletonView>` in `LiveSession.tsx`.
Acceptance:
- Tests: preview rejects a non-loopback client; nothing under the repo or `REPLAY_DIR`/`CAMERA_RECORD` contains image data after a session with preview on (privacy test); capture still writes the same JSONL with preview on or off.
- Web test: toggle hidden when not on localhost or preview unreachable; badge shown when on.
- `scripts/ci.sh` passes without opencv/mediapipe installed (lazy imports).

### T417 — Chart kit: LineChart + RangeSelector (Fey style)
- status: done
- class: standard
- priority: 0
- kind: improvement
- source: ian
- deps: T401
- area: web/src/ui/charts/LineChart.tsx, web/src/ui/charts/LineChart.test.tsx, web/src/ui/charts/RangeSelector.tsx, web/src/ui/charts/RangeSelector.test.tsx, web/src/ui/charts/scale.ts, web/src/ui/charts/scale.test.ts, web/src/ui/charts/charts.css
- owner: max_API_standard
- claimed: 2026-10-17T21:02Z
- pr: #397
- rating: 5/5 clear

What: Split from T402 so the chart kit is built in parallel. Dependency-free SVG `LineChart` per `docs/DESIGN.md`: thin 1.25–1.5px line, at most a faint gradient, a few hairline/dashed gridlines, tiny muted axis labels, **end-of-line value tag** (pill with the latest value), optional **baseline band** (mean ± threshold), optional dotted comparison series, hover/focus crosshair + tooltip, keyboard focus across points. `RangeSelector` (7D 14D 30D) on `SegmentedControl`. `scale.ts`: linear/time scales and "nice" ticks. Check Fey chart refs via the mobbin MCP (see T401).
Acceptance: accessible name + text alternative (summary line); tests for ticks, end tag = latest value, band drawn only when given, keyboard focus; `cd web && npm test && npm run build`.

### T407 — Redesign: landing page onto the Fey-inspired system
- status: done
- class: standard
- priority: 0
- kind: improvement
- deps: T401, T417
- area: web/src/landing/, web/landing.html
- owner: ian-claude
- claimed: 2026-10-17T21:28Z
- pr: #405
- rating: 4/5 clear; the only judgement call was that the chart kit's band is symmetric around the mean, so an error score needs data whose mean is well above 2 sigma to avoid a negative lower bound

What: The landing page (T378) predates the redesign. Restyle it per `docs/DESIGN.md`: dark premium hero, one real chart from the chart kit (a resident's score vs personal baseline band, with the end-of-line tag) as the hero visual, sections as hairline cards. Check Fey refs via the mobbin MCP. Copy unchanged unless it breaks the layout.
Acceptance: mobile + desktop screenshots (before/after) in the PR; landing tests still pass; `scripts/ci.sh` passes.

### T409 — Person view: "My routine"
- status: done
- class: heavy
- priority: 0
- kind: feature
- source: ian
- deps: T408
- area: web/src/people/MyRoutine.tsx, web/src/people/MyRoutine.test.tsx, web/src/person/routine/
- owner: ian-claude-heavy-3
- claimed: 2026-10-17T21:23Z
- pr: #407
- note: T408 already shipped a basic MyRoutine in web/src/people/MyRoutine.tsx; extend it there, put new pieces under web/src/person/routine/ (own CSS file, not people.css). Use PrivacyCard (T429) and personNotes (T423).
- rating: 4/5 clear on the sections and wording; it pointed at PrivacyCard (T429) and personNotes (T423) as if both had landed, but T429 was still todo, so the privacy card had to be built to its interface inside this area

What: What someone watching themselves sees (SPEC §17). Calm and personal; never alarming or diagnostic. Use the mobbin MCP for 2–3 references of calm personal health/habit dashboards (and follow `docs/DESIGN.md` if it has landed).
Interface (`web/src/person/MyRoutine.tsx` + pieces):
- Status in plain words ("Your routine looks like your usual this week" / "A few things looked different today").
- One chart: my usual vs today/this week (reuse existing chart components or the chart kit if merged).
- Recent sessions (task, time, what went smoothly / what was different).
- **Notes** when a change is flagged: the same patterns, rephrased for the person ("Some steps took longer than usual for you, mostly in the evening. Worth mentioning to Lena or your doctor."), with a "tell my supervisor" button (mock). Use `personNote`/`personStatus` from `web/src/person/personNotes.ts` (T423) if merged.
- **Who can see this**: supervisors list with remove; "Invite someone" (shows the invite code + copy link from T408's API); self-monitoring state when there's nobody.
- Privacy: pause monitoring, "what's stored" (skeletons only, no video), and "your supervisors see exactly this".
Acceptance:
- Vitest for each section incl. no-supervisor and flagged states; wording test: no "diagnos", no "patient", no alarm words ("danger", "warning", "emergency") in person-facing copy.
- Keyboard + screen-reader friendly; mobile width works; `scripts/ci.sh` passes. Screenshot in PR.

### T418 — Chart kit: BarChart (paired bars + callout)
- status: done
- class: light
- priority: 0
- kind: improvement
- source: ian
- deps: T401
- area: web/src/ui/charts/BarChart.tsx, web/src/ui/charts/BarChart.test.tsx
- owner: Max_codex_light
- claimed: 2026-10-17T20:48Z
- pr: #394
- rating: 5/5 clear

What: Split from T402. Read only `docs/DESIGN.md`, `web/src/index.css` (tokens) and `web/src/ui/` primitives. SVG `BarChart`: slim rounded bars, optional second series muted/outlined beside each bar (e.g. this week vs usual), optional callout pill above one highlighted bar (`callout={{index, label: "2.4× usual"}}`), tiny muted labels, tokens only (no hex). Props: `data: {label: string, value: number, compare?: number}[]`, `ariaLabel`, `highlight?`. Self-contained (own min/max scaling; don't import `scale.ts`).
Acceptance: renders N bars; compare series only when present; callout shows its label; has an accessible name and a visually hidden data table; `cd web && npx vitest run src/ui/charts/BarChart.test.tsx`.

### T419 — Chart kit: MicroBars (14-day tick strip)
- status: done
- class: light
- priority: 0
- kind: improvement
- source: ian
- deps: T401
- area: web/src/ui/charts/MicroBars.tsx, web/src/ui/charts/MicroBars.test.tsx
- owner: ian-claude
- claimed: 2026-10-17T21:04Z
- pr: #398
- rating: 5/5 clear

What: Split from T402. Read only `docs/DESIGN.md` and `web/src/index.css`. A row of thin vertical ticks (like Fey's sector rows), one per day, height = score, colour by status token (normal / watch / flagged; missing day = faint hairline). Props: `days: {date: string, score: number | null, status: 'normal'|'watch'|'flagged'}[]`, `ariaLabel`. Fixed small size (~84×20) for list rows.
Acceptance: one tick per day; null days render as hairlines; status colours via tokens; accessible name summarises "14 days, 2 flagged"; `cd web && npx vitest run src/ui/charts/MicroBars.test.tsx`.

### T421 — Restyle: BaselineChart + drift card on LineChart
- status: done
- class: standard
- priority: 0
- kind: improvement
- source: ian
- deps: T417
- area: web/src/resident/BaselineChart.tsx, web/src/resident/BaselineChart.test.tsx, web/src/resident/*Drift*.tsx, web/src/resident/*Drift*.test.tsx
- owner: ian-claude-standard-4
- claimed: 2026-10-17T21:37Z
- pr: #409
- rating: 4/5 mostly clear: DriftCard has no series data in its props (only slopePerDay/days/trending/minDays), so the acceptance's 'dotted trend series' and 'same props and data as today' had to be reconciled by synthesizing a 2-point fitted line from the slope rather than plotting real daily readings - worth saying explicitly next time if that's the intent
- note: CI fails only on check:bundle (over budget); rebase on main once T442 (bundle budget) merges.

What: Split from T402. `BaselineChart` → `LineChart` with the personal baseline band, end-of-line tag and `RangeSelector`; the slow-drift card → `LineChart` with a dotted trend series. Same props and data as today.
Acceptance: existing tests pass (selectors only); before/after screenshot of Mrs. K in the PR; `cd web && npm test`.

### T422 — Restyle: HeatCalendar in the Fey palette
- status: done
- class: light
- priority: 0
- kind: improvement
- source: ian
- deps: T401
- area: web/src/resident/HeatCalendar.tsx, web/src/resident/HeatCalendar.test.tsx, web/src/resident/heatCalendar.css
- owner: ian-claude-standard
- claimed: 2026-10-17T21:27Z
- pr: #401
- note: released by ian-claude-standard-4: run ended without progress; partial work on branch task/T422-wip-2122: start from it (git switch task/T422-wip-2122 && git merge origin/main)
- rating: 5/5 clear

What: Split from T402. Read only `docs/DESIGN.md`, `web/src/index.css` and the HeatCalendar files. Muted Fey palette: tinted cells from the status tokens, hairline gaps, small rounded cells, muted weekday labels, legend as small pills. No hex in the component; behaviour unchanged.
Acceptance: existing HeatCalendar tests pass (selectors only); `cd web && npx vitest run src/resident/HeatCalendar.test.tsx`.

### T410 — Supervisor side: "People I support" + add a person
- status: done
- class: standard
- priority: 0
- kind: feature
- source: ian
- deps: T408
- area: web/src/people/PeopleISupport.tsx, web/src/people/PeopleISupport.test.tsx, web/src/supporting/, web/src/overview/UnitOverview.tsx, web/src/overview/UnitOverview.test.tsx
- owner: ian-claude-standard-3
- claimed: 2026-10-17T22:02Z
- pr: #412
- note: orch: bundle budget raised in #409; merged origin/main into PR, CI re-running with auto-merge
- rating: 4/5 clear, but T408 (merged before this task existed) had already implemented most of SPEC §17's supervisor routing in App.tsx outside this task's listed area, so the real gap was narrower (and less obvious) than the task text implied -- the note helped but didn't flag that

What: Generalise the nurse overview into "People I support" (SPEC §17). Care-home supervisor sees the unit list as today; a family supervisor with one person goes straight to that person; anyone can **add a person** by entering an invite code (T408's mock API), with a clear "linked" confirmation. Each row/detail shows the person's context ("care home · Room 12" vs "lives alone").
Acceptance: Vitest for many/one/zero supported people and the add-by-code flow; existing overview behaviour kept for the care-home case; `scripts/ci.sh` passes. Screenshot in PR.

### T423 — Person view: person-facing wording for status and pattern notes
- status: done
- class: light
- priority: 1
- kind: feature
- source: orch (carved from T409)
- deps: —
- area: web/src/person/personNotes.ts, web/src/person/personNotes.test.ts
- owner: max_API_light
- claimed: 2026-10-17T20:45Z
- pr: #393
- rating: 5/5 clear

What: Pure functions that turn existing nurse-facing data into calm, personal copy for someone watching themselves (SPEC §17 "Person view"). T409 ("My routine") will consume them.
Why: inherits T409 — the person view is half of the roles pivot judges will see.
Read only: `web/src/contracts.ts` (type `PatternMatch`, ~line 374), `web/src/wording.test.ts` (style of the existing wording checks).
Interface (`web/src/person/personNotes.ts`):
- `personStatus(state: 'normal' | 'watch' | 'flagged'): string` — e.g. normal "Your routine looks like your usual this week", watch "A few things looked a little different lately", flagged "A few things looked different today".
- `personNote(match: PatternMatch, supervisorName?: string): { title: string; body: string }` — one entry per pattern_id: `sudden_change`, `slow_drift`, `evening_worsening`, `motor_slowing`, `executive_pattern`, `one_sided_change`, plus a generic fallback for unknown ids. Describe what was different in everyday words ("Some steps took longer than usual, mostly in the evening") and end with "Worth mentioning to <supervisorName> or your doctor." (or "Worth mentioning to your doctor or someone you trust." without a name). Never reuse the nurse-facing `name` (it has clinical terms like "delirium").
Acceptance:
- `web/src/person/personNotes.test.ts` (Vitest): every pattern id + the fallback returns non-empty title/body; with and without supervisor name; for all outputs, case-insensitive: no "diagnos", "patient", "delirium", "dementia", "stroke", "danger", "warning", "emergency", "urgent".
- `cd web && npx vitest run src/person/personNotes.test.ts` and `scripts/ci.sh` pass.

### T424 — Live screen: local camera preview component (toggle, video under skeleton, badge)
- status: done
- class: light
- priority: 1
- kind: feature
- source: orch (carved from T416)
- deps: —
- area: web/src/live/CameraPreview.tsx, web/src/live/CameraPreview.test.tsx
- owner: ian-claude-standard-3
- claimed: 2026-10-17T20:47Z
- pr: #389
- rating: 5/5 clear

What: A self-contained React component for T416's local-only camera preview. Not wired into any screen here (T416 does that).
Why: inherits T416 — the demo is far more convincing with the real kitchen under the skeleton.
Read only: `web/src/live/SkeletonView.tsx` (renders an `<svg>` sized `width`×`height`, default 480×360).
Interface (`web/src/live/CameraPreview.tsx`):
- `export function CameraPreview({ port = 8765, children, probe }: { port?: number; children: React.ReactNode; probe?: () => Promise<boolean> })`.
- Default probe: only if `window.location.hostname` is `localhost`, `127.0.0.1` or `::1`, `fetch('http://127.0.0.1:<port>/health')` with a 1 s timeout (AbortController); true when it returns `{ ok: true }`. Any error → false, no console noise.
- Probe false: render `children` only (no toggle, nothing else).
- Probe true: a toggle button "Show camera preview (this device only)" (`aria-pressed`). On: an `<img src="http://127.0.0.1:<port>/preview.mjpg" alt="">` fills the box, `children` absolutely positioned on top at the same size, and a visible badge "Preview · not recorded · this device only". Off: children only.
Acceptance:
- `CameraPreview.test.tsx` (Vitest + Testing Library, inject `probe`): toggle hidden when probe false; hidden on a non-localhost hostname with the default probe (mock `fetch`, assert not called); toggle on shows img + badge + children; toggle off removes img; button keyboard operable.
- `cd web && npx vitest run src/live/CameraPreview.test.tsx` and `scripts/ci.sh` pass.

### T425 — Review: handoff summary counts unclear-camera rooms as "nothing to review"
- status: done
- class: light
- priority: 1
- kind: bug
- source: reviewer
- deps: —
- area: pipeline/src/routine_watch/handoff.py, pipeline/tests/test_handoff_unclear.py
- owner: ian-claude-standard
- claimed: 2026-10-17T20:47Z
- pr: #390
- rating: 5/5 clear

What: T355 added `unclear_sessions` to each handoff row and a chip on screen, but `_context()` in `handoff.py` still counts a resident whose room had unclear sessions (and no flags) in "N residents with nothing to review", so the summary a nurse reads says the room was quiet while the row says check the camera — the exact silence T355 meant to fix.
Fix: in `_context()`, add one line per resident with `unclear_sessions > 0` (e.g. "<name>: N sessions too unclear to score, check the camera view", camera wording, nothing about the resident) and exclude them from the `quiet` count. Keep `_needs_review` unchanged (unclear is not a flag).
Acceptance:
- Test in `test_handoff_unclear.py`: with one unclear session recorded for a quiet resident's room, the explainer context mentions the camera line and the quiet count drops by one.
- `scripts/ci.sh` passes.

### T426 — Bug: integration check still flaky ("dashboard did not render" on a cold start)
- status: done
- class: standard
- priority: 0
- kind: bug
- source: ian
- deps: —
- area: scripts/integration.sh, scripts/dev.sh
- owner: ian-claude-standard
- claimed: 2026-10-17T21:00Z
- pr: #396
- rating: 5/5 clear, found a real latent gap in the render check while verifying the acceptance criterion

What: T367 didn't fully fix it. The hourly integration check and the tester both see `FAIL dashboard did not render (no 'Routine Watch' in DOM)` on the first run after `dev.sh up`, then pass on a re-run: Vite's cold dependency optimisation finishes after headless Chrome's 8 s budget.
Why: a red integration check the morning of the demo (due 13:00 UTC) hides real breakage.
Interface: in `scripts/integration.sh`, warm the dev server before the render check (fetch `/`, `/src/main.tsx` and wait until a second fetch of the page is fast) and retry the DOM check up to 3 times with a longer budget; or render against `vite preview` of a built `dist/` instead of the dev server. Don't weaken the check (it must still fail if the app really doesn't render).
Acceptance: `scripts/dev.sh down && scripts/integration.sh` passes 5 times in a row from cold; breaking `web/src/main.tsx` on purpose makes it fail.

### T427 — Replays data layer: API client + mock fixture for the replays library
- status: done
- class: light
- priority: 0
- kind: feature
- deps: T412
- area: web/src/replays/api.ts, web/src/replays/api.test.ts, web/src/mock/replays.ts
- owner: max_API_light
- claimed: 2026-10-17T21:11Z
- pr: #403
- rating: 4/5 Repeat marker wording differs from contract perseveration; otherwise clear

What: The fetch layer T413's Replays screen will consume, carved out of T413 so the screen task only builds UI. Backend routes landed in T412.
Interface: in `web/src/replays/api.ts` export `fetchPersonReplays(personId): Promise<PersonReplays>`, `fetchReplay(replayId): Promise<Replay>`, `deleteReplay(replayId): Promise<void>`, calling `GET /people/{id}/replays`, `GET /replays/{id}`, `DELETE /replays/{id}`. Follow the base-URL/offline-fallback pattern in `web/src/evidence/api.ts` exactly (fall back to the mock when the API is unreachable or in offline mode). Types `PersonReplays`, `ReplaySummary`, `Replay`, `ReplayMarker` already exist in `web/src/contracts.ts` (~lines 431–510); do not change contracts. `web/src/mock/replays.ts`: 3 replays for Mrs. K (omission, sequence, repeat markers), 1 for Mr. D, 0 for Sam, plus one `normal` summary; skeleton frames only, no images.
Files to read: `web/src/evidence/api.ts`, `web/src/evidence/api.test.ts`, `web/src/contracts.ts` (replay types), `web/src/mock/replay.ts`, `web/src/mock/people.ts` (person ids), `pipeline/src/routine_watch/api_residents.py` lines 179–260 (route shapes).
Acceptance:
- Vitest in `web/src/replays/api.test.ts`: success path (mocked fetch), fallback to mock on network error, delete sends DELETE, Sam returns an empty list.
- `cd web && npx vitest run src/replays` and `scripts/ci.sh` pass.

### T404 — Redesign 4/6: resident detail
- status: done
- class: standard
- priority: 0
- kind: improvement
- deps: T401, T421, T422
- area: web/src/resident/ResidentDetail.tsx, web/src/resident/SessionList.tsx, web/src/resident/ContextTimeline.tsx, web/src/resident/*.css, web/src/resident/ResidentDetail.test.tsx
- owner: max_API_standard-2
- claimed: 2026-10-17T22:36Z
- pr: #421
- rating: 5/5 clear

What: Fey "stock detail" layout for a resident: header (name, status pill, top pattern), hero BaselineChart card with range selector, then a two-column grid of cards (heat calendar, sessions as dense rows with error pills, care-record timeline with tinted markers for new meds/fever). Faint warm vignette background per `docs/DESIGN.md`.
Acceptance: same data and states (loading/empty/error) as now; before/after screenshot; `scripts/ci.sh` passes.

### T428 — Handoff: delta chip onto the Pill primitive
- status: done
- class: light
- priority: 1
- kind: improvement
- source: orch (carved from T406)
- deps: —
- area: web/src/handoff/HandoffDelta.tsx, web/src/handoff/HandoffDelta.css, web/src/handoff/HandoffDelta.test.tsx
- owner: Max_codex_light
- claimed: 2026-10-17T21:17Z
- pr: #400
- rating: 5/5 clear

What: Render `<HandoffDelta>` with the redesign's `Pill` (`web/src/ui/Pill.tsx`) instead of its own CSS chip, so handoff rows get Fey-style delta pills.
Why: inherits T406 — the handoff screen is on the demo path and should match the redesign.
Read only: `web/src/handoff/HandoffDelta.tsx`, `web/src/handoff/HandoffDelta.test.tsx`, `web/src/ui/Pill.tsx`.
Interface: keep `HandoffDelta({flags, previousFlags})` and `handoffDeltaLabel(...)` signatures and every label string unchanged. Mapping: more → `<Pill tone="negative" direction="up">`, fewer → `tone="positive" direction="down"`, same → `tone="neutral"` (no direction). Keep a `handoff-delta` class on the pill (via `className`) so existing selectors in `Handoff.tsx` tests still find it. Delete `HandoffDelta.css` if nothing else imports it (`grep -r HandoffDelta.css web/src`).
Acceptance:
- Tests updated: each tone renders the matching `pill--<tone>` class and the same label text; nothing rendered when `previousFlags` is null/undefined.
- `cd web && npx vitest run src/handoff` and `scripts/ci.sh` pass.

### T429 — Person view: privacy card (pause, what's stored, who sees it)
- status: done
- class: light
- priority: 1
- kind: feature
- source: orch (carved from T409)
- deps: —
- area: web/src/person/PrivacyCard.tsx, web/src/person/PrivacyCard.test.tsx, web/src/person/privacyCard.css
- owner: max_API_standard
- claimed: 2026-10-17T21:28Z
- pr: #402
- rating: 5/5 clear

What: A self-contained card T409 ("My routine") will drop in. Not wired into any screen here.
Why: inherits T409 — "skeletons only, no video" is the privacy story judges ask about.
Read only: `web/src/ui/Card.tsx`, `web/src/ui/Button.tsx`, `web/src/ui/SectionHeader.tsx`, `web/src/person/personNotes.test.ts` (wording-check style).
Interface: `export function PrivacyCard({ paused, onTogglePause, supervisorNames }: { paused: boolean; onTogglePause: () => void; supervisorNames: string[] })`.
- Heading "Your privacy". Pause button: "Pause watching" / "Resume watching" (`aria-pressed={paused}`); when paused a line "Watching is paused. Nothing is recorded until you resume."
- "What's stored": "Body outlines (skeletons) and timings only. No video or photos ever leave this device or get saved."
- Who sees it: with names → "Lena and Sam see exactly what you see here." (join 1/2/3+ names naturally); with none → "Only you can see this."
- Own CSS in `privacyCard.css` using tokens from `web/src/index.css`.
Acceptance:
- Vitest: paused/unpaused text + `aria-pressed`, click calls `onTogglePause`, 0/1/2/3 supervisor names; no "diagnos", "patient", "danger", "warning", "emergency" in rendered text.
- `cd web && npx vitest run src/person/PrivacyCard.test.tsx` and `scripts/ci.sh` pass.

### T420 — Restyle: overview Sparkline → MicroBars
- status: done
- class: light
- priority: 0
- kind: improvement
- source: ian
- deps: T419
- area: web/src/overview/Sparkline.tsx, web/src/overview/Sparkline.test.tsx
- owner: max_API_standard-2
- claimed: 2026-10-17T22:05Z
- pr: #415
- rating: 4/5 Separate Sparkline accessibility tests and baseline bundle-budget failure were not listed
- note: orch: CI failed on bundle budget (171 B over); budget raised in #418, branch updated with main, CI re-running

What: Split from T402. Make `Sparkline` render `MicroBars` (web/src/ui/charts/MicroBars.tsx) from the same input it takes today; keep its props and export so callers don't change. Read only those files and `web/src/overview/types.ts`.
Acceptance: existing Sparkline tests pass (update selectors only); `cd web && npx vitest run src/overview`.

### T430 — Replays: list with error-type filter and empty state (component)
- status: done
- class: light
- priority: 0
- kind: feature
- deps: —
- area: web/src/replays/ReplayList.tsx, web/src/replays/ReplayList.test.tsx, web/src/replays/replayList.css
- owner: Max_codex_light
- claimed: 2026-10-17T21:43Z
- pr: #408
- rating: 5/5 clear

What: Carved from T413 (Ian's replays library). A presentational list of a person's replays that T413's screen will drop in. No fetching, no routing.
Interface: `export function ReplayList(props: { replays: ReplaySummary[]; normal?: ReplaySummary | null; onOpen: (sessionId: string) => void })`. Rows newest first: date/time (from `started_at`), `task_id`, one `Pill` per `error_types` entry (labels from `web/src/ui/errorTypes.ts`), duration as "m:ss". Above the list a filter (`SegmentedControl` from `web/src/ui/`): "All" plus each error type that appears; filtering is local state. If `normal` is given, show it last, labelled "Most recent normal session (for comparison)". Empty state via `web/src/ui/EmptyState.tsx`: "No sessions with errors in the last 30 days". Each row is a button calling `onOpen(session_id)`.
Files to read: `web/src/contracts.ts` lines 425–535 (`PersonReplays`, `ReplaySummary`), `web/src/ui/Pill.tsx`, `web/src/ui/Row.tsx`, `web/src/ui/SegmentedControl.tsx`, `web/src/ui/EmptyState.tsx`, `web/src/ui/errorTypes.ts`, `docs/DESIGN.md` (tokens only). Use CSS vars from `web/src/index.css`; no new colours.
Acceptance:
- Vitest in `ReplayList.test.tsx`: newest-first order, filter narrows rows and "All" restores, empty state text, normal row shown last with its label, clicking a row calls `onOpen` with the id, rows reachable by Tab and activated by Enter.
- No "diagnos"/"patient" in copy. `cd web && npx vitest run src/replays/ReplayList` and `scripts/ci.sh` pass.

### T406 — Redesign 6/6: live session + handoff
- status: done
- class: standard
- priority: 0
- kind: improvement
- deps: T401
- area: web/src/live/, web/src/handoff/Handoff.tsx, web/src/handoff/handoff.css, web/src/handoff/Handoff.test.tsx, web/src/handoff/Handoff.keyboard.test.tsx, web/src/handoff/Handoff.defaults.test.tsx
- owner: ian-claude-standard-4
- claimed: 2026-10-17T22:36Z
- pr: #416
- note: conflict resolved; PR #416 is CLEAN, ci passed, auto-merge on
- rating: 4/5 clear on what to build and the note about T428 saved a collision; the area list didn't cover the before/after screenshots the acceptance asks for (docs/design/, docs/DESIGN.md), so that had to be taken outside the area

What: (Starts after T401; if the chart kit (T417–T419) hasn't merged yet, keep existing chart components and only restyle their containers; a follow-up swaps the charts.) Live screen as a dark media card (skeleton view) beside the task map styled as a vertical step list with Fey-style pills (done/green, error/red, repeat/amber, unclear/grey) and a slim progress line; shift handoff as dense rows with delta pills ("+2 vs last shift").
Acceptance: live updates still animate; tests updated for structure only; before/after screenshot; `scripts/ci.sh` passes.

### T431 — Replays: supervisor notes on a replay (component, local only)
- status: done
- class: light
- priority: 1
- kind: feature
- deps: —
- area: web/src/replays/ReplayNotes.tsx, web/src/replays/ReplayNotes.test.tsx, web/src/replays/replayNotes.css
- owner: ian-claude-standard
- claimed: 2026-10-17T21:47Z
- pr: #406
- rating: 5/5 clear

What: Carved from T413. Supervisors leave short notes on a replay, shown with author and time; the person sees the same notes (SPEC §17: they see exactly what supervisors see). Local state only, no API.
Interface: `export type ReplayNote = { id: string; author: string; at: string; text: string }`; `export function ReplayNotes(props: { notes: ReplayNote[]; canAdd: boolean; author: string; onAdd: (note: ReplayNote) => void; now?: () => Date })`. Lists notes oldest first ("Author · 21:40", time from `at`); when `canAdd`, a labelled textarea + "Add note" `Button` (disabled on empty/whitespace, trims text, clears after add). Empty: "No notes yet."
Files to read: `web/src/ui/Button.tsx`, `web/src/ui/Card.tsx`, `web/src/ui/SectionHeader.tsx`, `docs/DESIGN.md` (tokens only); CSS vars from `web/src/index.css`.
Acceptance:
- Vitest: notes in order with author + time, add flow calls `onAdd` with trimmed text and the given author, button disabled on blank input, `canAdd=false` hides the form, empty text shown.
- `cd web && npx vitest run src/replays/ReplayNotes` and `scripts/ci.sh` pass.

### T433 — Redesign follow-up: pattern library onto the Fey system
- status: done
- class: light
- priority: 1
- kind: improvement
- deps: T442
- area: web/src/patterns/PatternLibrary.tsx, web/src/patterns/PatternLibrary.css, web/src/patterns/urgencyFilter.css, web/src/patterns/PatternLibrary.test.tsx, web/src/patterns/PatternLibrary.filters.test.tsx, web/src/patterns/PatternLibrary.keyboard.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T22:41Z
- pr: #410
- rating: 5/5 clear
- note: orch: bundle budget raised in #409; merged origin/main into PR, CI re-running with auto-merge

What: The pattern library still uses the pre-redesign tokens (`--panel`, `--border`, `--muted`, `--accent`) and its own boxes. Rebuild its markup on the ui primitives (`Card`, `SectionHeader`, `Row`, `Pill`, `SegmentedControl` for the urgency filter) and the new tokens only. Read only `docs/DESIGN.md`, `web/src/ui/README.md`, `web/src/index.css` and the files in area.
Why: judges click into "consistent with" patterns from the alert; it's the one demo screen that still looks like the old app.
Interface: same exports/props as today; same data from `web/src/patterns/api.ts` and `mockPatterns.ts` (don't edit those).
Acceptance:
- no legacy tokens (`--panel`, `--border`, `--muted`, `--bg`) and no hex/px literals in the two CSS files;
- wording unchanged ("consistent with", never "diagnose");
- existing tests pass (update selectors only, keep behaviour); `cd web && npx vitest run src/patterns && npm run lint`.

### T434 — Redesign follow-up: guided tour card on the Fey system
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: T401
- area: web/src/tour/Tour.tsx, web/src/tour/tour.css, web/src/tour/Tour.test.tsx, web/src/tour/Tour.keyboard.test.tsx
- owner: Max_codex_light
- claimed: 2026-10-17T22:09Z
- pr: #413
- rating: 5/5 clear
- note: orch: bundle budget raised in #409; merged origin/main into PR, CI re-running with auto-merge

What: Restyle the guided-tour card: `--surface-raised`, `--hairline-strong`, `--radius-lg`, the one allowed float shadow (DESIGN.md principle 3), `Button` from `web/src/ui/Button.tsx` for next/back/close. Read only `docs/DESIGN.md`, `web/src/ui/README.md`, `web/src/index.css` and the files in area. Don't touch `steps.ts`.
Why: the tour is the first thing a judge sees on the dashboard; it should match the redesigned screens under it.
Interface: same `Tour` props/exports; behaviour and keyboard handling unchanged.
Acceptance:
- tokens only, no hex/px literals in `tour.css`;
- existing tests pass (selectors only); `cd web && npx vitest run src/tour && npm run lint`.

### T411 — Wording pass: people, not just residents and nurses
- status: done
- class: light
- priority: 1
- kind: improvement
- source: ian
- deps: T408, T409, T410
- area: web/src/alert/, web/src/resident/, web/src/handoff/, web/src/landing/, web/src/wording.test.ts
- owner: ian-claude-heavy-3
- claimed: 2026-10-17T23:28Z
- pr: #428
- note: released by max_API_light: run ended without progress
- rating: 4/5 area list missed the files the new rule forces (about/, ui/DemoBanner, tour/) and the pipeline-written handoff summary; acceptance itself was clear

What: Make shared UI copy role-neutral per SPEC §17: "resident" → "person" (or the person's name), "nurse" only where it's specifically the care-home supervisor, never "patient". Landing page: say it's for anyone, alone or with family, a carer or a care home.
Acceptance: `web/src/wording.test.ts` extended to fail on "patient" and on "nurse" outside an allow-list of care-home-specific strings; all tests pass; `scripts/ci.sh` passes.

### T435 — Redesign follow-up: privacy panel + monitoring toggle on the Fey system
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: T401
- area: web/src/about/PrivacyPanel.tsx, web/src/about/MonitoringToggle.tsx, web/src/about/privacyPanel.css, web/src/about/PrivacyPanel.test.tsx, web/src/about/PrivacyPanel.keyboard.test.tsx, web/src/about/PrivacyPanel.mobile.test.tsx, web/src/about/MonitoringToggle.test.tsx, web/src/about/MonitoringToggle.keyboard.test.tsx
- owner: max_API_standard
- claimed: 2026-10-17T22:29Z
- pr: #420
- note: released by ian-laptop-standard: run ended without progress
- rating: 5/5 clear

What: Move the supervisor-side privacy panel and the pause-monitoring toggle onto the new tokens and primitives (`Card`, `SectionHeader`, `Row` for each "what's stored" line, `Button` for the toggle). Don't edit `monitoringApi.ts` or `ResidentDetail.tsx` (T404 owns it). Read only `docs/DESIGN.md`, `web/src/ui/README.md`, `web/src/index.css` and the files in area.
Why: privacy (skeletons only, no video) is a judging talking point; the panel that says so is still in the old style.
Interface: same exports/props; same text.
Acceptance:
- no legacy tokens (`--muted`, `--panel`, `--border`) and no hex/px literals in `privacyPanel.css`;
- existing tests pass (selectors only, keep the phone-width wrapping assertion meaningful); `cd web && npx vitest run src/about && npm run lint`.

### T436 — Review: camera preview MJPEG readable by any website open on the capture machine
- status: done
- class: light
- priority: 0
- kind: bug
- source: reviewer
- deps: T442
- area: pipeline/src/routine_watch/preview.py, pipeline/tests/test_preview.py
- owner: Max_codex_light
- claimed: 2026-10-17T22:40Z
- pr: #411
- rating: 5/5 clear
- note: orch: bundle budget raised in #409; merged origin/main into PR, CI re-running with auto-merge

What: `preview.py` sends `Access-Control-Allow-Origin: *` on every reply, including `/preview.mjpg`. The loopback/Host checks don't stop a cross-site `fetch('http://127.0.0.1:8765/preview.mjpg')`: the browser runs on this machine (client is loopback) and sends `Host: 127.0.0.1:8765` (passes). So any web page open in that browser can read live camera frames and upload them — raw video leaving the machine, against SPEC §8/§12.
Fix: in `response_for`, take the request's `Origin` header (pass it from `_Handler.do_GET`); if present and its host is not loopback (`is_loopback(urlparse(origin).hostname)`), return 403. Echo the allowed loopback origin in `Access-Control-Allow-Origin` (plus `Vary: Origin`) instead of `*`; send no CORS header when there's no Origin. `<img src>` in `CameraPreview` still works (no CORS needed).
Acceptance:
- Tests in `test_preview.py`: `Origin: https://evil.example` → 403 on `/preview.mjpg` and `/health`; `Origin: http://localhost:5173` → 200 with that origin echoed; no Origin → 200; the existing `== "*"` asserts updated.
- `scripts/ci.sh` passes.

### T437 — Routine builder backend: draft a routine from words or a setup video (Gemini)
- status: done
- class: heavy
- priority: 0
- kind: feature
- source: ian
- deps: —
- area: pipeline/src/routine_watch/routine_builder.py, pipeline/src/routine_watch/api_routines.py, pipeline/src/routine_watch/api.py, pipeline/src/routine_watch/tasks/graph.py, pipeline/tests/test_routine_builder.py, pipeline/tests/fixtures/routine_builder/, .env.example
- owner: ian-claude
- claimed: 2026-10-17T22:03Z
- pr: #417
- rating: 5/5 clear

What: Ian's routine builder (option 1): a person or supervisor creates a new routine either by describing it in words or by uploading **one setup clip** of themselves doing it. Gemini (video understanding) or Claude (text) drafts the steps; code turns the draft into a valid task graph (same schema as `tasks/tea.yaml`) that the task map, error classifier and scoring already read.
Why: shows the approach generalises beyond tea and makes strong use of Gemini (prize) in a 20-second demo shot.
Privacy (SPEC §8, §12): the clip is a **one-time, opt-in setup step**. The request must carry `consent: true`; the video is held in memory (or a temp file deleted in `finally`), sent to Gemini once, never written to `REPLAY_DIR`/`CAMERA_RECORD`/the repo, never logged. Daily monitoring stays skeleton-only. Add one line to SPEC §12 saying exactly this.
Interface:
- `routine_builder.py`: `draft_from_text(description) -> RoutineDraft`, `draft_from_video(bytes, mime) -> RoutineDraft`, `to_task_graph(draft) -> dict` (ids slugged, deps only to earlier-known steps, objects mapped to known detector classes where they match, unknown objects kept and listed as `needs_training`), validated by `tasks/graph.py`'s loader (`parse_task`). Prompt asks for JSON only: steps (label, objects, depends_on, optional, once_only). Both providers behind an interface with a **fake default**; real calls only with `LIVE_API=1` through `api_cache.cached_call`, cheapest models (`GEMINI_MODEL`, `ANTHROPIC_MODEL`). Video: inline for clips ≤20 MB, reject longer than ~60 s or larger.
- **Offline/demo:** with `LIVE_API` unset, return canned drafts from `pipeline/tests/fixtures/routine_builder/` (e.g. "brush teeth", "make toast") picked by keyword, so the demo works on the offline try-out link.
- `api_routines.py`: `POST /routines/draft` (multipart: `description` or `video` + `consent=true`) → `{draft, task_graph, needs_training, warnings}`; `POST /routines` saves a reviewed graph (in-memory + `ROUTINES_DIR` JSON, default `.data/routines/`); `GET /routines` lists built-in + saved; `GET /routines/{id}`.
Acceptance:
- Tests with the fake: text → valid graph; video without `consent` → 400; video bytes never touch disk outside a deleted temp file (privacy test asserts nothing new under the repo/data dirs); invalid LLM JSON → clear 422; unknown objects listed in `needs_training`.
- `scripts/ci.sh` passes without network.

### T413 — Replays library for supervisors and the person
- status: done
- class: standard
- priority: 0
- kind: feature
- source: ian
- deps: T412, T427, T430, T431
- area: web/src/replays/Replays.tsx, web/src/replays/Replays.test.tsx, web/src/replays/replays.css, web/src/mock/replays.ts, web/src/App.tsx
- note: merge conflict fixed: merged origin/main (T446), wired Replay.markers into ReplayPlayer's new markers prop, rebuilt/retested, ci.sh green
- owner: ian-claude-standard
- claimed: 2026-10-17T23:56Z
- pr: #429
- rating: 4/5 clear, but the listed area (Replays.tsx/test/css, mock/replays.ts, App.tsx) didn't fit the entry-point work the spec asked for (a person's detail, an alert's error rows, My routine); ResidentDetail/AlertView/MyRoutine stayed untouched and entry points went into App.tsx's shell instead -- worth naming that tradeoff in the task next time

What: A "Replays" screen where a supervisor can browse a person's sessions that had errors and analyse them, and the person can see (and delete) their own (SPEC §17: they see exactly what supervisors see). Use the mobbin MCP for 2–3 references of video/recording libraries and timeline scrubbers; follow `docs/DESIGN.md` if merged.
Interface:
- List: per person, newest first, each row = date/time, task, error pills (omission/sequence/repeat/…), duration; filter by error type and date range; empty state ("No sessions with errors in the last 30 days").
- Player (extend `ReplayPlayer`): skeleton + object boxes, **timeline with error markers** (click to jump), play/pause/speed (0.5×/1×/2×), step labels as it plays, optional ghost overlay of the person's normal session, frame-by-frame with arrow keys.
- Supervisor notes on a replay (local/mock, shown with author + time); person view shows "Delete this replay".
- Entry points: from a person's detail ("Replays"), from an alert's error rows, and from "My routine" for the person.
- Offline/mock fallback in `web/src/mock/replays.ts`.
Acceptance: Vitest for list/filter/empty, marker jump, speed, delete, notes; keyboard operable; screenshot in PR; `scripts/ci.sh` passes.

### T432 — Task map as a Postman Flows–style node graph
- status: done
- class: standard
- priority: 0
- kind: improvement
- source: ian
- deps: T406
- area: web/src/live/TaskMap.tsx, web/src/live/TaskMap.test.tsx, web/src/live/taskMap.css, web/src/live/TaskMapLegend.tsx, web/src/live/TaskMapLegend.test.tsx
- owner: ian-claude
- claimed: 2026-10-18T00:08Z
- pr: #431
- rating: 4/5 the task says deps already come over /ws/live; they did not, so the PR had to extend session_start (contracts + live.py + live_camera.py). It also assumes the map has room for a left-to-right flow: the live screen's column is ~23 rem, four tea levels need ~49 rem
- note: conflict fixed on #431 (f98590d); CI running, auto-merge on

What: Ian wants the task map to look like **Postman Flows** (node-graph canvas). Use the mobbin MCP (`search_screens` / `search_flows` "Postman Flows") to study 2–3 references first and name them in the PR. Render the task graph (steps + deps from the task YAML, already sent over /ws/live) as rounded node cards on a dotted canvas, connected by smooth curved edges with small ports; parallel branches side by side (e.g. fill kettle ∥ get cup), optional steps dashed. Live state on each node: pending (muted), done (green check), current (glow/pulse), error (red, with the error type pill: omission/sequence/repeat/substitution), unclear (grey). Edges into an errored step turn red/amber. Fits the Fey-style tokens from `docs/DESIGN.md`.
Why: the task map is the centrepiece of the live demo shot; a flow canvas makes "dependencies, not a fixed order" obvious at a glance.
Interface: dependency-free SVG/HTML (no graph libraries); a simple layered layout (topological levels left→right) computed from deps; same props and data as today's TaskMap; keyboard/screen-reader: nodes are a list with state in their accessible names.
Acceptance: renders tea and meds graphs without overlaps; state changes animate; existing TaskMap tests pass (selectors only) + a layout test (parallel steps share a level); screenshot in PR; `cd web && npm test && npm run build`.

### T438 — Routine builder UI: describe it or upload a setup clip → editable task map → save
- status: done
- class: standard
- priority: 0
- kind: feature
- source: ian
- deps: —
- area: web/src/routines/, web/src/mock/routines.ts, web/src/App.tsx
- owner: —
- claimed: —
- pr: #414
- rating: 4/5 clear, though the two task-map interpretations (reorder-the-list vs edit-deps) under 'reorder deps' were ambiguous; implemented both
- note: merge conflict with main on PR #414: check out its branch, merge origin/main, fix, push

What: The front end for T437, built in parallel against the API shape in T437's Interface with a mock (`web/src/mock/routines.ts`) so it doesn't wait for T437. Follow `docs/DESIGN.md`; check 2–3 Mobbin references for "create from upload / AI builder" flows.
Interface (`web/src/routines/`):
- "New routine" entry from the shell (both roles).
- Two tabs: **Describe it** (textarea + examples) and **From a video** (file picker, max ~60 s; a consent checkbox that must be ticked: "This clip is sent once to Google Gemini to draft the steps. It is not stored. Day-to-day monitoring never sends video."). Progress state while drafting.
- Result: the drafted routine shown as a task map (reuse `web/src/live/TaskMap`), plus an editable step list (rename, reorder deps, toggle optional, delete, add) that updates the map live; a "needs training" note listing objects the detector doesn't know yet; **Save routine**. Saved routines appear in a "Routines" list (tea, meds, plus saved).
- Offline: the mock returns a believable draft ("Brush teeth") so the flow demos with no keys.
Acceptance: Vitest for both tabs (consent required before upload; text submit; edit updates preview; save adds to list); keyboard operable; screenshot in PR; `cd web && npm test && npm run build`.

### T439 — Bug: integration check failing on main
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
- note: orch: integration PASS on main per TESTREPORT 2026-10-17T23:05Z (dev.sh up OK); closed as transient, tester will refile if it recurs

What: `scripts/integration.sh` (stack up offline → API endpoints → dashboard render → live WebSocket) fails on main @ 24033f5:
  FAIL dev.sh up: 
    api log: INFO:     Started server process [2099018] INFO:     Waiting for application startup. INFO:     Application startup complete. INFO:     Uvicorn running on http://0.0.0.0:8100 (Press CTRL+C to quit) 
Interface: reproduce with `scripts/integration.sh`; logs in `.dev/api.log` / `.dev/web.log`. Fix the cause (not the check) unless the check itself is wrong.
Acceptance:
- `scripts/integration.sh` prints OK; `scripts/ci.sh` passes.

### T440 — Bug: flaky unit test test_frames_in_thread_hands_over_every_record_in_order
- status: done
- class: light
- priority: 0
- kind: bug
- deps: —
- area: pipeline/tests/test_api_live_camera.py
- owner: ian-claude-heavy-3
- claimed: 2026-10-17T22:06Z
- pr: #419
- source: orchestrator
- rating: 5/5 clear - the diagnosis, the exact call to make and the 20x acceptance loop were all in the task; only extra was that main was separately red on the bundle budget (T442/T421), so the branch needed rebasing onto e34c2a5 before ci.sh could pass

What: Failed main CI run 39073146552 (@24033f5, unrelated .gitattributes commit). `frames_in_thread` drops the newest record once `max_pending` (default `MAX_PENDING_FRAMES = 30`, pipeline/src/routine_watch/live_camera.py:94) are waiting, and FakeCamera's clip has ~43 frames, so when the capture thread outruns the event loop on a loaded runner, frames get dropped and `drain(camera) == camera.frames` fails. That's a timing race in the test, not a product bug.
Interface: test-only change. In `test_frames_in_thread_hands_over_every_record_in_order` (line ~298), call `drain(camera, max_pending=len(camera.frames) + 1)` so nothing can be dropped. Check the other tests in the file that compare a full list (not `stop_after`/`max_pending=0`) for the same race and fix them the same way. Do not change live_camera.py.
Acceptance:
- `cd pipeline && python -m pytest tests/test_api_live_camera.py -q` passes; run the file 20 times in a loop (`for i in $(seq 20); do python -m pytest tests/test_api_live_camera.py -q -x || break; done`) with no failure.
- `scripts/ci.sh` passes.

### T441 — Review: deleteReplay reports success when the API refuses the delete
- status: done
- class: light
- priority: 1
- kind: bug
- source: reviewer
- deps: —
- area: web/src/replays/api.ts, web/src/replays/api.test.ts
- owner: max_API_standard-2
- claimed: 2026-10-18T00:20Z
- pr: #433
- note: released by max_API_light: run ended without progress
- rating: 5/5 clear

What: In `web/src/replays/api.ts`, `deleteReplay` (and the two fetches) fall back to the offline mock library on *any* non-ok response, not just a network error. A 500/403 from `DELETE /replays/{id}` on a mock-library id therefore resolves and hides the replay locally while the server still stores it (privacy: the person thinks their replay is gone, SPEC §17). A 404 for a real replay likewise turns into "Replay not found" only by accident.
Interface: keep the signatures. Fall back to the offline library only inside `catch` (fetch threw = API unreachable). If the API answered: `ok` → success; `404` → throw `Error('Replay not found')`; anything else → throw `Error('Could not delete replay')` and do NOT add the id to `deleted`. Apply the same rule to `fetchPersonReplays`/`fetchReplay` (non-ok response → throw, don't silently show mock data).
Acceptance:
- tests in `web/src/replays/api.test.ts`: DELETE returning 500 rejects and a following `fetchPersonReplays` (fetch throwing) still lists the replay; fetch throwing still deletes offline.
- `cd web && npm test -- replays` and `scripts/ci.sh` pass.

### T442 — Bug: main CI red — first-load JS 336 bytes over bundle budget
- status: done
- class: light
- priority: 0
- kind: bug
- source: orchestrator
- deps: —
- area: web/scripts/check-bundle.mjs, web/README.md
- owner: ian-claude
- claimed: 2026-10-17T22:48Z
- pr: #422
- note: main green again: #418 raised the budget to 96,000 and merged; #422 recorded the measured 95,204/96,000 total and rewrapped the README note
- rating: 4/5 the note's premise was stale: #418 was already conflict-free and auto-merged mid-CI, and main's budget was 95_200 (T421) not 92_200, so the numbers in the task had to be re-measured

What: `main` CI fails at `npm run check:bundle`: first-load JS is 92536 bytes gzipped vs `BUDGET_BYTES = 92_200` (runs 39073873088, 39074550159). No single merge caused it; the redesign (T403/T407), person view (T409) and replays (T430/T431) each added always-on code. Open PRs (#409, #410) fail on this too.
Interface: in `web/scripts/check-bundle.mjs` raise `BUDGET_BYTES` to `96_000` and update the comment above it to say why (redesign shell + person view + replays are always-on screens added 2026-10-17; measured 92536 bytes). Add one line to the budget section of `web/README.md` with the new number and reason. Touch no other file.
Acceptance:
- `cd web && npm run build && npm run check:bundle` passes.
- `scripts/ci.sh` passes.

### T443 — Review: Routines screen crashes on the live API (GET /routines has no task_graph)
- status: done
- class: light
- priority: 0
- kind: bug
- source: reviewer
- deps: —
- area: web/src/routines/types.ts, web/src/routines/RoutinesScreen.tsx, web/src/routines/RoutinesScreen.test.tsx, web/src/mock/routines.ts
- owner: ian-claude-heavy-3
- claimed: 2026-10-17T22:58Z
- pr: #423
- note: released by ian-laptop-standard: run ended without progress
- rating: 4/5 clear on the fix; it didn't mention that saveRoutine's offline row and api.test.ts's whole-object assertion (T444's area) must change too, since POST /routines answers with detail() = summary + task_graph

What: `GET /routines` returns `Routine.summary()` (pipeline/src/routine_watch/routine_builder.py ~line 979): `id, title, task_id, built_in, source, step_count, needs_training` and NO `task_graph`. `web/src/routines/RoutinesScreen.tsx:77` reads `routine.task_graph.steps.length`, so with the API up the screen throws a TypeError (it only works on the offline mock, which includes `task_graph`).
Interface: in `types.ts` add a `RoutineSummary` type matching `summary()`; `fetchRoutines()` in api.ts returns `RoutineSummary[]` (change only its type annotation; its fallback logic is T444). `RoutinesScreen.tsx` renders `${routine.step_count} steps`. Make `mockBuiltInRoutines` and the localStorage fallback rows in `mock/routines.ts` carry `step_count` and the other summary fields. Do not change the pipeline.
Acceptance:
- RoutinesScreen test feeds a fetch response shaped exactly like `summary()` (no task_graph) and asserts "N steps" renders.
- `scripts/ci.sh` passes.

### T444 — Review: routine builder shows a canned draft / fake save when the API refuses
- status: done
- class: light
- priority: 1
- kind: bug
- source: reviewer
- deps: T443
- area: web/src/routines/api.ts, web/src/routines/api.test.ts, web/src/routines/RoutineBuilder.tsx, web/src/routines/RoutineBuilder.test.tsx
- owner: ian-claude-standard-4
- claimed: 2026-10-17T23:40Z
- pr: #427
- note: released by max_API_light: run ended without progress
- rating: 5/5 clear

What: `web/src/routines/api.ts` falls back to the mock on any non-ok response (same pattern as T441). A person's clip refused with 400/413/422/502 by `POST /routines/draft` comes back as a canned "make tea" draft as if Gemini had read their clip, and a `POST /routines` 422 (bad graph) / 409 (built-in id or library full) is silently "saved" to localStorage while the server never kept it.
Interface: fall back to mocks/localStorage only inside `catch` (fetch threw = API unreachable). If the API answered non-ok, throw `Error(detail)` using the JSON `detail` string (FastAPI `{detail: string}`), else a generic message. `RoutineBuilder.tsx` shows that message with the existing error UI from web/src/ui/ and keeps the user's draft/graph on screen.
Acceptance:
- api.test.ts: 413 on draftFromVideo rejects with the detail; 409 on saveRoutine rejects and writes nothing to localStorage; fetch throwing still returns the mock.
- `scripts/ci.sh` passes.

### T445 — Bug: flaky unit test MyRoutine "says nobody else can see this…" (lazy section not loaded within findBy's 1 s)
- status: done
- class: light
- priority: 0
- kind: bug
- deps: —
- area: web/src/people/MyRoutine.test.tsx
- source: tester
- owner: ian-claude-standard-4
- claimed: 2026-10-17T23:26Z
- note: released by max_API_standard: run ended without progress
- pr: #424
- rating: 5/5 clear

What: `scripts/ci.sh` on main @64ab65c failed in web tests: `src/people/MyRoutine.test.tsx > MyRoutine > says nobody else can see this when the person is watching themselves` → `Unable to find role="heading" and name "How this week looks"`; DOM still shows "Loading your week…". `MyRoutine.tsx` loads `RoutineSections` with `React.lazy` (line ~25), and the first test in the file pays the dynamic-import/transform cost, which exceeds `findByRole`'s default 1000 ms timeout on a loaded box. Repro: `cd web && for i in 1 2 3; do npx vitest run src/people/MyRoutine.test.tsx | grep "Tests "; done` failed 1 of 3 runs in isolation (plus the full ci.sh run). Expected: always passes. It's a test timing race, not a product bug.
Interface: test-only change. In `renderRoutine` in `MyRoutine.test.tsx`, wait longer (e.g. `findByRole(..., {}, { timeout: 5000 })`) or preload the lazy module in a `beforeAll` (`await import('../person/routine/RoutineSections.tsx')`). Do not change `MyRoutine.tsx`. Check other tests that render lazy screens with plain `findBy*` for the same race.
Acceptance:
- `cd web && for i in $(seq 20); do npx vitest run src/people/MyRoutine.test.tsx || break; done` with no failure.
- `scripts/ci.sh` passes.

### T446 — Replay player: error markers on the timeline, speed, arrow-key stepping
- status: done
- class: light
- priority: 0
- kind: feature
- source: ian
- deps: —
- area: web/src/evidence/ReplayPlayer.tsx, web/src/evidence/ReplayPlayer.markers.test.tsx, web/src/evidence/evidence.css
- owner: ian-claude
- claimed: 2026-10-17T23:20Z
- pr: #425
- rating: 4/5 clear on the interface; it didn't say the speed group can't use role=group (an existing unqualified getByRole('group') test pins the player) or that the eager first-load budget has ~100 B of headroom, so the feature needs a budget bump outside the area

What: Carved from T413 (Ian's replays library). Extend the existing skeleton `ReplayPlayer` so a supervisor can analyse a replay: error markers on the timeline that jump to the moment, a 0.5×/1×/2× speed control, and frame-by-frame stepping with arrow keys. Read only `web/src/evidence/ReplayPlayer.tsx`, `web/src/evidence/ReplayPlayer.test.tsx` (style reference) and `web/src/ui/Button.tsx`.
Interface: add optional props, existing callers unchanged: `markers?: { t: number; label: string; kind?: string }[]` (t in seconds, same clock as `frames[i].t`). Render each marker as a `<button>` positioned along the timeline (left = t / last frame t), accessible name `"Jump to <label> at m:ss"`, class `replay-player__marker` (+ `replay-player__marker--<kind>` if given; colours from existing tokens in evidence.css). Click → position = first frame with `t >= marker.t`, playback pauses. Speed: a labelled group of three `Button`s ("0.5×", "1×", "2×", `aria-pressed` on the active one, default 1×) multiplying the frame rate. On the player group: ArrowRight/ArrowLeft step one frame and pause; Space still plays/pauses. Mention arrow keys in the group `aria-label`.
Acceptance:
- New `ReplayPlayer.markers.test.tsx` (Vitest + Testing Library, fake timers): markers render with accessible names; clicking one moves the "Replay position" slider to the right frame; 2× advances twice as many frames as 1× over the same time; arrow keys step and pause; no `markers` prop → no marker buttons.
- Existing `ReplayPlayer*.test.tsx` pass unchanged.
- `cd web && npx vitest run src/evidence` and `scripts/ci.sh` pass.

### T447 — DEMO.md: click path for the new screens (people, My routine, routine builder, replays)
- status: done
- class: light
- priority: 1
- kind: docs
- deps: —
- area: docs/DEMO.md
- owner: ian-claude-standard
- claimed: 2026-10-17T23:37Z
- pr: #426
- source: proposed
- note: released by max_API_standard-2: run ended without progress
- rating: 5/5 clear

Why: Ian films the demo at 03:00 UTC from docs/DEMO.md, and its click path predates the people/supervisor roles, My routine, the routine builder and the replays screen, so he'd have no run order for them.
What: Extend the "Click path" section of `docs/DEMO.md` with short steps (same bullet style) for: "People I support" + add a person, the *Myself* view ("My routine": how this week looks, privacy card), the Routines screen + routine builder (describe it → editable task map → save; note it uses a canned fake draft unless `LIVE_API=1`), and the replays library if a nav entry for it exists on main (otherwise skip it). Keep the existing SPEC §10 order; put the new steps after "Shift handoff" and before "Close" as an optional segment.
Interface: read only `docs/DEMO.md`, `web/src/App.tsx` (nav labels), `web/src/people/PeopleISupport.tsx`, `web/src/people/MyRoutine.tsx`, `web/src/routines/RoutinesScreen.tsx`, `web/src/routines/RoutineBuilder.tsx` to get the exact button/heading text. Don't change code.
Acceptance:
- Every button/heading named in the new steps exists verbatim in those files.
- Wording: "flags a change for review", never "diagnoses".
- `scripts/ci.sh` passes.
