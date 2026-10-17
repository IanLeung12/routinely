# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: f59e5ba

## Tasks

### T386 — Test: demo banner reset works keyboard-only
- status: done
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
- status: done
- class: light
- priority: 2
- kind: test
- source: reviewer
- deps: —
- area: web/src/about/PrivacyPanel.mobile.test.tsx
- owner: max_API_standard
- claimed: 2026-10-17T20:02Z
- pr: #385
- rating: 5/5 clear

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
- status: done
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
- status: done
- class: heavy
- priority: 0
- kind: improvement
- deps: —
- area: docs/DESIGN.md, web/src/index.css, web/src/ui/
- owner: ian-claude-heavy-3
- claimed: 2026-10-17T20:21Z
- pr: #387
- rating: 4/5 clear brief and good starting observations; the only gap was where before/after screenshots should live on a private repo (raw links don't render), so I committed them under docs/design/ which is just outside the stated area

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

### T403 — Redesign 3/6: unit overview + app shell
- status: todo
- class: standard
- priority: 1
- kind: improvement
- deps: T401
- area: web/src/overview/, web/src/App.tsx, web/src/App.test.tsx
- owner: —
- claimed: —
- pr: —

What: (Starts after T401; if the chart kit (T417–T419) hasn't merged yet, keep existing chart components and only restyle their containers; a follow-up swaps the charts.) Make the overview read like Fey's watchlist: one card, dense resident rows (name + room, status pill, top pattern in muted text, MicroBars trend, score pill right-aligned), sort/filter as small segmented pills. App shell: compact top bar (product name, unit, offline/demo indicator) and a floating rounded nav dock for the main screens, following `docs/DESIGN.md`. Check Fey refs via the mobbin MCP (watchlist, home).
Acceptance: keyboard nav and existing behaviour unchanged (tests updated for structure only); flagged resident still understood in 10 s; before/after screenshot in PR; `scripts/ci.sh` passes.

### T404 — Redesign 4/6: resident detail
- status: todo
- class: standard
- priority: 1
- kind: improvement
- deps: T401, T421, T422
- area: web/src/resident/ResidentDetail.tsx, web/src/resident/SessionList.tsx, web/src/resident/ContextTimeline.tsx, web/src/resident/*.css, web/src/resident/ResidentDetail.test.tsx
- owner: —
- claimed: —
- pr: —

What: Fey "stock detail" layout for a resident: header (name, status pill, top pattern), hero BaselineChart card with range selector, then a two-column grid of cards (heat calendar, sessions as dense rows with error pills, care-record timeline with tinted markers for new meds/fever). Faint warm vignette background per `docs/DESIGN.md`.
Acceptance: same data and states (loading/empty/error) as now; before/after screenshot; `scripts/ci.sh` passes.

### T405 — Redesign 5/6: alert / evidence view
- status: claimed
- class: standard
- priority: 1
- kind: improvement
- deps: T401
- area: web/src/alert/, web/src/evidence/, web/src/patterns/
- owner: ian-claude-heavy-3
- claimed: 2026-10-17T20:48Z
- pr: —

What: (Starts after T401; if the chart kit (T417–T419) hasn't merged yet, keep existing chart components and only restyle their containers; a follow-up swaps the charts.) The "why" screen judges score most. Summary as a Fey "daily recap" card (short bold summary, muted detail); "Possible patterns" as ranked cards with confidence bars and rule-out checks; errors as dense timestamped rows with type pills (red/amber/grey); replay and ghost replay in a dark media card; Confirm / False alarm as clear buttons. Keep "consistent with", never "diagnosis".
Acceptance: readable in 10 s (one glance: what changed, how sure, what to check); tests updated for structure only; before/after screenshot; `scripts/ci.sh` passes.

### T406 — Redesign 6/6: live session + handoff
- status: todo
- class: standard
- priority: 2
- kind: improvement
- deps: T401
- area: web/src/live/, web/src/handoff/
- owner: —
- claimed: —
- pr: —

What: (Starts after T401; if the chart kit (T417–T419) hasn't merged yet, keep existing chart components and only restyle their containers; a follow-up swaps the charts.) Live screen as a dark media card (skeleton view) beside the task map styled as a vertical step list with Fey-style pills (done/green, error/red, repeat/amber, unclear/grey) and a slim progress line; shift handoff as dense rows with delta pills ("+2 vs last shift").
Acceptance: live updates still animate; tests updated for structure only; before/after screenshot; `scripts/ci.sh` passes.

### T407 — Redesign: landing page onto the Fey-inspired system
- status: todo
- class: standard
- priority: 2
- kind: improvement
- deps: T401, T417
- area: web/src/landing/, web/landing.html
- owner: —
- claimed: —
- pr: —

What: The landing page (T378) predates the redesign. Restyle it per `docs/DESIGN.md`: dark premium hero, one real chart from the chart kit (a resident's score vs personal baseline band, with the end-of-line tag) as the hero visual, sections as hairline cards. Check Fey refs via the mobbin MCP. Copy unchanged unless it breaks the layout.
Acceptance: mobile + desktop screenshots (before/after) in the PR; landing tests still pass; `scripts/ci.sh` passes.

### T408 — Roles: role chooser, role-aware shell, mock people/linking API
- status: todo
- class: heavy
- priority: 1
- kind: feature
- source: ian
- deps: —
- area: web/src/people/, web/src/App.tsx, web/src/App.test.tsx, web/src/mock/people.ts
- owner: —
- claimed: —
- pr: #388
- rating: 4/5 clear on the API and routing; didn't say who the supervisor 'I' am (Nurse Ana with the whole unit, or Lena with one) - that choice decides whether the existing nurse flow stays the default, and Mr. D/Sam have no pipeline data so their detail screen is empty
- note: merge conflict with main on PR #388: check out its branch, merge origin/main, fix, push

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
- **Notes** when a change is flagged: the same patterns, rephrased for the person ("Some steps took longer than usual for you, mostly in the evening. Worth mentioning to Lena or your doctor."), with a "tell my supervisor" button (mock). Use `personNote`/`personStatus` from `web/src/person/personNotes.ts` (T423) if merged.
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
- status: claimed
- class: heavy
- priority: 1
- kind: feature
- source: ian
- deps: —
- area: pipeline/src/routine_watch/replays.py, pipeline/src/routine_watch/session_log.py, pipeline/src/routine_watch/live.py, pipeline/src/routine_watch/live_camera.py, pipeline/src/routine_watch/api_residents.py, pipeline/src/routine_watch/evidence.py, pipeline/src/routine_watch/demo.py, pipeline/tests/test_replays.py
- owner: ian-claude
- claimed: 2026-10-17T20:18Z
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

### T414 — Bug: resident detail still shows the old threshold after "Confirmed" changes it
- status: done
- class: light
- priority: 1
- kind: bug
- source: tester
- deps: —
- area: pipeline/src/routine_watch/api_state.py, pipeline/tests/test_api_feedback_threshold.py
- owner: ian-claude-standard
- claimed: 2026-10-17T20:22Z
- pr: #386
- rating: 5/5 clear

What: After a nurse clicks "Confirmed" on Mrs. K's alert, the alert view shows "Current threshold: 2.3" (was 2.4), but going back to Mrs. K's resident detail the baseline chart still says "flag threshold 2.4". `api_state._tuned()` recomputes `status`/`top_pattern` against the feedback-tuned threshold but returns `baseline.threshold` unchanged, so `/residents` and `/residents/{id}` disagree with the alert payload (SPEC MVP 7: threshold visibly changes).
Repro (OFFLINE_MODE=true): `scripts/dev.sh up` → dashboard → let the Making tea live replay finish → Open alert → Confirmed (shows 2.3) → reload, open Mrs. K → chart aria-label "Baseline chart: ... flag threshold 2.4".
Expected: resident detail/overview show the same tuned threshold as the alert (2.3). Actual: raw baseline threshold 2.4.
Interface: `_tuned()` also returns `baseline: {**resident["baseline"], "threshold": <tuned>}`; no contract change.
Acceptance:
- pytest: after confirm feedback via the API, `GET /residents/mrs-k` `baseline.threshold` equals the alert's threshold; with no feedback it is unchanged
- `scripts/ci.sh` passes

### T415 — Deploy: Docker images + compose for API and dashboard (Vultr-ready)
- status: in-review
- class: standard
- priority: 1
- kind: feature
- deps: —
- area: deploy/, docs/DEPLOY.md, .dockerignore
- owner: max_API_standard
- claimed: 2026-10-17T20:35Z
- pr: #391
- rating: 4/5 Clear deployment interface; worker lacks Docker, so acceptance ran on an isolated GitHub Actions Linux runner.

What: SPEC §5/§16-C says the backend (FastAPI + dashboard) is hosted on Vultr, but the repo has no container or deploy setup, so the judges' demo URL can't be stood up quickly. Add a reproducible container build that a human can run on any Docker host (Vultr VM) with one command. Don't provision cloud resources or buy domains; humans do that.
Interface:
- `deploy/api.Dockerfile`: Python image, `uv sync` of `pipeline/` (no `capture` extra), runs `uvicorn routine_watch.api:app --host 0.0.0.0 --port 8000`; non-root user; healthcheck on an existing GET route.
- `deploy/web.Dockerfile`: multi-stage, `npm ci && npm run build` in `web/` with build arg `VITE_API_URL`, served by nginx (both `/` and `/landing.html`), SPA fallback to `index.html`.
- `deploy/docker-compose.yml`: `api` + `web` (+ optional `db` timescale service under a `tsdb` profile, used only when `DATABASE_URL` points at it); env from `.env` (`env_file`), defaults `OFFLINE_MODE=true`, `LIVE_API=0`; `CORS_ORIGINS` set to the web origin; replay/data dirs on a named volume.
- `docs/DEPLOY.md` (≤60 lines): build/run commands, which `.env` vars matter in prod, how to point a domain + TLS (Caddy or similar, described not committed), and the privacy rule (no video stored).
- `.dockerignore`: excludes node_modules, .venv, .cache, .data, .dev, .env, models/.
Acceptance:
- `docker compose -f deploy/docker-compose.yml up -d --build` then `DASHBOARD_URL=http://localhost:<web port> API_URL=http://localhost:8000 scripts/smoke.sh` passes (paste the output in the PR); `docker compose ... down` cleans up.
- No secrets in images (`.env` not copied); `scripts/ci.sh` passes.
- If you add a module or script, add a CODEMAP note in this PR.

### T416 — Local camera preview: real video + skeleton overlay, this device only
- status: todo
- class: heavy
- priority: 1
- kind: feature
- source: ian
- deps: T424
- area: pipeline/src/routine_watch/capture.py, pipeline/src/routine_watch/preview.py, pipeline/tests/test_preview.py, scripts/camera.sh, web/src/live/LiveSession.tsx, web/src/live/LiveSession.test.tsx, docs/DEMO.md, SPEC.md
- owner: —
- claimed: —
- pr: —

What: Ian wants to see the actual camera picture during a live session, not just the skeleton. Keep the privacy promise: video never leaves the capture machine, is never stored, never reaches the API or a remote supervisor.
Why: the demo is far more convincing with the real kitchen and the skeleton tracking on top, and it helps frame the camera for Roboflow training clips.
Interface:
- `preview.py`: an MJPEG endpoint served by the **capture process itself**, bound to `127.0.0.1` only (`PREVIEW_PORT`, default 8765), off unless `CAMERA_PREVIEW=1` / `scripts/camera.sh --preview`. Frames come from the same capture loop (one camera handle; Windows can't open the webcam twice), downscaled (≤640 px, ~10 fps), held in memory for the current frame only, never written to disk. Refuses non-loopback clients.
- Web (`web/src/live/`): "Show camera preview (this device only)" toggle on the Live screen, shown only when the page is on localhost and the preview responds. Video underneath, the existing skeleton + boxes canvas on top, aligned to the same coordinates; a visible "Preview · not recorded · this device only" badge. Falls back to skeleton-only everywhere else, quietly.
- `scripts/camera.sh --preview` turns it on and prints the URL; `docs/DEMO.md` explains it; SPEC §12/§16 gets one line: optional local preview, loopback only, never stored or transmitted.
Split (orch): the web toggle/overlay component is T424 (`web/src/live/CameraPreview.tsx`). This task serves `GET /preview.mjpg` and `GET /health` → `{"ok": true}` with `Access-Control-Allow-Origin: *` on the loopback server, and wires `<CameraPreview>` around the existing `<SkeletonView>` in `LiveSession.tsx`.
Acceptance:
- Tests: preview rejects a non-loopback client; nothing under the repo or `REPLAY_DIR`/`CAMERA_RECORD` contains image data after a session with preview on (privacy test); capture still writes the same JSONL with preview on or off.
- Web test: toggle hidden when not on localhost or preview unreachable; badge shown when on.
- `scripts/ci.sh` passes without opencv/mediapipe installed (lazy imports).

### T417 — Chart kit: LineChart + RangeSelector (Fey style)
- status: todo
- class: standard
- priority: 1
- kind: improvement
- source: ian
- deps: T401
- area: web/src/ui/charts/LineChart.tsx, web/src/ui/charts/LineChart.test.tsx, web/src/ui/charts/RangeSelector.tsx, web/src/ui/charts/RangeSelector.test.tsx, web/src/ui/charts/scale.ts, web/src/ui/charts/scale.test.ts, web/src/ui/charts/charts.css
- owner: —
- claimed: —
- pr: —

What: Split from T402 so the chart kit is built in parallel. Dependency-free SVG `LineChart` per `docs/DESIGN.md`: thin 1.25–1.5px line, at most a faint gradient, a few hairline/dashed gridlines, tiny muted axis labels, **end-of-line value tag** (pill with the latest value), optional **baseline band** (mean ± threshold), optional dotted comparison series, hover/focus crosshair + tooltip, keyboard focus across points. `RangeSelector` (7D 14D 30D) on `SegmentedControl`. `scale.ts`: linear/time scales and "nice" ticks. Check Fey chart refs via the mobbin MCP (see T401).
Acceptance: accessible name + text alternative (summary line); tests for ticks, end tag = latest value, band drawn only when given, keyboard focus; `cd web && npm test && npm run build`.

### T418 — Chart kit: BarChart (paired bars + callout)
- status: claimed
- class: light
- priority: 1
- kind: improvement
- source: ian
- deps: T401
- area: web/src/ui/charts/BarChart.tsx, web/src/ui/charts/BarChart.test.tsx
- owner: Max_codex_light
- claimed: 2026-10-17T20:48Z
- pr: —

What: Split from T402. Read only `docs/DESIGN.md`, `web/src/index.css` (tokens) and `web/src/ui/` primitives. SVG `BarChart`: slim rounded bars, optional second series muted/outlined beside each bar (e.g. this week vs usual), optional callout pill above one highlighted bar (`callout={{index, label: "2.4× usual"}}`), tiny muted labels, tokens only (no hex). Props: `data: {label: string, value: number, compare?: number}[]`, `ariaLabel`, `highlight?`. Self-contained (own min/max scaling; don't import `scale.ts`).
Acceptance: renders N bars; compare series only when present; callout shows its label; has an accessible name and a visually hidden data table; `cd web && npx vitest run src/ui/charts/BarChart.test.tsx`.

### T419 — Chart kit: MicroBars (14-day tick strip)
- status: todo
- class: light
- priority: 1
- kind: improvement
- source: ian
- deps: T401
- area: web/src/ui/charts/MicroBars.tsx, web/src/ui/charts/MicroBars.test.tsx
- owner: —
- claimed: —
- pr: —

What: Split from T402. Read only `docs/DESIGN.md` and `web/src/index.css`. A row of thin vertical ticks (like Fey's sector rows), one per day, height = score, colour by status token (normal / watch / flagged; missing day = faint hairline). Props: `days: {date: string, score: number | null, status: 'normal'|'watch'|'flagged'}[]`, `ariaLabel`. Fixed small size (~84×20) for list rows.
Acceptance: one tick per day; null days render as hairlines; status colours via tokens; accessible name summarises "14 days, 2 flagged"; `cd web && npx vitest run src/ui/charts/MicroBars.test.tsx`.

### T420 — Restyle: overview Sparkline → MicroBars
- status: todo
- class: light
- priority: 1
- kind: improvement
- source: ian
- deps: T419
- area: web/src/overview/Sparkline.tsx, web/src/overview/Sparkline.test.tsx
- owner: —
- claimed: —
- pr: —

What: Split from T402. Make `Sparkline` render `MicroBars` (web/src/ui/charts/MicroBars.tsx) from the same input it takes today; keep its props and export so callers don't change. Read only those files and `web/src/overview/types.ts`.
Acceptance: existing Sparkline tests pass (update selectors only); `cd web && npx vitest run src/overview`.

### T421 — Restyle: BaselineChart + drift card on LineChart
- status: todo
- class: standard
- priority: 1
- kind: improvement
- source: ian
- deps: T417
- area: web/src/resident/BaselineChart.tsx, web/src/resident/BaselineChart.test.tsx, web/src/resident/*Drift*.tsx, web/src/resident/*Drift*.test.tsx
- owner: —
- claimed: —
- pr: —

What: Split from T402. `BaselineChart` → `LineChart` with the personal baseline band, end-of-line tag and `RangeSelector`; the slow-drift card → `LineChart` with a dotted trend series. Same props and data as today.
Acceptance: existing tests pass (selectors only); before/after screenshot of Mrs. K in the PR; `cd web && npm test`.

### T422 — Restyle: HeatCalendar in the Fey palette
- status: todo
- class: light
- priority: 1
- kind: improvement
- source: ian
- deps: T401
- area: web/src/resident/HeatCalendar.tsx, web/src/resident/HeatCalendar.test.tsx, web/src/resident/heatCalendar.css
- owner: —
- claimed: —
- pr: —

What: Split from T402. Read only `docs/DESIGN.md`, `web/src/index.css` and the HeatCalendar files. Muted Fey palette: tinted cells from the status tokens, hairline gaps, small rounded cells, muted weekday labels, legend as small pills. No hex in the component; behaviour unchanged.
Acceptance: existing HeatCalendar tests pass (selectors only); `cd web && npx vitest run src/resident/HeatCalendar.test.tsx`.

### T423 — Person view: person-facing wording for status and pattern notes
- status: claimed
- class: light
- priority: 1
- kind: feature
- source: orch (carved from T409)
- deps: —
- area: web/src/person/personNotes.ts, web/src/person/personNotes.test.ts
- owner: max_API_light
- claimed: 2026-10-17T20:45Z
- pr: —

What: Pure functions that turn existing nurse-facing data into calm, personal copy for someone watching themselves (SPEC §17 "Person view"). T409 ("My routine") will consume them.
Why: inherits T409 — the person view is half of the roles pivot judges will see.
Read only: `web/src/contracts.ts` (type `PatternMatch`, ~line 374), `web/src/wording.test.ts` (style of the existing wording checks).
Interface (`web/src/person/personNotes.ts`):
- `personStatus(state: 'normal' | 'watch' | 'flagged'): string` — e.g. normal "Your routine looks like your usual this week", watch "A few things looked a little different lately", flagged "A few things looked different today".
- `personNote(match: PatternMatch, supervisorName?: string): { title: string; body: string }` — one entry per pattern_id: `sudden_change`, `slow_drift`, `evening_worsening`, `motor_slowing`, `executive_pattern`, `one_sided_change`, plus a generic fallback for unknown ids. Describe what was different in everyday words ("Some steps took longer than usual, mostly in the evening") and end with "Worth mentioning to <supervisorName> or your doctor." (or "Worth mentioning to your doctor or someone you trust." without a name). Never reuse the nurse-facing `name` (it has clinical terms like "delirium").
Acceptance:
- `web/src/person/personNotes.test.ts` (Vitest): every pattern id + the fallback returns non-empty title/body; with and without supervisor name; for all outputs, case-insensitive: no "diagnos", "patient", "delirium", "dementia", "stroke", "danger", "warning", "emergency", "urgent".
- `cd web && npx vitest run src/person/personNotes.test.ts` and `scripts/ci.sh` pass.

### T424 — Live screen: local camera preview component (toggle, video under skeleton, badge)
- status: in-review
- class: light
- priority: 1
- kind: feature
- source: orch (carved from T416)
- deps: —
- area: web/src/live/CameraPreview.tsx, web/src/live/CameraPreview.test.tsx
- owner: ian-claude-standard-3
- claimed: 2026-10-17T20:47Z
- pr: #389
- rating: 5/5 clear

What: A self-contained React component for T416's local-only camera preview. Not wired into any screen here (T416 does that).
Why: inherits T416 — the demo is far more convincing with the real kitchen under the skeleton.
Read only: `web/src/live/SkeletonView.tsx` (renders an `<svg>` sized `width`×`height`, default 480×360).
Interface (`web/src/live/CameraPreview.tsx`):
- `export function CameraPreview({ port = 8765, children, probe }: { port?: number; children: React.ReactNode; probe?: () => Promise<boolean> })`.
- Default probe: only if `window.location.hostname` is `localhost`, `127.0.0.1` or `::1`, `fetch('http://127.0.0.1:<port>/health')` with a 1 s timeout (AbortController); true when it returns `{ ok: true }`. Any error → false, no console noise.
- Probe false: render `children` only (no toggle, nothing else).
- Probe true: a toggle button "Show camera preview (this device only)" (`aria-pressed`). On: an `<img src="http://127.0.0.1:<port>/preview.mjpg" alt="">` fills the box, `children` absolutely positioned on top at the same size, and a visible badge "Preview · not recorded · this device only". Off: children only.
Acceptance:
- `CameraPreview.test.tsx` (Vitest + Testing Library, inject `probe`): toggle hidden when probe false; hidden on a non-localhost hostname with the default probe (mock `fetch`, assert not called); toggle on shows img + badge + children; toggle off removes img; button keyboard operable.
- `cd web && npx vitest run src/live/CameraPreview.test.tsx` and `scripts/ci.sh` pass.

### T425 — Review: handoff summary counts unclear-camera rooms as "nothing to review"
- status: in-review
- class: light
- priority: 1
- kind: bug
- source: reviewer
- deps: —
- area: pipeline/src/routine_watch/handoff.py, pipeline/tests/test_handoff_unclear.py
- owner: ian-claude-standard
- claimed: 2026-10-17T20:47Z
- pr: #390
- rating: 5/5 clear

What: T355 added `unclear_sessions` to each handoff row and a chip on screen, but `_context()` in `handoff.py` still counts a resident whose room had unclear sessions (and no flags) in "N residents with nothing to review", so the summary a nurse reads says the room was quiet while the row says check the camera — the exact silence T355 meant to fix.
Fix: in `_context()`, add one line per resident with `unclear_sessions > 0` (e.g. "<name>: N sessions too unclear to score, check the camera view", camera wording, nothing about the resident) and exclude them from the `quiet` count. Keep `_needs_review` unchanged (unclear is not a flag).
Acceptance:
- Test in `test_handoff_unclear.py`: with one unclear session recorded for a quiet resident's room, the explainer context mentions the camera line and the quiet count drops by one.
- `scripts/ci.sh` passes.
