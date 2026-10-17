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
