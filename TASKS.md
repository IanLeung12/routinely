# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: 7fac25f

## Tasks

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

### T240 — Pattern library: usable at phone width (375 px)
- status: todo
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

### T305 — Feedback history card: usable at phone width (375 px)
- status: todo
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

### T317 — Test: each screen sets its page title
- status: todo
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

### T348 — Docs: CODEMAP note that unclear sessions are never scored
- status: todo
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

### T355 — Shift handoff: say when a room's capture was too unclear to score this shift
- status: claimed
- class: heavy
- priority: 2
- kind: feature
- source: proposed
- deps: T343
- area: pipeline/src/routine_watch/contracts.py, contracts/, pipeline/src/routine_watch/live.py, pipeline/src/routine_watch/handoff.py, pipeline/src/routine_watch/store.py, pipeline/tests/test_handoff_unclear.py, web/src/contracts.ts, web/src/handoff/HandoffRow.tsx, web/src/handoff/mockHandoff.ts
- owner: ian-claude
- claimed: 2026-10-17T19:50Z
- pr: —

What: Rationale: since T342 unclear sessions are dropped from history, so repeated bad lighting or a blocked camera goes unnoticed; the incoming nurse should see "2 sessions too unclear to score — check the camera view" for that room. Keep a per-room count of unclear sessions (timestamps only, never frames, never in the resident's scored history) and surface it as `HandoffResident.unclear_sessions: int` for the window.
Interface: `HandoffResident.unclear_sessions: int` (default 0; regenerate schema and web types the repo's way, update every consumer and mock in the same PR); the handoff row shows the line only when > 0. Wording is about the capture, never the resident.
Acceptance:
- pytest: two unclear live sessions in the window → `unclear_sessions == 2`, resident's history and flag unchanged; outside the window → 0
- web test: row shows the camera line when > 0 and nothing when 0
- `scripts/ci.sh` passes

### T363 — Test: task map legend has accessible names for every step state
- status: todo
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

### T367 — Bug: integration check failing on main
- status: todo
- class: standard
- priority: 0
- kind: bug
- deps: —
- area: scripts/dev.sh, pipeline/src/routine_watch/api.py, web/src/
- owner: —
- claimed: —
- pr: —
- source: integration
- note: T388 (#370) stopped integration.sh sharing/killing a running dev stack, a likely cause; first re-run scripts/integration.sh on main twice and, if both print OK, mark done with a note. Earlier: tester saw this once on a cold start (TESTREPORT: likely Vite cold-start/dep-optimise timing; re-run passed). If it is timing, make scripts/integration.sh wait for Vite readiness (fixing the check is fine here); otherwise fix the render.

What: `scripts/integration.sh` (stack up offline → API endpoints → dashboard render → live WebSocket) fails on main @ c332a28:
  FAIL dashboard did not render (no 'Routine Watch' in DOM)
Interface: reproduce with `scripts/integration.sh`; logs in `.dev/api.log` / `.dev/web.log`. Fix the cause (not the check) unless the check itself is wrong.
Acceptance:
- `scripts/integration.sh` prints OK; `scripts/ci.sh` passes.

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

### T373 — Docs: CODEMAP note that web tests share one default WebSocket stub
- status: todo
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

### T379 — Test: shift handoff Print button works keyboard-only
- status: claimed
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/handoff/Handoff.keyboard.test.tsx
- owner: max_API_light
- claimed: 2026-10-17T19:36Z
- pr: —

What: T203 added a "Print handoff" button; the keyboard-only test (T294/T321) predates it. Cover it so a nurse without a mouse can print.
Interface: read only web/src/handoff/Handoff.keyboard.test.tsx, web/src/handoff/Handoff.tsx and the 'Print handoff' test near line 171 of web/src/handoff/Handoff.test.tsx (stub `window.print` the same way). No production code changes.
Acceptance:
- Tabbing from "Copy summary" reaches "Print handoff"; Enter and Space each call `window.print` once.
- `cd web && npx vitest run src/handoff/Handoff.keyboard.test.tsx` passes; `scripts/ci.sh` passes.

### T380 — Dashboard: dark theme for night shift (prefers-color-scheme)
- status: todo
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
- status: claimed
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/ContextTimeline.tsx, web/src/resident/contextTimeline.css, web/src/resident/ContextTimeline.mobile.test.tsx
- owner: Max_codex_light
- claimed: 2026-10-17T19:36Z
- pr: —

What: Same treatment as the other phone-width tasks (e.g. T345 session list): the care-record timeline on resident detail must not overflow at 375 px.
Interface: read only web/src/resident/ContextTimeline.tsx, web/src/resident/SessionList.mobile.test.tsx and web/src/resident/sessionList.css (copy their approach). Add a `contextTimeline.css` imported by the component; wrap long labels, stack date above text under 480 px.
Acceptance:
- New ContextTimeline.mobile.test.tsx in the style of SessionList.mobile.test.tsx.
- `cd web && npx vitest run src/resident/ContextTimeline` passes; `scripts/ci.sh` passes.

### T384 — Ghost replay: aria-label says what is being compared
- status: claimed
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/evidence/GhostReplay.tsx, web/src/evidence/GhostReplay.test.tsx
- owner: ian-claude-heavy-2
- claimed: 2026-10-17T19:41Z
- pr: —

What: The ghost replay SVG's label is the fixed "Today and usual skeleton replay"; a screen-reader user gets no information. Describe the comparison in words.
Interface: read only web/src/evidence/GhostReplay.tsx and its test. Build the label from the props already passed (e.g. "Today's routine drawn over the usual routine, frame 12 of 40"); if a prop you'd need doesn't exist, keep to what's there. No new props from other files.
Acceptance:
- Test asserts the label changes with the frame and never contains "diagnos".
- `cd web && npx vitest run src/evidence/GhostReplay` passes; `scripts/ci.sh` passes.

### T385 — Docs: CODEMAP notes for overview filter counts and remembered prefs
- status: todo
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

### T386 — Test: demo banner reset works keyboard-only
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/ui/DemoBanner.keyboard.test.tsx
- owner: —
- claimed: —
- pr: —

What: The presenter resets the demo from the banner; it must work without a mouse like every other screen's keyboard test.
Interface: read only web/src/ui/DemoBanner.tsx, web/src/ui/DemoBanner.test.tsx (reuse its fetch stub) and web/src/about/PrivacyPanel.keyboard.test.tsx (style). No production code changes.
Acceptance:
- Tab reaches the reset button; Enter and Space each trigger one reset request; focus stays visible on the button afterwards.
- `cd web && npx vitest run src/ui/DemoBanner` passes; `scripts/ci.sh` passes.

### T387 — Test: guided tour works keyboard-only
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/tour/Tour.keyboard.test.tsx
- owner: —
- claimed: —
- pr: —

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
- status: todo
- class: light
- priority: 2
- kind: test
- source: reviewer
- deps: —
- area: web/src/about/PrivacyPanel.mobile.test.tsx
- owner: —
- claimed: —
- pr: —

What: the T369 test sets `window.innerWidth = 375` and only asserts class names exist; jsdom ignores innerWidth and `privacyPanel.css` is stubbed in Vitest, so deleting the whole `@media (max-width: 480px)` block still passes.
Interface: read `src/about/privacyPanel.css` with `vi.importActual('node:fs').readFileSync` (same as `web/src/tour/Tour.test.tsx`) and assert the `@media (max-width: 480px)` block contains `.privacy-panel__list` with `word-break: break-word`; drop the innerWidth line (and don't leave it mutated for other tests). Only this test file.
Acceptance:
- Removing the @media block from `privacyPanel.css` makes the test fail
- `cd web && npm test` and `scripts/ci.sh` pass

### T390 — Docs: CODEMAP note for scripts/preflight.sh
- status: todo
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

### T391 — Preflight: write step logs to a temp dir, not fixed /tmp paths
- status: todo
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

### T392 — Test: scripts/camera.sh argument handling (no camera needed)
- status: claimed
- class: standard
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_camera_script.py
- owner: max_API_standard
- claimed: 2026-10-17T19:39Z
- pr: —
- note: released by ian-claude-standard: run ended without progress; partial work on branch task/T392-wip-1934: start from it (git switch task/T392-wip-1934 && git merge origin/main)

What: scripts/camera.sh (T356) has no tests. Cover the parts that run before any install or camera: `--help` prints the header usage, unknown args and a non-numeric `--camera` exit 2 with a message, missing values for `--camera`/`--record` fail.
Interface: new pytest file running `bash scripts/camera.sh ...` via subprocess with a short timeout; must never reach the pip install / camera / dev.sh steps (only invoke paths that exit during argument parsing).
Acceptance:
- tests for --help (exit 0, usage text), unknown arg (exit 2), `--camera abc` (exit 2), `--camera` with no value (non-zero)
- no network, no camera, no stack started
- `scripts/ci.sh` passes

### T393 — Landing page: usable at phone width (375 px)
- status: todo
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

### T394 — Live: tell the nurse when the camera could not be opened (close code 4503)
- status: claimed
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/live/useLiveSession.ts, web/src/live/useLiveSession.test.ts, web/src/live/LiveSession.tsx, web/src/live/LiveSession.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T19:50Z
- pr: —
- note: partial work pushed on branch task/T394-camera-unavailable (worker retired mid-task): start from it: git switch task/T394-camera-unavailable && git merge origin/main

What: `/ws/live?source=camera` closes with 4503 (`live_camera.CAMERA_UNAVAILABLE`) when no camera can be read (T356). Make sure the Live screen shows a plain, specific message for that code ("No camera could be opened on this machine — run scripts/camera.sh, or watch a recorded session") with a button back to the recorded scenario, distinct from "API unreachable" and 4404.
Interface: map close code 4503 to its own state in useLiveSession; render via the shared ui ErrorState/Button. If this already exists, tighten tests only.
Acceptance:
- unit test with the fake WebSocket closing 4503 shows the camera message and a working "watch a recorded session" button
- 4404 and network-error messages unchanged (existing tests pass)
- `cd web && npm test` and `scripts/ci.sh` pass

### T395 — Docs: CODEMAP note for live camera source and scripts/camera.sh
- status: todo
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

### T396 — Flag outcomes: unit-wide confirmed vs false-alarm counts per pattern
- status: todo
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

### T397 — Test: live WebSocket path and offline replay flag the same scenario the same way
- status: claimed
- class: heavy
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_live_replay_parity.py
- owner: ian-claude-heavy-3
- claimed: 2026-10-17T19:38Z
- pr: —

What: The live screen comes from live.py and the alert view from replay.py; nothing checks they agree. For every single-session scenario under tests/scenarios/, compare the errors and change flag in live `session_messages(...)`'s session_end message with `replay.run(load_scenario(...))`.
Interface: read pipeline/src/routine_watch/live.py (session_messages, as_json), replay.py (run), scenario.py (load_scenario). Test only: if a scenario disagrees, mark it `xfail(strict=True)` with the reason and list it in the PR body; don't change pipeline code.
Acceptance:
- `cd pipeline && pytest tests/test_live_replay_parity.py` passes quickly (fake clock, no real sleeps).
- `scripts/ci.sh` passes.

### T398 — Test: landing page works keyboard-only
- status: todo
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

### T399 — Smoke: check the landing page is served
- status: todo
- class: standard
- priority: 2
- kind: test
- deps: —
- area: scripts/smoke.sh
- owner: —
- claimed: —
- pr: —

What: `scripts/smoke.sh` checks the dashboard at `/` returns HTML but not the public landing page `/landing.html` (T378, second Vite entry in `web/vite.config.ts`), so a broken landing build would go unnoticed before the demo.
Interface: add one check next to the existing `GET $DASHBOARD_URL -> HTML` block (~line 233): `GET $DASHBOARD_URL/landing.html` must return HTML containing `Routine Watch`; use the existing `get`/`pass`/`fail` helpers. Update the header comment listing what it checks.
Acceptance:
- With `scripts/dev.sh up`, `scripts/smoke.sh` passes and prints the new pass line; with the landing entry removed from the build it fails with a readable message.
- `bash -n scripts/smoke.sh` and `scripts/ci.sh` pass.

### T400 — Docs: DEMO.md points judges at the landing page
- status: todo
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
