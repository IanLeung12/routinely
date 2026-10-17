# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: 95a0556

## Tasks

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
- status: claimed
- class: standard
- priority: 1
- deps: T011, T020
- area: pipeline/src/routine_watch/replay.py, pipeline/tests/test_replay.py, tests/scenarios/README.md, tests/scenarios/tea_no_kettle/
- owner: ian-claude-standard
- claimed: 2026-10-17T04:55Z
- pr: —

What: Review finding on PR #20/#21: `replay.steps_from_frames` is still the STUB recogniser, so `frames.jsonl` scenarios never exercise `recogniser.recognise` (T011). Replace the stub with the real recogniser and delete the "Stubs" section of the scenarios README.
Interface: `replay.run` calls `recognise(frames, graph, session_id=...)` for `frames.jsonl` scenarios; `steps.jsonl` scenarios unchanged. Remove `STUB_CONFIDENCE`, `touched_objects`, `steps_from_frames` and the stub helpers. Public CLI/output format unchanged.
Acceptance:
- `tea_no_kettle` passes through the real recogniser (fix its `frames.jsonl` only if the recogniser's rules genuinely need different frames; say so in the PR). No "STUB" left in replay.py or README.
- `cd pipeline && uv run pytest tests/test_replay.py -q`, `scripts/e2e.sh` and `scripts/ci.sh` pass.

### T027 — Web alerts API client + mock
- status: claimed
- class: light
- priority: 1
- deps: —
- area: web/src/alert/api.ts, web/src/alert/api.test.ts, web/src/mock/alerts.ts
- owner: max-codex-light-1
- claimed: 2026-10-17T05:05Z
- pr: —

What: Dashboard client for the alerts API (already live on the backend). Read only the files in `area`, `web/src/overview/api.ts` (copy its fallback pattern), `web/src/config.ts`, `web/src/contracts.ts` (type `Alert`, `FeedbackVerdict`; do not edit it), `web/src/overview/UnitOverview.test.tsx` (test style) and `web/package.json`. Do not edit any other file.
Interface: `fetchAlerts(): Promise<Alert[]>` → `GET ${apiUrl}/alerts`; `fetchAlert(id): Promise<Alert | null>` → `GET ${apiUrl}/alerts/{id}` (404 → null); `postFeedback(id: string, verdict: FeedbackVerdict, note?: string): Promise<Alert>` → `POST ${apiUrl}/alerts/{id}/feedback` JSON `{verdict, note}`. GETs fall back to `mockAlerts` on network error / non-ok; a failed POST returns the mock alert with `feedback = {verdict, by: "nurse", at: new Date().toISOString(), note}` set locally. `mockAlerts`: one `change_flag` alert for resident `mrs-k` with two errors (`omission` of `teabag_in_cup` at t=42, `perseveration` of `pour` at t=75), baseline `{task_id:"make_tea", metric:"error_score", observed:5, baseline_mean:0.2, baseline_sd:0.4, baseline_days:14, threshold:1.2}`, all four suggested checks, a summary starting "Flagged for review:". Never the word "diagnose".
Acceptance:
- Vitest with `vi.stubGlobal('fetch', ...)`: success paths, fallback on rejection, 404 → null, POST body shape, failed POST sets feedback locally.
- `cd web && npm test && npm run build` and `scripts/ci.sh` pass.

### T028 — Alert / evidence view screen
- status: todo
- class: standard
- priority: 1
- deps: T027
- area: web/src/alert/AlertView.tsx, web/src/alert/AlertView.test.tsx, web/src/alert/ErrorList.tsx, web/src/alert/alert.css
- owner: —
- claimed: —
- pr: —

What: SPEC §9 screen 4, readable in 10 seconds: plain-language summary on top, baseline comparison ("5.0 vs 0.2 normal over 14 days"), error list with m:ss timestamps and nurse-readable phrases (same wording as `pipeline/src/routine_watch/explain.py`), `SuggestedChecks`, and `FeedbackButtons` wired to `postFeedback`; after feedback show the updated threshold. Each error row has an `onOpenEvidence(error)` callback (replay view comes later). Don't touch App.tsx (T022 owns it); a later task wires navigation.
Interface: `AlertView({alertId, onBack, onOpenEvidence?})` loads via `fetchAlert` (mock fallback); `ErrorList({errors, onOpen})`.
Acceptance:
- Vitest: renders summary, comparison, both mock errors with "0:42"/"1:15", four checks; clicking "False alarm" calls postFeedback and shows the new threshold; no "diagnos" in rendered text.
- `cd web && npm test && npm run build` and `scripts/ci.sh` pass.

### T029 — Live session WebSocket (scenario-driven)
- status: claimed
- class: heavy
- priority: 1
- deps: T020
- area: pipeline/src/routine_watch/live.py, pipeline/src/routine_watch/api.py (add the route only), pipeline/tests/test_live.py
- owner: ian-claude
- claimed: 2026-10-17T05:04Z
- pr: —

What: SPEC §16 B and §10 fallback: one WebSocket carries the live view. For now it plays a recorded scenario through the pipeline in (sped-up) real time, which is also the demo fallback; the camera source plugs into the same generator later.
Interface: `live.session_messages(scenario_dir, speed=1.0) -> AsyncIterator[dict]` yielding `{"type":"frame","frame":CaptureFrame}` (downsampled to ≤10 fps), `{"type":"step","event":StepEvent}`, `{"type":"step_state","states":{step_id: "pending"|"done"|"omission"|"repeat"|"sequence"}}` (matches web `TaskMap`), `{"type":"error","error":TaskError}`, `{"type":"session_end","score":float,"flag":bool,"alert_id":str|None}`. Errors are classified incrementally (`classify_errors(..., ended=False)` per new event, `ended=True` at the end), deduplicated by error_id. Route `WS /ws/live?scenario=<name>&speed=<x>`; unknown scenario → close code 4404. For `steps.jsonl` scenarios, skip frame messages.
Acceptance:
- Tests with FastAPI TestClient websocket and speed=1000: `tea_skip_teabag_pour_twice` yields omission + perseveration errors, step_state shows teabag_in_cup=omission and pour=repeat, session_end flag true; `tea_normal` yields no errors; unknown scenario → 4404.
- `cd pipeline && uv run pytest tests/test_live.py -q` and `scripts/ci.sh` pass.

### T030 — Gemini step verifier behind an interface
- status: todo
- class: standard
- priority: 2
- deps: T031
- area: pipeline/src/routine_watch/verifier.py, pipeline/tests/test_verifier.py, pipeline/pyproject.toml
- owner: —
- claimed: —
- pr: —

What: SPEC §6.2 and §16 A: when `recogniser.needs_verifier(event)` is true, ask a vision LLM which step happened. Fake by default; Gemini only with `LIVE_API=1`, via `api_cache`, model from `GEMINI_MODEL` (default flash-lite). Images are in-memory JPEG bytes from a ring buffer, never written to disk (the cache stores only the JSON response, keyed by a hash).
Interface: `VerifierResult(step_id: str | None, objects: list[str], confidence: float)`; `class Verifier(Protocol): def verify(self, images: list[bytes], candidates: list[str], timeout_s: float = 3.0) -> VerifierResult | None` (None = unclear); `FakeVerifier(answers: dict | None)`; `GeminiVerifier` (REST via httpx or `google-genai`, max 8 images); `get_verifier()` returns Fake unless `LIVE_API=1` and `GEMINI_API_KEY` set; `resolve(event, verifier, images, candidates) -> StepEvent` sets `source="verifier"` on a confident answer, `unclear=True` on None/timeout/exception.
Acceptance:
- Tests use FakeVerifier and a stubbed HTTP transport only; no network. Timeout/exception → unclear; answer outside `candidates` → unclear.
- `cd pipeline && uv run pytest tests/test_verifier.py -q` and `scripts/ci.sh` pass.

### T031 — On-disk API response cache + LIVE_API guard
- status: todo
- class: light
- priority: 1
- deps: —
- area: pipeline/src/routine_watch/api_cache.py, pipeline/tests/test_api_cache.py
- owner: —
- claimed: —
- pr: —

What: Every paid API call (Gemini, Claude) must go through an on-disk cache under `.cache/api/` and only run when `LIVE_API=1`. Read only the files in `area`, `pipeline/src/routine_watch/hesitation.py` (code style) and `pipeline/pyproject.toml`. Standard library only.
Interface: `class LiveApiDisabled(RuntimeError)`; `live_api_enabled() -> bool` (env `LIVE_API == "1"`); `request_key(namespace: str, request: dict) -> str` = sha256 hex of `namespace + json.dumps(request, sort_keys=True, separators=(",", ":"))` (bytes values must be pre-hashed by the caller); `cached_call(namespace, request, fn: Callable[[], dict], cache_dir: Path | None = None) -> dict`: returns the cached JSON at `<cache_dir>/<namespace>/<key>.json` if present; else if not live raises `LiveApiDisabled`; else calls `fn()`, writes the result atomically (tmp file + rename) and returns it. Default `cache_dir` = env `API_CACHE_DIR` or `<repo root>/.cache/api`.
Acceptance:
- Tests (use `tmp_path`, `monkeypatch`): cache hit never calls fn even with LIVE_API=0; miss with LIVE_API=0 raises; miss with LIVE_API=1 calls once then hits; key stable under dict key order; different namespaces don't collide.
- `cd pipeline && uv run pytest tests/test_api_cache.py -q` and `scripts/ci.sh` pass.

### T032 — Claude alert summariser behind the Explainer interface
- status: todo
- class: standard
- priority: 2
- deps: T031
- area: pipeline/src/routine_watch/explain_claude.py, pipeline/tests/test_explain_claude.py, pipeline/pyproject.toml
- owner: —
- claimed: —
- pr: —

What: SPEC §6.4: Claude writes the plain-language summary from the detected evidence only. Template stays the default and the fallback.
Interface: `ClaudeExplainer(client=None, model=env ANTHROPIC_MODEL or "claude-haiku-4-5")` implementing `explain.Explainer.summarise(errors, baseline, context)`; calls go through `api_cache.cached_call("anthropic", ...)`; prompt forbids diagnosis, speculation and facts not in input. Output guard: if the reply contains "diagnos" (any case), any number or m:ss not present in the template output/inputs, or exceeds 3 sentences, return `TemplateExplainer` output instead. Any exception/timeout → template. `get_explainer()` returns Template unless `LIVE_API=1` and `ANTHROPIC_API_KEY` set.
Acceptance:
- Tests with an injected fake client only: good reply used; "diagnosed" reply rejected; invented timestamp rejected; exception → template; `get_explainer()` default is Template.
- `cd pipeline && uv run pytest tests/test_explain_claude.py -q` and `scripts/ci.sh` pass.

### T033 — Slow-drift trend detector
- status: todo
- class: light
- priority: 2
- deps: —
- area: pipeline/src/routine_watch/drift.py, pipeline/tests/test_drift.py
- owner: —
- claimed: —
- pr: —

What: SPEC Nice-to-have 6: a sustained upward trend in a resident's daily error score over weeks, reported as a trend for review, separate from the sudden-change flag. Read only the files in `area`, `pipeline/src/routine_watch/change_detection.py` (style; do not edit) and `pipeline/pyproject.toml`. Standard library only.
Interface: `@dataclass(frozen=True) class Drift: slope_per_day: float; days: int; trending: bool`; `drift(daily: Sequence[tuple[date, float]], min_days: int = 7, min_slope: float = 0.1) -> Drift`. Slope = Theil–Sen (median of pairwise slopes, x in days). `trending` = `days >= min_days and slope_per_day >= min_slope`. Fewer than 2 points → slope 0, not trending. Input order doesn't matter.
Acceptance:
- Tests: flat series not trending; steady +0.2/day over 14 days trending; one huge spike in an otherwise flat series NOT trending (robustness); 5 days of rising scores not trending (too short); unsorted input same result.
- `cd pipeline && uv run pytest tests/test_drift.py -q` and `scripts/ci.sh` pass.

### T034 — More step-level scenarios
- status: todo
- class: light
- priority: 2
- deps: —
- area: tests/scenarios/tea_sequence_error/, tests/scenarios/tea_substitution/, tests/scenarios/tea_unclear_not_error/, tests/scenarios/tea_single_bad_no_flag/
- owner: —
- claimed: —
- pr: —

What: Widen e2e coverage of SPEC §7. Read only `tests/scenarios/README.md`, every file in `tests/scenarios/tea_normal/` and `tests/scenarios/tea_skip_teabag_pour_twice/` (copy their style), `pipeline/src/routine_watch/tasks/tea.yaml` and `contracts/step_event.schema.json`. Add four `steps.jsonl` + `expected.yaml` scenarios, each with a header comment saying what it proves. Do not edit any code.
Interface: `tea_sequence_error`: pour before teabag_in_cup, teabag added after → one `sequence` error. `tea_substitution`: stir done with `milk` instead of `spoon` → one `substitution` error. `tea_unclear_not_error`: normal session where teabag_in_cup has confidence 0.4 and `unclear: true` → no errors. `tea_single_bad_no_flag`: the demo bad session with quiet history and NO other recent bad session → errors as usual, `flag: false` (a single bad session never alerts).
Acceptance:
- `scripts/e2e.sh` passes for all scenarios. If the pipeline disagrees with SPEC §7 on one, don't edit code: leave that scenario out and describe the disagreement in the PR body.
- `scripts/ci.sh` passes.

### T035 — Ghost replay overlay component
- status: todo
- class: light
- priority: 2
- deps: —
- area: web/src/evidence/GhostReplay.tsx, web/src/evidence/GhostReplay.test.tsx
- owner: —
- claimed: —
- pr: —

What: SPEC Nice-to-have 1: today's skeleton drawn over the resident's normal routine at the same moment. Skeleton only, never video. Read only the files in `area`, `web/src/contracts.ts` (types `CaptureFrame`, `Pose`, `Landmark`; do not edit), `web/src/live/TaskMap.test.tsx` (test style) and `web/package.json`. Self-contained SVG; do not import other components.
Interface: `GhostReplay({today, normal, t, width = 480, height = 360}: {today: CaptureFrame[]; normal: CaptureFrame[]; t: number; width?: number; height?: number})`. Picks the frame with the closest `t` from each list; draws the normal pose as grey circles+lines at 40% opacity (`data-layer="normal"`) under today's pose in blue (`data-layer="today"`). Landmarks are normalised 0–1. Pose connections: shoulders 11–12, arms 11–13–15 and 12–14–16, torso 11–23, 12–24, 23–24. Empty list → that layer omitted; both empty → text "No skeleton data". A small legend "Today" / "Usual".
Acceptance:
- Vitest: both layers render with the right circle counts; nearest-t frame chosen; empty normal → only today layer; both empty → text.
- `cd web && npm test && npm run build` and `scripts/ci.sh` pass.

### T036 — Skeleton replay player
- status: todo
- class: light
- priority: 2
- deps: T025
- area: web/src/evidence/ReplayPlayer.tsx, web/src/evidence/ReplayPlayer.test.tsx
- owner: —
- claimed: —
- pr: —

What: Plays a span of skeleton frames as the "evidence one tap away" for an error. Read only the files in `area`, `web/src/live/SkeletonView.tsx` (import it; do not edit), `web/src/contracts.ts` (type `CaptureFrame`), `web/src/live/TaskMap.test.tsx` and `web/package.json`.
Interface: `ReplayPlayer({frames, autoPlay = false, fps = 10}: {frames: CaptureFrame[]; autoPlay?: boolean; fps?: number})`: renders `SkeletonView` for the current frame, a Play/Pause button, an `<input type="range" aria-label="Replay position">` scrubber, and the current time as m:ss. Uses `setInterval` at `fps`; stops at the end. Empty frames → "No replay available".
Acceptance:
- Vitest with fake timers: play advances frames; pause stops; scrubber jumps; stops at end; empty list text.
- `cd web && npm test && npm run build` and `scripts/ci.sh` pass.

### T037 — Skeleton replay API for evidence
- status: todo
- class: standard
- priority: 2
- deps: T029
- area: pipeline/src/routine_watch/evidence.py, pipeline/src/routine_watch/api.py (add the route only), pipeline/tests/test_evidence.py
- owner: —
- claimed: —
- pr: —

What: Back the alert's "open evidence" with skeleton frames, never video (SPEC §8). Demo sessions have no recorded frames, so map the flagged resident's latest session to the `tea_skip_teabag_pour_twice`-style frames scenario (or `tea_no_kettle` until it exists) and a normal session for the ghost layer.
Interface: `evidence.replay_frames(session_id, t_start, t_end, fps=10) -> list[CaptureFrame]` (downsampled, padded ±2 s, clipped to session); `GET /sessions/{session_id}/replay?t_start&t_end&fps` → `{session_id, frames}`, 404 unknown session; `GET /residents/{id}/normal_replay?t_start&t_end` → frames from a normal session for the ghost overlay.
Acceptance:
- Tests: frames within window, fps cap honoured, 404s, payload validates against `contracts/capture_frame.schema.json`, no image/bytes fields.
- `cd pipeline && uv run pytest tests/test_evidence.py -q` and `scripts/ci.sh` pass.

### T038 — Session store: in-memory default + Tiger Data (TimescaleDB)
- status: todo
- class: standard
- priority: 2
- deps: —
- area: pipeline/src/routine_watch/store.py, pipeline/sql/schema.sql, pipeline/tests/test_store.py, pipeline/pyproject.toml, .env.example
- owner: —
- claimed: —
- pr: —

What: SPEC §6.3 and the Tiger Data prize: sessions, step events and errors stored as time series. In-memory is the default so tests/CI/demo need no DB; Timescale only when `DATABASE_URL` is set.
Interface: `class Store(Protocol)`: `add_session(Session)`, `add_events(list[StepEvent])`, `add_errors(list[TaskError])`, `sessions(resident_id, task_id, since: datetime) -> list[Session]`, `errors_for(session_id) -> list[TaskError]`. `MemoryStore`; `TimescaleStore(dsn)` using psycopg 3 (optional extra `db`); `schema.sql` creates `sessions`, `step_events`, `task_errors` with hypertables on the time column; `get_store()` picks by env. Not wired into the API yet.
Acceptance:
- MemoryStore tests for every method; TimescaleStore tests skipped unless `DATABASE_URL` set; `schema.sql` parses (basic check) and is idempotent (`IF NOT EXISTS`).
- `cd pipeline && uv run pytest tests/test_store.py -q` and `scripts/ci.sh` pass.

### T039 — Capture process: MediaPipe + local detector → JSONL
- status: todo
- class: heavy
- priority: 1
- deps: —
- area: pipeline/src/routine_watch/capture.py, pipeline/src/routine_watch/detector.py, pipeline/tests/test_capture.py, pipeline/pyproject.toml (optional extra `capture`), .env.example
- owner: —
- claimed: —
- pr: —

What: SPEC MVP 1–2 and §16: the privacy boundary. Webcam or video file → MediaPipe pose + hands + local object detector → one `CaptureFrame` JSONL record per frame; frames dropped after processing, never written. Roboflow weights run locally (no hosted inference, no training runs); until weights exist, `FakeDetector` returns no boxes.
Interface: `frame_record(t, pose_landmarks, hand_landmarks, detections, source) -> CaptureFrame` (pure, tested); `class Detector(Protocol): detect(image) -> list[ObjectDetection]`, `FakeDetector`, `LocalDetector(weights_path)` (ONNX/ultralytics, import guarded); `run(source: int | Path, out: Path, fps: int = 15)`; CLI `python -m routine_watch.capture --camera 0 | --video path --out file.jsonl`. Heavy deps (mediapipe, opencv) only in the `capture` extra and imported lazily so CI doesn't need them.
Acceptance:
- Tests (no camera, no mediapipe needed): `frame_record` from fake landmark objects validates against `contracts/capture_frame.schema.json`; output records contain no image/bytes/base64 fields; CLI `--help` works without the extra installed.
- `cd pipeline && uv run pytest tests/test_capture.py -q` and `scripts/ci.sh` pass.

### T040 — Privacy guard test
- status: todo
- class: light
- priority: 2
- deps: —
- area: pipeline/tests/test_privacy.py
- owner: —
- claimed: —
- pr: —

What: SPEC §8/§12 as a test: nothing that flows between stages or is stored can carry an image, and nothing says "diagnose". Read only `pipeline/tests/test_contracts.py` (style), `contracts/README.md` and the file list of `contracts/` and `tests/scenarios/`. Do not edit any other file.
Interface: pytest only. (1) Walk every `contracts/*.schema.json`; fail if any property name matches `image|frame_bytes|jpeg|png|video|pixels|base64` (case-insensitive) or has `contentEncoding`. (2) Every line of every `tests/scenarios/*/*.jsonl` and `contracts/examples/*.jsonl` is < 20 kB and contains no `data:image` / long base64 run (≥ 200 chars of `[A-Za-z0-9+/=]`). (3) No file under `pipeline/src/` or `web/src/` (excluding tests) contains `diagnos` except in a negation like "never diagnos" / "not diagnos" / "It never diagnoses" — list offenders.
Acceptance:
- Test passes on current main (if it finds a real offender, report it in the PR instead of editing other files, and mark that check `xfail` with the reason).
- `cd pipeline && uv run pytest tests/test_privacy.py -q` and `scripts/ci.sh` pass.

### T041 — Second task: taking medication with water
- status: todo
- class: heavy
- priority: 3
- deps: —
- area: contracts/, pipeline/src/routine_watch/contracts.py, web/src/contracts.ts (regenerated), pipeline/src/routine_watch/tasks/meds.yaml, pipeline/tests/test_meds_graph.py, tests/scenarios/meds_normal/, tests/scenarios/meds_skip_water/
- owner: —
- claimed: —
- pr: —

What: SPEC Nice-to-have 4: show the graph-based approach generalises. Add detector classes `pill_bottle`, `pill_organiser`, `glass`, `water_jug` (contracts change: regenerate schemas + TS via `uv run python -m routine_watch.contracts`), a `meds.yaml` graph (get glass → fill glass; open organiser → take pill → drink water; close organiser optional), and two step-level scenarios.
Interface: `load_task("meds")` works; existing tea graph and scenarios untouched.
Acceptance:
- Graph tests (deps, optional step, aliases); `meds_skip_water` yields an omission of `drink_water`; contracts check in CI passes.
- `scripts/e2e.sh` and `scripts/ci.sh` pass.

### T042 — Design system: tokens + shared UI primitives
- status: todo
- class: standard
- priority: 0
- deps: —
- area: web/src/index.css, web/src/ui/, web/src/ui/*.test.tsx
- owner: —
- claimed: —
- pr: —

What: One visual language for every screen so parallel web tasks don't drift. Keep the current calm dark theme; extend it, don't restyle.
Interface: tokens in `web/src/index.css` (colour incl. status normal/watch/flagged and error red/amber/unclear grey, spacing scale, radii, type scale, focus ring); shared components in `web/src/ui/`: `Card`, `StatusChip` (move/replace `overview/StatusChip.tsx`), `Button` (primary/secondary/danger), `SectionHeader`, `EmptyState`, `ErrorState`, `Loading`; `web/src/ui/README.md` with one-line usage each.
Acceptance:
- Existing screens switched to the tokens/components with no visual regressions beyond consistency; no hard-coded hex in components.
- Contrast ≥ 4.5:1 for text tokens; Vitest tests for each component.
- `cd web && npm run lint && npm test && npm run build` passes.
