# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: fa8034b

## Tasks

### T355 — Shift handoff: say when a room's capture was too unclear to score this shift
- status: in-review
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
- status: claimed
- class: standard
- priority: 0
- kind: bug
- deps: —
- area: scripts/integration.sh, scripts/dev.sh
- owner: ian-claude-heavy-3
- claimed: 2026-10-17T19:59Z
- pr: —
- source: integration
- note: area narrowed (was web/src/, which overlapped claims and kept this P0 from being handed out). T388 (#370) stopped integration.sh sharing/killing a running dev stack, a likely cause; first re-run scripts/integration.sh on main twice and, if both print OK, mark done with a note. If it is Vite cold-start timing, make integration.sh wait for Vite readiness. If the render itself is broken, note the file and set blocked so a web task can be filed.

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
- status: in-review
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
- status: claimed
- class: light
- priority: 2
- kind: test
- source: reviewer
- deps: —
- area: web/src/about/PrivacyPanel.mobile.test.tsx
- owner: max_API_standard
- claimed: 2026-10-17T20:02Z
- pr: —

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
- status: in-review
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
- status: todo
- class: heavy
- priority: 0
- kind: improvement
- deps: —
- area: docs/DESIGN.md, web/src/index.css, web/src/ui/
- owner: —
- claimed: —
- pr: —

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

### T402 — Redesign 2/6: chart kit in Fey style + restyle existing charts
- status: todo
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

### T403 — Redesign 3/6: unit overview + app shell
- status: todo
- class: standard
- priority: 1
- kind: improvement
- deps: T401, T402
- area: web/src/overview/, web/src/App.tsx, web/src/App.test.tsx
- owner: —
- claimed: —
- pr: —

What: Make the overview read like Fey's watchlist: one card, dense resident rows (name + room, status pill, top pattern in muted text, MicroBars trend, score pill right-aligned), sort/filter as small segmented pills. App shell: compact top bar (product name, unit, offline/demo indicator) and a floating rounded nav dock for the main screens, following `docs/DESIGN.md`. Check Fey refs via the mobbin MCP (watchlist, home).
Acceptance: keyboard nav and existing behaviour unchanged (tests updated for structure only); flagged resident still understood in 10 s; before/after screenshot in PR; `scripts/ci.sh` passes.

### T404 — Redesign 4/6: resident detail
- status: todo
- class: standard
- priority: 1
- kind: improvement
- deps: T401, T402
- area: web/src/resident/ResidentDetail.tsx, web/src/resident/SessionList.tsx, web/src/resident/ContextTimeline.tsx, web/src/resident/*.css, web/src/resident/ResidentDetail.test.tsx
- owner: —
- claimed: —
- pr: —

What: Fey "stock detail" layout for a resident: header (name, status pill, top pattern), hero BaselineChart card with range selector, then a two-column grid of cards (heat calendar, sessions as dense rows with error pills, care-record timeline with tinted markers for new meds/fever). Faint warm vignette background per `docs/DESIGN.md`.
Acceptance: same data and states (loading/empty/error) as now; before/after screenshot; `scripts/ci.sh` passes.

### T405 — Redesign 5/6: alert / evidence view
- status: todo
- class: standard
- priority: 1
- kind: improvement
- deps: T401, T402
- area: web/src/alert/, web/src/evidence/, web/src/patterns/
- owner: —
- claimed: —
- pr: —

What: The "why" screen judges score most. Summary as a Fey "daily recap" card (short bold summary, muted detail); "Possible patterns" as ranked cards with confidence bars and rule-out checks; errors as dense timestamped rows with type pills (red/amber/grey); replay and ghost replay in a dark media card; Confirm / False alarm as clear buttons. Keep "consistent with", never "diagnosis".
Acceptance: readable in 10 s (one glance: what changed, how sure, what to check); tests updated for structure only; before/after screenshot; `scripts/ci.sh` passes.

### T406 — Redesign 6/6: live session + handoff
- status: todo
- class: standard
- priority: 2
- kind: improvement
- deps: T401, T402
- area: web/src/live/, web/src/handoff/
- owner: —
- claimed: —
- pr: —

What: Live screen as a dark media card (skeleton view) beside the task map styled as a vertical step list with Fey-style pills (done/green, error/red, repeat/amber, unclear/grey) and a slim progress line; shift handoff as dense rows with delta pills ("+2 vs last shift").
Acceptance: live updates still animate; tests updated for structure only; before/after screenshot; `scripts/ci.sh` passes.

### T407 — Redesign: landing page onto the Fey-inspired system
- status: todo
- class: standard
- priority: 2
- kind: improvement
- deps: T401, T402
- area: web/src/landing/, web/landing.html
- owner: —
- claimed: —
- pr: —

What: The landing page (T378) predates the redesign. Restyle it per `docs/DESIGN.md`: dark premium hero, one real chart from the chart kit (a resident's score vs personal baseline band, with the end-of-line tag) as the hero visual, sections as hairline cards. Check Fey refs via the mobbin MCP. Copy unchanged unless it breaks the layout.
Acceptance: mobile + desktop screenshots (before/after) in the PR; landing tests still pass; `scripts/ci.sh` passes.

### T408 — Roles: role chooser, role-aware shell, mock people/linking API
- status: claimed
- class: heavy
- priority: 1
- kind: feature
- source: ian
- deps: —
- area: web/src/people/, web/src/App.tsx, web/src/App.test.tsx, web/src/mock/people.ts
- owner: ian-claude-heavy-2
- claimed: 2026-10-17T20:14Z
- pr: —

What: Ian's pivot (SPEC §3, §17): the app is for anyone, not just nurses. Two roles: **person** (watches themselves) and **supervisor** (family, carer or nurse). Frontend only; no pairing backend.
Interface:
- `web/src/people/api.ts`: `getRole()/setRole('person'|'supervisor')`, `currentPerson()`, `supervisorsOf(personId)`, `peopleISupport()`, `createInvite(personId) -> {code, link}`, `acceptInvite(code)`, `unlink(personId, supervisorId)`. Backed by localStorage + `web/src/mock/people.ts` (Mrs. K ← Nurse Ana; Mr. D ← his daughter Lena; Sam self-monitoring, no supervisor). Keep it an interface so a real API can replace it.
- First-open **role chooser** ("I'm setting this up for myself" / "I'm supporting someone"), remembered; a role switcher in the shell; "Reset demo" clears it.
- Routing in `App.tsx`: person → `MyRoutine` placeholder (T409 fills it); supervisor → existing overview, but with exactly one supported person it opens straight into their detail.
Acceptance:
- Vitest: chooser shows on first open and not after; switching roles changes the home screen; invite create/accept/unlink round-trips through the mock.
- Existing nurse/care-home flow still works as the supervisor-with-many case; `scripts/ci.sh` passes.

### T409 — Person view: "My routine"
- status: todo
- class: heavy
- priority: 1
- kind: feature
- source: ian
- deps: T408
- area: web/src/person/
- owner: —
- claimed: —
- pr: —

What: What someone watching themselves sees (SPEC §17). Calm and personal; never alarming or diagnostic. Use the mobbin MCP for 2–3 references of calm personal health/habit dashboards (and follow `docs/DESIGN.md` if it has landed).
Interface (`web/src/person/MyRoutine.tsx` + pieces):
- Status in plain words ("Your routine looks like your usual this week" / "A few things looked different today").
- One chart: my usual vs today/this week (reuse existing chart components or the chart kit if merged).
- Recent sessions (task, time, what went smoothly / what was different).
- **Notes** when a change is flagged: the same patterns, rephrased for the person ("Some steps took longer than usual for you, mostly in the evening. Worth mentioning to Lena or your doctor."), with a "tell my supervisor" button (mock).
- **Who can see this**: supervisors list with remove; "Invite someone" (shows the invite code + copy link from T408's API); self-monitoring state when there's nobody.
- Privacy: pause monitoring, "what's stored" (skeletons only, no video), and "your supervisors see exactly this".
Acceptance:
- Vitest for each section incl. no-supervisor and flagged states; wording test: no "diagnos", no "patient", no alarm words ("danger", "warning", "emergency") in person-facing copy.
- Keyboard + screen-reader friendly; mobile width works; `scripts/ci.sh` passes. Screenshot in PR.

### T410 — Supervisor side: "People I support" + add a person
- status: todo
- class: standard
- priority: 1
- kind: feature
- source: ian
- deps: T408
- area: web/src/supporting/, web/src/overview/UnitOverview.tsx, web/src/overview/UnitOverview.test.tsx
- owner: —
- claimed: —
- pr: —

What: Generalise the nurse overview into "People I support" (SPEC §17). Care-home supervisor sees the unit list as today; a family supervisor with one person goes straight to that person; anyone can **add a person** by entering an invite code (T408's mock API), with a clear "linked" confirmation. Each row/detail shows the person's context ("care home · Room 12" vs "lives alone").
Acceptance: Vitest for many/one/zero supported people and the add-by-code flow; existing overview behaviour kept for the care-home case; `scripts/ci.sh` passes. Screenshot in PR.

### T411 — Wording pass: people, not just residents and nurses
- status: todo
- class: light
- priority: 2
- kind: improvement
- source: ian
- deps: T408, T409, T410
- area: web/src/alert/, web/src/resident/, web/src/handoff/, web/src/landing/, web/src/wording.test.ts
- owner: —
- claimed: —
- pr: —

What: Make shared UI copy role-neutral per SPEC §17: "resident" → "person" (or the person's name), "nurse" only where it's specifically the care-home supervisor, never "patient". Landing page: say it's for anyone, alone or with family, a carer or a care home.
Acceptance: `web/src/wording.test.ts` extended to fail on "patient" and on "nurse" outside an allow-list of care-home-specific strings; all tests pass; `scripts/ci.sh` passes.

### T412 — Replay store: keep skeleton replays of every session with errors
- status: todo
- class: heavy
- priority: 1
- kind: feature
- source: ian
- deps: —
- area: pipeline/src/routine_watch/replays.py, pipeline/src/routine_watch/session_log.py, pipeline/src/routine_watch/live.py, pipeline/src/routine_watch/live_camera.py, pipeline/src/routine_watch/api_residents.py, pipeline/src/routine_watch/evidence.py, pipeline/src/routine_watch/demo.py, pipeline/tests/test_replays.py
- owner: —
- claimed: —
- pr: —

What: Ian wants supervisors (and the person) to look back at failed attempts and judge for themselves (SPEC §17). Today replays exist only inside an alert and come from two canned recordings; live sessions keep steps and errors but not frames. Store a replay for every session that had at least one error (and keep the person's most recent normal session as the comparison). Skeletons, hand landmarks, object boxes and timestamps only, downsampled (~10 fps); never video (SPEC §8).
Interface:
- `replays.py`: `ReplayStore` interface with in-memory default and an on-disk JSONL.gz implementation (`REPLAY_DIR`, default `.data/replays/`); `save(session, frames, errors)`, `list(person_id, since=None, error_type=None) -> [ReplaySummary]`, `get(session_id) -> Replay` (frames + error markers with t_start/t_end/type/step), `delete(session_id)`, retention `REPLAY_RETENTION_DAYS` (default 30) pruned on save. Shape as contracts (`ReplaySummary`, `Replay`, `ReplayMarker`) and regenerate TS.
- Live and camera sessions save on `session_end` when errors > 0; demo/synthetic people get generated replays for their bad sessions (reuse `stick_figure` where no landmarks), so the library isn't empty in the demo.
- API: `GET /people/{person_id}/replays?type=&since=`, `GET /replays/{session_id}` (frames + markers, supersedes the alert-only path; keep `/sessions/{id}/replay` working), `DELETE /replays/{session_id}`.
Acceptance:
- Tests: a session with errors is saved and listed, a clean session is not; markers line up with the error timestamps; retention prunes; delete works; no image/video fields can be stored (privacy test).
- `scripts/ci.sh` + `scripts/e2e.sh` pass.

### T413 — Replays library for supervisors and the person
- status: todo
- class: standard
- priority: 1
- kind: feature
- source: ian
- deps: T412
- area: web/src/replays/, web/src/evidence/ReplayPlayer.tsx, web/src/evidence/ReplayPlayer.test.tsx, web/src/mock/replays.ts
- owner: —
- claimed: —
- pr: —

What: A "Replays" screen where a supervisor can browse a person's sessions that had errors and analyse them, and the person can see (and delete) their own (SPEC §17: they see exactly what supervisors see). Use the mobbin MCP for 2–3 references of video/recording libraries and timeline scrubbers; follow `docs/DESIGN.md` if merged.
Interface:
- List: per person, newest first, each row = date/time, task, error pills (omission/sequence/repeat/…), duration; filter by error type and date range; empty state ("No sessions with errors in the last 30 days").
- Player (extend `ReplayPlayer`): skeleton + object boxes, **timeline with error markers** (click to jump), play/pause/speed (0.5×/1×/2×), step labels as it plays, optional ghost overlay of the person's normal session, frame-by-frame with arrow keys.
- Supervisor notes on a replay (local/mock, shown with author + time); person view shows "Delete this replay".
- Entry points: from a person's detail ("Replays"), from an alert's error rows, and from "My routine" for the person.
- Offline/mock fallback in `web/src/mock/replays.ts`.
Acceptance: Vitest for list/filter/empty, marker jump, speed, delete, notes; keyboard operable; screenshot in PR; `scripts/ci.sh` passes.
