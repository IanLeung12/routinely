# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: 091f283

## Tasks

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
- status: in-review
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
- status: todo
- class: standard
- priority: 1
- deps: T001
- area: scripts/dev.sh, README.md (Run section)
- owner: —
- claimed: —
- pr: —

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
- status: todo
- class: heavy
- priority: 1
- deps: T002, T003
- area: pipeline/src/routine_watch/errors.py, pipeline/tests/test_errors.py
- owner: —
- claimed: —
- pr: —

What: Turn one session's step events plus the task graph into TaskErrors for the graph-based types in SPEC §7: omission, sequence, perseveration, substitution, abandonment, plus self-corrected slips. Hesitation is T014 (needs a baseline); do not implement it here.
Interface: `classify_errors(events: list[StepEvent], graph: TaskGraph, *, session_id: str, ended: bool = True, abandon_after_s: float = 120.0, self_correct_window_s: float = 15.0) -> list[TaskError]` in `errors.py` (keep `ERROR_TYPES`). Consumes `routine_watch.contracts.StepEvent/TaskError/EvidenceRef` and `routine_watch.tasks.TaskGraph` (`deps`, `allowed_objects`, `is_optional`, `is_once_only`). Events with `unclear=True` are ignored. Each error's `evidence` points at the StepEvent(s) involved. Deterministic `error_id`s.
Acceptance:
- Tests: valid alternative orders and skipped optional steps → no errors; skip teabag then pour → omission on `teabag_in_cup`; pour twice with steps between → perseveration; stir with a non-allowed object → substitution; a step before its dep with the dep done later → sequence; dep done within `self_correct_window_s` → `self_corrected=True`; gap > `abandon_after_s` with required steps left → abandonment; unclear events never produce errors.
- `cd pipeline && uv run pytest tests/test_errors.py -q` and `scripts/ci.sh` pass. Once T005 is merged, the `tea_skip_teabag_pour_twice` scenario must be driven by this classifier in a follow-up (note it in the PR).

### T011 — Step recogniser state rules
- status: todo
- class: heavy
- priority: 1
- deps: T002, T003
- area: pipeline/src/routine_watch/recogniser.py, pipeline/tests/test_recogniser.py, pipeline/tests/fixtures/recogniser/
- owner: —
- claimed: —
- pr: —

What: State rules over hand–object interactions that turn a stream of CaptureFrames into timestamped StepEvents with confidence (SPEC §6.2, §16 "Hands"). No verifier calls here: events below `MIN_STEP_CONFIDENCE` are emitted with `unclear=True` and a hook left for the Gemini verifier (later task).
Interface: `recognise(frames: Iterable[CaptureFrame], graph: TaskGraph, *, session_id: str) -> list[StepEvent]` (`source="rule"`). Rules use hand landmarks near object boxes (e.g. hand overlaps teabag box then teabag box overlaps cup box → `teabag_in_cup`; kettle box tilted/over cup → `pour`). Keep thresholds as module constants.
Acceptance:
- Hand-built small JSONL fixtures (generated by a helper in the test, not raw video) for at least: fill kettle, teabag in cup, pour, stir; each recognised with correct ordering and t_start ≤ t_end.
- Ambiguous fixture → event with `unclear=True`, never dropped silently.
- `cd pipeline && uv run pytest tests/test_recogniser.py -q` and `scripts/ci.sh` pass.

### T012 — Demo residents API
- status: todo
- class: standard
- priority: 1
- deps: T007, T008, T009, T004
- area: pipeline/src/routine_watch/api.py, pipeline/src/routine_watch/demo.py, pipeline/tests/test_api_residents.py
- owner: —
- claimed: —
- pr: —

What: Serve the 3–5 synthetic demo residents (SPEC §8: most normal, one spike, one drift; demo resident "Mrs. K" is the spike) to the dashboard, scored and flagged with the existing pure functions. Offline, no DB yet.
Interface: `demo.py`: `demo_residents() -> list[dict]` built from `synth.history.generate_history`, `synth.care_records.generate_care_records`, `scoring.session_score`, `change_detection.build_baseline/flag_change`. Routes: `GET /residents` → `[{id, name, room, status: "normal"|"watch"|"flagged", scores: [{ts, score}]}]`; `GET /residents/{id}` → that plus `sessions`, `care_records`, `baseline: {mean, std, threshold}`; 404 for unknown id. Status: flagged if `flag_change`, watch if the latest session is above threshold, else normal.
Acceptance:
- Tests via FastAPI TestClient: spike resident is `flagged`, normal residents `normal`, 404 works, output deterministic.
- `cd pipeline && uv run pytest tests/test_api_residents.py -q` and `scripts/ci.sh` pass.

### T013 — Dashboard unit overview screen
- status: todo
- class: standard
- priority: 1
- deps: T001
- area: web/src/ (new files under web/src/overview/ and web/src/mock/, plus App.tsx wiring)
- owner: —
- claimed: —
- pr: —

What: SPEC §9 screen 1: resident list with a status chip (normal / watch / flagged) and a sparkline of each resident's error score. Visual first; a nurse should read it in 10 s.
Interface: `type ResidentSummary = {id: string; name: string; room: string; status: "normal"|"watch"|"flagged"; scores: {ts: string; score: number}[]}` (same shape as T012's `GET /residents`). `fetchResidents()` calls `${API_URL}/residents` and falls back to `web/src/mock/residents.ts` when the API is unreachable. Sparkline in plain SVG (no chart library). Flagged residents sort first.
Acceptance:
- Vitest + Testing Library: renders all mock residents, chip text/colour per status, flagged first, fallback to mock on fetch failure.
- `cd web && npm test && npm run build` and `scripts/ci.sh` pass.

### T014 — Hesitation detector
- status: in-review
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
- status: in-review
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
- status: in-review
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
