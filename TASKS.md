# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: 21fbbee

## Tasks

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

### T030 — Gemini step verifier behind an interface
- status: todo
- class: standard
- priority: 2
- kind: feature
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

### T032 — Claude alert summariser behind the Explainer interface
- status: todo
- class: standard
- priority: 2
- kind: feature
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

### T037 — Skeleton replay API for evidence
- status: todo
- class: standard
- priority: 2
- kind: feature
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
- kind: feature
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
- status: claimed
- class: heavy
- priority: 1
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/capture.py, pipeline/src/routine_watch/detector.py, pipeline/tests/test_capture.py, pipeline/pyproject.toml (optional extra `capture`), .env.example
- owner: ian-claude
- claimed: 2026-10-17T05:21Z
- pr: —

What: SPEC MVP 1–2 and §16: the privacy boundary. Webcam or video file → MediaPipe pose + hands + local object detector → one `CaptureFrame` JSONL record per frame; frames dropped after processing, never written. Roboflow weights run locally (no hosted inference, no training runs); until weights exist, `FakeDetector` returns no boxes.
Interface: `frame_record(t, pose_landmarks, hand_landmarks, detections, source) -> CaptureFrame` (pure, tested); `class Detector(Protocol): detect(image) -> list[ObjectDetection]`, `FakeDetector`, `LocalDetector(weights_path)` (ONNX/ultralytics, import guarded); `run(source: int | Path, out: Path, fps: int = 15)`; CLI `python -m routine_watch.capture --camera 0 | --video path --out file.jsonl`. Heavy deps (mediapipe, opencv) only in the `capture` extra and imported lazily so CI doesn't need them.
Acceptance:
- Tests (no camera, no mediapipe needed): `frame_record` from fake landmark objects validates against `contracts/capture_frame.schema.json`; output records contain no image/bytes/base64 fields; CLI `--help` works without the extra installed.
- `cd pipeline && uv run pytest tests/test_capture.py -q` and `scripts/ci.sh` pass.

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

### T041 — Second task: taking medication with water
- status: todo
- class: heavy
- priority: 3
- kind: feature
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

### T044 — Alert notifier behind an interface (push alert)
- status: todo
- class: standard
- priority: 2
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/notify.py, pipeline/tests/test_notify.py, .env.example
- owner: —
- claimed: —
- pr: —

What: SPEC Nice-to-have 3 (push alert to a phone) and §10 step 4. A `Notifier` interface with a fake used by default and a Supabase implementation used only when `LIVE_API=1` and Supabase env vars are set. No route wiring in this task.
Interface: `class Notifier(Protocol): def send(self, alert: dict) -> None`; `FakeNotifier` (records sent alerts in `.sent`); `SupabaseNotifier(url, key)` inserting `{alert_id, resident_id, summary, created_at}` into table `alerts_feed` via the REST endpoint with plain HTTP (httpx or urllib, no new SDK); `get_notifier() -> Notifier` returns Supabase only when `LIVE_API=1` and `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` are set, else Fake. Network errors are logged and swallowed (never break the pipeline). Payload carries ids and summary text only, no frames. Document the table in the module docstring; any new env var goes in `.env.example`.
Acceptance:
- Tests: default env → FakeNotifier; LIVE_API=1 without keys → Fake; with keys → Supabase (HTTP mocked; assert URL, headers, body); network failure doesn't raise. No real calls.
- `cd pipeline && uv run pytest tests/test_notify.py -q` and `scripts/ci.sh` pass.

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

### T051 — Feedback buttons announce the recorded choice
- status: todo
- class: light
- priority: 3
- kind: feature
- deps: —
- area: web/src/alert/FeedbackButtons.tsx, web/src/alert/FeedbackButtons.test.tsx
- source: proposed
- owner: —
- claimed: —
- pr: —

What: Accessibility (Execution/Clarity): after a tap, screen-reader and sighted users get a confirmation that the verdict was saved. Read only the files in `area`.
Interface: keep the current props. Add a `<p role="status" aria-live="polite">` under the buttons: `value === 'confirmed'` → "Marked as confirmed", `'false_alarm'` → "Marked as false alarm", no value → empty. Wrap the buttons in `role="group"` with `aria-label="Nurse feedback"`. Keep `aria-pressed`.
Acceptance:
- Vitest: group label present; status text for each value; clicking calls `onChange` with the verdict; empty status with no value.
- `cd web && npm run lint && npm test && npm run build` passes.

### T052 — Demo-data banner component
- status: todo
- class: light
- priority: 3
- kind: feature
- deps: —
- area: web/src/ui/DemoBanner.tsx, web/src/ui/DemoBanner.test.tsx, web/src/ui/README.md (add one line)
- source: proposed
- owner: —
- claimed: —
- pr: —

What: Responsible design / Clarity for judges: a thin banner stating the dashboard runs on synthetic residents. Component only; wiring into `App.tsx` is a later task. Read only the files in `area` and `web/src/ui/Card.tsx` (style).
Interface: `export function DemoBanner({ onDismiss }: { onDismiss?: () => void })` renders `role="note"` with text "Demo mode: synthetic residents, no real patient data. Flags a change for review; never a diagnosis." and, if `onDismiss` is given, a "Dismiss" button. CSS vars only.
Acceptance:
- Vitest: text present, role=note, dismiss button only when `onDismiss` given and calls it.
- `cd web && npm run lint && npm test && npm run build` passes.

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
- status: in-review
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
- status: in-review
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
- status: in-review
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

### T059 — Show the drift card on the resident detail screen
- status: in-review
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
- status: in-review
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
