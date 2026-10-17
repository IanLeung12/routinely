# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: ce4748f

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
- status: claimed
- class: heavy
- priority: 0
- deps: T001
- area: contracts/, pipeline/routine_watch/contracts.py, web/src/contracts.ts
- owner: ian-claude
- claimed: 2026-10-17T03:22Z
- pr: —

What: Define the data that flows between stages (SPEC §6, §7, §16): CaptureFrame (the single per-frame JSONL record: timestamp, pose skeleton keypoints, MediaPipe hand landmarks, object boxes; used by live camera, fallback video, tests and scenarios), ObjectDetection, StepEvent (step id, objects, t_start, t_end, confidence, source rule|verifier, unclear flag), TaskError (type ∈ omission|sequence|perseveration|substitution|hesitation|abandonment, step, timestamps, evidence refs, self_corrected), Session (resident, task, start/end, assisted flag, score), Alert (resident, sessions, errors, baseline comparison, summary, suggested checks, feedback).
Interface: JSON Schema files in `contracts/`, matching pydantic models and TS types. No raw frames anywhere.
Acceptance:
- Round-trip test: pydantic model → JSON → validates against schema, for each type.
- `web` type-checks against the TS types.
- A sample `contracts/examples/capture.jsonl` (a few frames) validates against the CaptureFrame schema.

### T003 — Tea task graph definition
- status: todo
- class: standard
- priority: 1
- deps: T001
- area: pipeline/routine_watch/tasks/, pipeline/tests/
- owner: —
- claimed: —
- pr: —

What: The "make tea" dependency graph from SPEC §7 as data plus a loader. Steps: fill kettle, boil, get cup, teabag in cup, pour water, (optional) milk, (optional) sugar, stir, remove teabag. Dependencies, allowed objects per step (spoon|teaspoon), once-only flags, optional flags.
Interface: `tasks/tea.yaml`; `load_task(name) -> TaskGraph` with `deps(step)`, `allowed_objects(step)`, `is_optional(step)`, `valid_orders()` helper for tests.
Acceptance:
- Tests: "fill kettle" and "get cup" in either order are both valid; "pour" requires "teabag in cup"; optional steps can be skipped.

### T004 — Synthetic care-record generator
- status: claimed
- class: light
- priority: 2
- deps: T001
- area: pipeline/routine_watch/synth/care_records.py, pipeline/tests/test_care_records.py
- owner: ian-claude-light
- claimed: 2026-10-17T03:22Z
- pr: —

What: Generate fake care-record context for demo residents: medication changes, temperature readings, daily fluid intake. Read only the files in `area` and `pipeline/pyproject.toml`.
Interface: `generate_care_records(resident_id: str, days: int = 14, seed: int = 0, scenario: str = "normal") -> list[dict]`. Each dict: `{"resident_id", "ts" (ISO), "kind": "med_change"|"temperature"|"fluid_intake", "value", "note"}`. Scenario `"spike"`: new antibiotic 2 days before the end, temperature rises to ~38.2 °C in the last day, fluid intake drops. `"normal"`: no med changes, temp 36.4–37.0, fluids 1200–1800 ml/day.
Acceptance:
- Deterministic for a given seed.
- Tests check both scenarios' properties above.
- `cd pipeline && uv run pytest tests/test_care_records.py -q` passes.

### T005 — Scenario replay harness (e2e)
- status: todo
- class: heavy
- priority: 1
- deps: T002, T003
- area: scripts/e2e.sh, tests/scenarios/, pipeline/routine_watch/replay.py, pipeline/tests/test_replay.py
- owner: —
- claimed: —
- pr: —

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
