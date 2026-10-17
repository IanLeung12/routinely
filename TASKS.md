# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: 2b94bf9

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
* Also one line that handoff rows open the resident's alert by looking up the id in `GET /alerts` (T152, `web/src/handoff/Handoff.tsx` `alertByResident`).
* No other file changed.

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

### T198 — Docs: DEMO.md mentions opening an alert from the shift handoff
- status: todo
- class: light
- priority: 3
- kind: docs
- deps: —
- area: docs/DEMO.md
- owner: —
- claimed: —
- pr: —

What: Since T152 (PR #177), each handoff row with an alert pending review has an "Open alert" button. The runbook's handoff step doesn't say so.
Interface: Read only `docs/DEMO.md` and `web/src/handoff/Handoff.tsx` (the `Open alert` button). Add 1-3 lines to the handoff step.
Acceptance:
* DEMO.md says the presenter can click "Open alert" on Mrs. K's handoff row to reach her alert.
* Wording says "flags a change for review"; no "diagnose". No other file changed.

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

### T203 — Shift handoff: print-friendly layout
- status: todo
- class: light
- priority: 3
- kind: feature
- source: proposed
- deps: —
- area: web/src/handoff/handoff.css, web/src/handoff/Handoff.tsx, web/src/handoff/Handoff.test.tsx
- owner: —
- claimed: —
- pr: —

What: nurses hand off on paper; a "Print" button plus `@media print` rules (hide nav/banner/buttons, black on white, no row breaks across pages) make the handoff usable as a printout.
Interface: read only the three area files. Button calls `window.print()`.
Acceptance:
- "Print handoff" button; test mocks window.print and asserts it's called on click
- handoff.css has an `@media print` block hiding `.no-print` elements and `break-inside: avoid` on rows
- `cd web && npm test -- Handoff` passes; `scripts/ci.sh` passes

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

### T206 — Test: alerts.top_pattern_for edge cases
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_top_pattern_for.py
- owner: —
- claimed: —
- pr: —

What: `top_pattern_for` (pipeline/src/routine_watch/alerts.py, added in T183) has only API-level coverage. Add unit tests for it directly.
Interface: read pipeline/src/routine_watch/alerts.py (`top_pattern_for`, `_patterns`), pipeline/src/routine_watch/demo.py (`demo_residents`), and pipeline/tests/test_api_residents.py for fixture style. New file only.
Acceptance:
- With `feedback=None`, for every resident from `demo_residents()` whose `top_pattern` is set, `top_pattern_for(resident)["pattern_id"] == resident["top_pattern"]["pattern_id"]`.
- Returned dict has exactly the keys `pattern_id`, `name`, `urgency`, and `urgency` is a plain string.
- A resident whose patterns all fall below threshold (build one by copying a demo resident and clearing its errors/sessions as needed) returns `None`.
- `cd pipeline && python -m pytest tests/test_top_pattern_for.py -q` and `scripts/ci.sh` pass.

### T207 — Bug: skeleton view and evidence ghost replay show no skeleton, only object boxes
- status: claimed
- class: standard
- priority: 1
- kind: bug
- deps: —
- area: pipeline/src/routine_watch/live.py, pipeline/src/routine_watch/evidence.py, pipeline/tests/
- owner: ian-claude
- claimed: 2026-10-17T09:54Z
- pr: —

What: Tester (main 355d6b1). Every stand-in frame the demo serves is built with `poses=[]` and `hands=[]` (`live._synthetic_frames`, and the recordings behind `/sessions/{id}/replay` and `/residents/{id}/normal_replay`), so the live "Skeleton view" and the alert's "Today / Usual" ghost replay draw only labelled object boxes, never a body skeleton or hands (SPEC §5 ghost replay, §10 step 3 "skeleton view").
Repro: `OFFLINE_MODE=true scripts/dev.sh up`; open the dashboard, wait for the live session to flag, click "Open alert", press Play under Evidence. `curl "localhost:8000/sessions/mrs-k-22/replay?t_start=40&t_end=60"` → every frame has `"poses": [], "hands": []`.
Expected: a simple stick-figure pose (and a hand near the active object) in each synthetic frame, moving between the objects of each step; Usual replay differs visibly from Today. Actual: boxes only.
Interface: `_synthetic_frames` (and whatever builds the replay stand-in frames) fill `poses`/`hands` with keypoints per the `contracts/` CaptureFrame schema (no contract change); see `contracts/examples/capture.jsonl` for the shape.
Acceptance:
- Pipeline test: synthetic live frames and `/sessions/{id}/replay` frames have ≥1 pose with keypoints in [0,1].
- No change to step/error/flag results: `scripts/e2e.sh` still 23/23.
- `scripts/ci.sh` passes.

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
- status: claimed
- class: standard
- priority: 2
- kind: feature
- source: proposed
- deps: —
- area: web/src/live/SessionSummary.tsx (new), web/src/live/SessionSummary.test.tsx (new), web/src/live/LiveSession.tsx, web/src/live/LiveSession.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T10:03Z
- pr: —

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

### T212 — Docs: CODEMAP note that alerts read live session errors
- status: todo
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

### T213 — Alert view: heading order, focus on open, landmark
- status: claimed
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/alert/AlertView.tsx, web/src/alert/AlertView.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T10:08Z
- pr: —

What: The alert is the screen judges and nurses read most. Make it navigable by screen reader and keyboard: one `h1` (resident + "Flagged for review"), section `h2`s in reading order (What changed, Errors, Evidence, Patterns, Suggested checks, Feedback), the view wrapped in a labelled `main`/`section`, and focus moved to the `h1` when an alert opens.
Interface: markup-only changes in `AlertView.tsx`; keep existing class names and copy.
Acceptance:
- Tests: heading levels via `getAllByRole('heading')`, `h1` has focus after render, existing tests still pass unchanged in meaning.
- `cd web && npm test` and `scripts/ci.sh` pass.

### T214 — TaskMapLegend: CSS classes instead of inline styles
- status: in-review
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
- status: todo
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/DriftCard.tsx, web/src/resident/driftCard.css, web/src/resident/DriftCard.test.tsx
- owner: —
- claimed: —
- pr: —

What: `DriftCard.tsx` sets text colour inline, including a `state === 'trending'` ternary. Move it to a new `web/src/resident/driftCard.css` keyed off the existing `data-state` attribute (`.drift-card[data-state="trending"] .drift-card__summary { color: var(--error-amber-text) }`). No visual change.
Interface: read only the area files and `web/src/resident/heatCalendar.css` as the example.
Acceptance:
- `grep -c "style={{" web/src/resident/DriftCard.tsx` is 0
- test asserts the trending summary has the `drift-card__summary` class and the card keeps `data-state="trending"`
- `cd web && npm test -- DriftCard` and `scripts/ci.sh` pass

### T216 — HeatCalendar grid and cells: CSS classes instead of inline styles
- status: todo
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/HeatCalendar.tsx, web/src/resident/heatCalendar.css, web/src/resident/HeatCalendar.test.tsx
- owner: —
- claimed: —
- pr: —

What: after T197 moved the legend to `heatCalendar.css`, the grid (line ~24) and day cells (~30, ~52) still use inline styles. Move static layout to classes (`heat-grid`, `heat-cell`). A per-cell colour that depends on the score may stay inline only as a single CSS custom property (e.g. `style={{ '--heat': ... }}`). No visual change.
Interface: read only the area files.
Acceptance:
- HeatCalendar.tsx has at most one inline style, and it only sets a CSS custom property
- existing HeatCalendar tests pass; one new test asserts cells have the `heat-cell` class
- `cd web && npm test -- HeatCalendar` and `scripts/ci.sh` pass

### T217 — Resident detail: heading order, landmark, focus on open
- status: todo
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/ResidentDetail.tsx, web/src/resident/ResidentDetail.test.tsx
- owner: —
- claimed: —
- pr: —

What: same accessibility pass as T213 does for the alert view, on the resident detail screen: one `h1` (the resident's display name), section headings as `h2` in visual order, the screen wrapped in `<main>` or a labelled region, and focus moved to the `h1` when the screen opens so a screen-reader user hears whose page it is.
Interface: ResidentDetail only; don't touch child components (BaselineChart, HeatCalendar, DriftCard, SessionList, ContextTimeline) beyond what ResidentDetail renders around them.
Acceptance:
- test: exactly one `heading` of level 1 with the resident's name; it has focus after render
- test: no heading level is skipped (h1 → h2)
- `cd web && npm test -- ResidentDetail` and `scripts/ci.sh` pass

### T218 — Test: DemoBanner disables Reset while resetting and clears the error on retry
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/ui/DemoBanner.tsx, web/src/ui/DemoBanner.test.tsx
- owner: —
- claimed: —
- pr: —

What: the Reset demo button (T189, T200) is the presenter's recovery path, so pin its behaviour: the button is disabled while the reset promise is pending, and a "Couldn't reset the demo" error from a failed attempt disappears after a later successful reset. If the second case fails today, fix it in DemoBanner.tsx.
Interface: `DemoBanner({ onReset })` with an injected fake `onReset`; read only the area files.
Acceptance:
- test: pending reset → button disabled; resolved → enabled
- test: reject then resolve → `role="alert"` error gone
- `cd web && npm test -- DemoBanner` and `scripts/ci.sh` pass

### T219 — Bug: live session's final error list differs from replay for sequence scenarios
- status: todo
- class: standard
- priority: 1
- kind: bug
- deps: —
- area: pipeline/src/routine_watch/live.py, pipeline/tests/test_live_matches_replay.py, pipeline/tests/test_live.py
- owner: —
- claimed: —
- pr: —

What: Played live, `tea_sequence_error`, `tea_self_corrected`, `meds_pill_before_water` and `meds_self_corrected` stream a transient `omission` for a dependency that happens later, so the errors the demo ends on are not the ones `expected.yaml` checks (xfailed in `test_live_matches_replay.py`, noted again in T202/#197). Keep streaming errors as now, but make `session_end` carry the healed final list so the screen can settle on the right answer.
Interface: the `session_end` message gains `errors` = the `final` `classify_errors(..., ended=True)` result `live.py` already computes, serialised like the `error` message's `error`. The `live.py` docstring says streamed errors are provisional and `session_end.errors` is authoritative. No change to `contracts.py`.
Acceptance:
* `test_live_matches_replay.py` compares `session_end["errors"]` against `expected.yaml` for every scenario; the `_SEQUENCE_HEALS_FROM_A_TRANSIENT_OMISSION` xfail set is removed and all scenarios pass.
* Existing live tests still pass; `scripts/ci.sh` passes.

### T220 — Live screen: settle on session_end's final error list
- status: todo
- class: light
- priority: 1
- kind: bug
- deps: T219
- area: web/src/live/useLiveSession.ts, web/src/live/mockLiveStream.ts, web/src/live/useLiveSession.test.ts
- owner: —
- claimed: —
- pr: —

What: After T219 the `session_end` WebSocket message carries `errors`, the session's final (healed) error list. The live screen should replace its streamed error list with it, so a step reported missed mid-session but done later no longer shows as missed once the session ends.
Interface: read `web/src/live/useLiveSession.ts` (message union and reducer, `case 'session_end'`), `web/src/live/mockLiveStream.ts`, and the `session_end` part of the module docstring in `pipeline/src/routine_watch/live.py`. Add optional `errors` to the `session_end` message type (same shape as the `error` message's `error`); on `session_end` with `errors`, set the state's errors to it; without `errors` (older server), keep the streamed list. Add `errors` to the mock's `session_end`.
Acceptance:
* test: a streamed omission followed by a `session_end` whose `errors` lack it leaves only the final errors
* test: a `session_end` without `errors` keeps the streamed list
* `cd web && npm test` and `scripts/ci.sh` pass

### T221 — Copy summary uses the resident's real name, not one guessed from the id
- status: todo
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/alert/alertText.ts, web/src/alert/alertText.test.ts, web/src/alert/AlertView.tsx
- owner: —
- claimed: —
- pr: —

What: T211 (#198) added `residentDisplayName` in `alertText.ts`, which builds "Mrs. K" from the id `mrs-k`, while the rest of the app (`App.tsx` ~line 50) shows `resident.name` from the API, so the two can disagree for other residents. Pass the real name in instead.
Interface: read `web/src/alert/alertText.ts`, `web/src/alert/alertText.test.ts`, `web/src/alert/AlertView.tsx` (it already calls `fetchResident(alert.resident_id)`). Change to `alertText(alert: Alert, residentName?: string)` using `residentName ?? alert.resident_id`; delete `residentDisplayName` and `TITLES`. In `AlertView.tsx`, keep the fetched resident's `name` in state next to the care records and pass it to `alertText`.
Acceptance:
* test: with a name, the first line is `Resident: <name>`; without, it falls back to the id; existing wording tests still pass
* `cd web && npm test` and `scripts/ci.sh` pass
