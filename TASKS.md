# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: 1898e3b

## Tasks

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

### T152 — Shift handoff rows open the resident's alert
- status: claimed
- class: standard
- priority: 3
- kind: feature
- deps: T151
- area: web/src/handoff/Handoff.tsx, web/src/handoff/Handoff.test.tsx, web/src/App.tsx, web/src/App.test.tsx
- source: proposed
- owner: ian-claude
- claimed: 2026-10-17T09:10Z
- pr: —

What: From the handoff, the incoming nurse should reach the evidence in one tap. Rows with an unreviewed alert get an "Open alert" button that goes to the alert screen. Check `pipeline/src/routine_watch/handoff.py` for whether rows carry alert ids; if not, use the first matching alert from `fetchAlerts()` by resident id (don't change the API here; note it in the PR).
Interface: `Handoff({ onBack, onOpenAlert }: { onBack: () => void; onOpenAlert?: (alertId: string) => void })`; App passes `id => { setOpenHandoff(false); setOpenAlert(id) }`.
Acceptance:
- tests: button only on rows with unreviewed alerts; clicking calls `onOpenAlert` with the right id; App test: handoff → Open alert shows the alert view.
- `cd web && npx vitest run` passes; `scripts/ci.sh` passes.

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
- status: todo
- class: light
- priority: 3
- kind: improvement
- deps: —
- area: web/src/resident/HeatCalendar.tsx, web/src/resident/HeatCalendar.test.tsx
- owner: —
- claimed: —
- pr: —

What: The heat calendar has no legend, so a nurse can't tell what darker red means, and cell labels show raw scores ("score 3.4000001"). Add a one-line legend under the grid ("Lighter = fewer errors · Darker = more errors · Grey = no session", with small swatches using the same CSS vars) and format cell labels with `formatScore`.
Interface: Read only `web/src/resident/HeatCalendar.tsx`, its test, and `formatScore` in `web/src/resident/format.ts` (import; don't modify). Swatches `aria-hidden`; legend text visible.
Acceptance:
- tests: legend text rendered; a cell label uses the formatted score.
- `cd web && npm test -- HeatCalendar` and `scripts/ci.sh` pass.

### T173 — Docs: CODEMAP note for the overview's top pattern
- status: todo
- class: light
- priority: 3
- kind: docs
- deps: —
- area: docs/CODEMAP.md
- owner: —
- claimed: —
- pr: —

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
- status: claimed
- class: light
- priority: 2
- kind: test
- deps: —
- area: scripts/smoke.sh
- owner: ian-claude-standard-2
- claimed: 2026-10-17T09:15Z
- pr: —

What: `scripts/smoke.sh` hits the API routes of a running stack but skips `GET /handoff` (shift handoff screen), so a broken handoff route wouldn't show up in smoke runs.
Interface: Read only `scripts/smoke.sh` and the `/handoff` route in `pipeline/src/routine_watch/api.py` (returns `{window_hours, residents: [...], summary: str}`, `hours` query 1-168, default 12). Add checks in the existing PASS/FAIL style.
Acceptance:
* New check: `GET /handoff` returns 200 with `window_hours == 12`, a non-empty `residents` list and a non-empty `summary` string.
* New check: `GET /handoff?hours=0` returns 422.
* `bash -n scripts/smoke.sh` passes; `scripts/ci.sh` passes. Say in the PR whether you ran it against `scripts/dev.sh up`.

### T179 — Docs: CODEMAP note that handoff reuses the alert's errors
- status: todo
- class: light
- priority: 3
- kind: docs
- deps: —
- area: docs/CODEMAP.md
- owner: —
- claimed: —
- pr: —

What: T166 (PR #159) made `alerts.session_id_for`, `task_errors`, `distinct_clauses` and `normal_error_rate` public so `handoff.py` writes its summary from the same evidence as the alert, against that resident's own baseline. CODEMAP notes don't say so.
Interface: Read only `docs/CODEMAP.md`, `git show e4f8fe1 --stat` and the module docstrings of `pipeline/src/routine_watch/alerts.py` and `handoff.py`. Edit notes only, not the generated file list.
Acceptance:
* 2-4 line note next to the existing handoff/alert notes naming the four shared functions and why (same steps, same times, same baseline).
* No other file changed.

### T180 — Handoff: each row says what's normal for that resident
- status: todo
- class: standard
- priority: 3
- kind: feature
- deps: —
- area: web/src/handoff/
- owner: —
- claimed: —
- source: proposed
- pr: —

What: Rationale: a night nurse reading the handoff can't tell whether "2 flags" is unusual for that resident. Each row gets a short muted line like "Usually 0.4 errors a session" so the change reads against her own normal (SPEC §7, Clarity).
Interface: Read `web/src/handoff/Handoff.tsx`, `types.ts`, `api.ts`, `mockHandoff.ts` and the row fields in `pipeline/src/routine_watch/handoff.py`. If rows don't carry a baseline, take it from the resident detail fetch in `web/src/resident/api.ts` (one fetch per row is fine for the demo) and say so in the PR; don't change the API or `contracts/`.
Acceptance:
* Rows with history show the baseline line; residents with no history show nothing (no "NaN", no "0").
* Wording never says "diagnos"/"has <condition>"; plain numbers a nurse reads in 10 s.
* New/updated test in `web/src/handoff/Handoff.test.tsx`; `scripts/ci.sh` passes.

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

### T182 — Review: false alarm makes the alert 404, so the cause answer can't be saved
- status: claimed
- class: standard
- priority: 0
- kind: bug
- source: reviewer
- deps: —
- area: pipeline/src/routine_watch/api.py, pipeline/tests/test_api_feedback.py
- owner: ian-claude-standard
- claimed: 2026-10-17T09:15Z
- pr: —

What: Since T167, `_alerts_by_id()` builds alerts only from `_flagged_residents()` (feedback-tuned). A "false alarm" raises the resident's threshold 10%; if that un-flags her, the alert disappears, so `GET /alerts/{id}` and the next `POST /alerts/{id}/feedback` return 404. AlertView posts the verdict, then posts again with the "what was it?" cause, so the nurse sees "Feedback could not be saved" and can never correct a mistaken tap. Fix: look alerts up by id from every raw-flagged resident (`build_alerts([r for r in demo_residents() if r["status"] == "flagged"], feedback=_feedback_store)`); keep the tuned filter only for the `/alerts` list.
Acceptance:
* Test: flagged resident, POST false_alarm with a threshold step big enough to un-flag; `/alerts` no longer lists it, but `GET /alerts/{id}` is 200 and a second POST with `cause` is 200 and stores the cause.
* `scripts/ci.sh` passes.

### T183 — Review: overview/handoff top pattern ignores nurse-feedback weights
- status: todo
- class: light
- priority: 1
- kind: bug
- source: reviewer
- deps: T182
- area: pipeline/src/routine_watch/api.py, pipeline/src/routine_watch/handoff.py, pipeline/tests/test_api_residents.py
- owner: —
- claimed: —
- pr: —

What: `/residents` shows `top_pattern` from `demo.py` (`score_patterns` with no weights), while the alert's `patterns[0]` is re-weighted by `FeedbackStore.pattern_weights` (T130). After a nurse answers "what was it?", the overview chip and the alert can name different patterns for the same resident. `handoff.build_handoff` also calls `build_alerts(residents)` without `feedback=`. Fix: in `api._tuned`, when the resident has pattern weights, recompute `top_pattern` with `score_patterns(features, weights=..., answers=...)` (reuse `alerts._patterns` or expose a small helper) and pass the store into `build_alerts` in handoff.
Acceptance:
* Test: confirm an alert with a cause that reorders the ranking; `/residents` top_pattern id equals `/alerts/{id}` `patterns[0].pattern_id`.
* `scripts/ci.sh` passes.

### T184 — Test: status_for with the raw threshold gives each resident's own status
- status: in-review
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
- status: todo
- class: standard
- priority: 2
- kind: improvement
- deps: T184
- area: pipeline/src/routine_watch/demo.py, pipeline/tests/test_demo.py
- owner: —
- claimed: —
- pr: —

What: `demo_residents()` and `status_for()` each build `timestamped`, call `flag_change` and `_watch`, then `_status` (the second copy calls `_watch(sessions, sessions, ...)` instead of `(history, sessions, ...)`, which only works because live sessions fall after the baseline cutoff). Pull this into one private helper both call, with no behaviour change.
Interface: one private helper (e.g. `_status_from(history, sessions, scores, baseline: Baseline) -> str`); `status_for` signature unchanged; `api.py` untouched.
Acceptance:
* `flag_change(` and `_watch(` are each called once in `demo.py`.
* T184's test and `pipeline/tests/test_demo*.py` pass unchanged.
* `scripts/ci.sh` passes.

### T186 — Live screen: ?task=meds opens on the medication routine
- status: in-review
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

### T187 — Test: App shows the live routine picker with tea selected
- status: todo
- class: light
- priority: 3
- kind: test
- deps: —
- area: web/src/App.test.tsx
- owner: —
- claimed: —
- pr: —

What: T161 swapped `LiveSession` for `LiveScreen` in `App.tsx`; nothing at app level checks the picker is there. Add one test.
Interface: Read only `web/src/App.tsx`, `web/src/App.test.tsx`, `web/src/live/LiveScreen.tsx`. Reuse App.test's existing fetch/websocket mocks.
Acceptance:
* Test: the "Routine to watch" group renders with "Making tea" pressed and "Medication with water" not pressed.
* `scripts/ci.sh` passes.
