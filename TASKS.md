# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: 8f7b286

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

### T183 — Review: overview/handoff top pattern ignores nurse-feedback weights
- status: claimed
- class: light
- priority: 1
- kind: bug
- source: reviewer
- deps: T182
- area: pipeline/src/routine_watch/api.py, pipeline/src/routine_watch/handoff.py, pipeline/tests/test_api_residents.py
- owner: ian-claude
- claimed: 2026-10-17T09:23Z
- pr: —

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
- status: in-review
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

### T192 — /demo/reset also resumes paused room monitoring
- status: todo
- class: light
- priority: 2
- kind: improvement
- deps: T149
- area: pipeline/src/routine_watch/api.py (demo_reset only), pipeline/tests/test_api_demo_reset.py
- owner: —
- claimed: —
- pr: —

What: After T149 a rehearsal can pause a room, and `/demo/reset` leaves it paused. Make reset also call the monitoring store's `reset()`.
Interface: read `pipeline/src/routine_watch/api.py` (`demo_reset`), `pipeline/src/routine_watch/monitoring.py` (`get_monitoring_store`, `MonitoringStore.reset`), `pipeline/tests/test_api_demo_reset.py`.
Acceptance:
- Test: PUT a room to paused, POST /demo/reset, GET /monitoring shows no paused rooms.
- `cd pipeline && pytest tests/test_api_demo_reset.py` and `scripts/ci.sh` pass.

### T193 — Scenario: medication taken twice is a repetition error
- status: claimed
- class: standard
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/meds_pill_twice/ (new), tests/scenarios/README.md
- owner: ian-claude-standard-2
- claimed: 2026-10-17T09:27Z
- pr: —

What: The medication routine has skip and order scenarios but none for a repeated step, the most safety-relevant meds error. Add one.
Interface: copy the shape of `tests/scenarios/meds_normal/` and `tests/scenarios/tea_kettle_twice/`; `frames.jsonl` + `expected.yaml` with one repetition error on the take-pill step.
Acceptance:
- `scripts/e2e.sh` passes including the new scenario; README lists it (the README coverage test passes).
- If the meds graph can't express it, stop and set the task blocked with the reason (don't change pipeline code).

### T194 — smoke.sh: seeded alert survives /demo/reset
- status: claimed
- class: light
- priority: 2
- kind: test
- deps: T178
- area: scripts/smoke.sh
- owner: max_API_light
- claimed: 2026-10-17T09:28Z
- pr: —

What: Reset must only drop live sessions and feedback, not the seeded demo history. After smoke.sh's POST /demo/reset, check GET /alerts still returns at least one alert.
Interface: read `scripts/smoke.sh` (the `/demo/reset` block at the end and the existing `/alerts` check).
Acceptance:
- New PASS/FAIL line "GET /alerts after reset" right after the reset check.
- `bash -n scripts/smoke.sh` and `scripts/ci.sh` pass; against `scripts/dev.sh up` all checks pass.

### T195 — Unit overview: All / Flagged / Watch filter
- status: todo
- class: standard
- priority: 3
- kind: feature
- source: proposed
- deps: —
- area: web/src/overview/UnitOverview.tsx, web/src/overview/UnitOverview.test.tsx
- owner: —
- claimed: —
- pr: —

What: Rationale: on a real unit a nurse wants only the residents needing attention in one tap (Clarity). Add a three-way filter above the resident list; All stays default so the demo path is unchanged.
Interface: local state in `UnitOverview`; buttons with `aria-pressed`; filters on the existing resident `status`; empty filter result uses `EmptyState` "No residents flagged for review." / "No residents to watch.".
Acceptance:
- Tests: each filter shows only matching residents; empty case shows the message; default is All.
- `cd web && npm test -- UnitOverview` and `scripts/ci.sh` pass.
