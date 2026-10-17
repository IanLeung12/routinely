# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: 6b93111

## Tasks

### T403 — Redesign 3/6: unit overview + app shell
- status: in-review
- class: standard
- priority: 0
- kind: improvement
- deps: T401
- area: web/src/overview/, web/src/App.tsx, web/src/App.test.tsx
- owner: ian-claude-standard-3
- claimed: 2026-10-17T21:01Z
- pr: #404
- rating: 4/5 clear task, but it landed just as T408 (role chooser / role-aware shell) merged into main and also rewrote App.tsx's header, which the task description didn't anticipate; had to merge origin/main mid-task and hand-reconcile the two shells

What: (Starts after T401; if the chart kit (T417–T419) hasn't merged yet, keep existing chart components and only restyle their containers; a follow-up swaps the charts.) Make the overview read like Fey's watchlist: one card, dense resident rows (name + room, status pill, top pattern in muted text, MicroBars trend, score pill right-aligned), sort/filter as small segmented pills. App shell: compact top bar (product name, unit, offline/demo indicator) and a floating rounded nav dock for the main screens, following `docs/DESIGN.md`. Check Fey refs via the mobbin MCP (watchlist, home).
Acceptance: keyboard nav and existing behaviour unchanged (tests updated for structure only); flagged resident still understood in 10 s; before/after screenshot in PR; `scripts/ci.sh` passes.

### T404 — Redesign 4/6: resident detail
- status: todo
- class: standard
- priority: 0
- kind: improvement
- deps: T401, T421, T422
- area: web/src/resident/ResidentDetail.tsx, web/src/resident/SessionList.tsx, web/src/resident/ContextTimeline.tsx, web/src/resident/*.css, web/src/resident/ResidentDetail.test.tsx
- owner: —
- claimed: —
- pr: —

What: Fey "stock detail" layout for a resident: header (name, status pill, top pattern), hero BaselineChart card with range selector, then a two-column grid of cards (heat calendar, sessions as dense rows with error pills, care-record timeline with tinted markers for new meds/fever). Faint warm vignette background per `docs/DESIGN.md`.
Acceptance: same data and states (loading/empty/error) as now; before/after screenshot; `scripts/ci.sh` passes.

### T406 — Redesign 6/6: live session + handoff
- status: claimed
- class: standard
- priority: 0
- kind: improvement
- deps: T401
- area: web/src/live/, web/src/handoff/Handoff.tsx, web/src/handoff/handoff.css, web/src/handoff/Handoff.test.tsx, web/src/handoff/Handoff.keyboard.test.tsx, web/src/handoff/Handoff.defaults.test.tsx
- owner: ian-claude-heavy-2
- claimed: 2026-10-17T21:41Z
- pr: —
- note: Delta pills split out to T428 (HandoffDelta on Pill); just keep using <HandoffDelta>.

What: (Starts after T401; if the chart kit (T417–T419) hasn't merged yet, keep existing chart components and only restyle their containers; a follow-up swaps the charts.) Live screen as a dark media card (skeleton view) beside the task map styled as a vertical step list with Fey-style pills (done/green, error/red, repeat/amber, unclear/grey) and a slim progress line; shift handoff as dense rows with delta pills ("+2 vs last shift").
Acceptance: live updates still animate; tests updated for structure only; before/after screenshot; `scripts/ci.sh` passes.

### T407 — Redesign: landing page onto the Fey-inspired system
- status: in-review
- class: standard
- priority: 0
- kind: improvement
- deps: T401, T417
- area: web/src/landing/, web/landing.html
- owner: ian-claude
- claimed: 2026-10-17T21:28Z
- pr: #405
- rating: 4/5 clear; the only judgement call was that the chart kit's band is symmetric around the mean, so an error score needs data whose mean is well above 2 sigma to avoid a negative lower bound

What: The landing page (T378) predates the redesign. Restyle it per `docs/DESIGN.md`: dark premium hero, one real chart from the chart kit (a resident's score vs personal baseline band, with the end-of-line tag) as the hero visual, sections as hairline cards. Check Fey refs via the mobbin MCP. Copy unchanged unless it breaks the layout.
Acceptance: mobile + desktop screenshots (before/after) in the PR; landing tests still pass; `scripts/ci.sh` passes.

### T409 — Person view: "My routine"
- status: claimed
- class: heavy
- priority: 0
- kind: feature
- source: ian
- deps: T408
- area: web/src/people/MyRoutine.tsx, web/src/people/MyRoutine.test.tsx, web/src/person/routine/
- owner: ian-claude-heavy-3
- claimed: 2026-10-17T21:23Z
- pr: —
- note: T408 already shipped a basic MyRoutine in web/src/people/MyRoutine.tsx; extend it there, put new pieces under web/src/person/routine/ (own CSS file, not people.css). Use PrivacyCard (T429) and personNotes (T423).

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
- priority: 0
- kind: feature
- source: ian
- deps: T408
- area: web/src/people/PeopleISupport.tsx, web/src/people/PeopleISupport.test.tsx, web/src/supporting/, web/src/overview/UnitOverview.tsx, web/src/overview/UnitOverview.test.tsx
- owner: —
- claimed: —
- pr: —
- note: T408 already shipped PeopleISupport (list + add by code) in web/src/people/; extend it there; Person.context already holds the context line; new CSS under web/src/supporting/, not people.css.

What: Generalise the nurse overview into "People I support" (SPEC §17). Care-home supervisor sees the unit list as today; a family supervisor with one person goes straight to that person; anyone can **add a person** by entering an invite code (T408's mock API), with a clear "linked" confirmation. Each row/detail shows the person's context ("care home · Room 12" vs "lives alone").
Acceptance: Vitest for many/one/zero supported people and the add-by-code flow; existing overview behaviour kept for the care-home case; `scripts/ci.sh` passes. Screenshot in PR.

### T411 — Wording pass: people, not just residents and nurses
- status: todo
- class: light
- priority: 1
- kind: improvement
- source: ian
- deps: T408, T409, T410
- area: web/src/alert/, web/src/resident/, web/src/handoff/, web/src/landing/, web/src/wording.test.ts
- owner: —
- claimed: —
- pr: —

What: Make shared UI copy role-neutral per SPEC §17: "resident" → "person" (or the person's name), "nurse" only where it's specifically the care-home supervisor, never "patient". Landing page: say it's for anyone, alone or with family, a carer or a care home.
Acceptance: `web/src/wording.test.ts` extended to fail on "patient" and on "nurse" outside an allow-list of care-home-specific strings; all tests pass; `scripts/ci.sh` passes.

### T427 — Replays data layer: API client + mock fixture for the replays library
- status: in-review
- class: light
- priority: 0
- kind: feature
- deps: T412
- area: web/src/replays/api.ts, web/src/replays/api.test.ts, web/src/mock/replays.ts
- owner: max_API_light
- claimed: 2026-10-17T21:11Z
- pr: #403
- rating: 4/5 Repeat marker wording differs from contract perseveration; otherwise clear

What: The fetch layer T413's Replays screen will consume, carved out of T413 so the screen task only builds UI. Backend routes landed in T412.
Interface: in `web/src/replays/api.ts` export `fetchPersonReplays(personId): Promise<PersonReplays>`, `fetchReplay(replayId): Promise<Replay>`, `deleteReplay(replayId): Promise<void>`, calling `GET /people/{id}/replays`, `GET /replays/{id}`, `DELETE /replays/{id}`. Follow the base-URL/offline-fallback pattern in `web/src/evidence/api.ts` exactly (fall back to the mock when the API is unreachable or in offline mode). Types `PersonReplays`, `ReplaySummary`, `Replay`, `ReplayMarker` already exist in `web/src/contracts.ts` (~lines 431–510); do not change contracts. `web/src/mock/replays.ts`: 3 replays for Mrs. K (omission, sequence, repeat markers), 1 for Mr. D, 0 for Sam, plus one `normal` summary; skeleton frames only, no images.
Files to read: `web/src/evidence/api.ts`, `web/src/evidence/api.test.ts`, `web/src/contracts.ts` (replay types), `web/src/mock/replay.ts`, `web/src/mock/people.ts` (person ids), `pipeline/src/routine_watch/api_residents.py` lines 179–260 (route shapes).
Acceptance:
- Vitest in `web/src/replays/api.test.ts`: success path (mocked fetch), fallback to mock on network error, delete sends DELETE, Sam returns an empty list.
- `cd web && npx vitest run src/replays` and `scripts/ci.sh` pass.

### T413 — Replays library for supervisors and the person
- status: todo
- class: standard
- priority: 0
- kind: feature
- source: ian
- deps: T412, T427, T430, T431
- area: web/src/replays/Replays.tsx, web/src/replays/Replays.test.tsx, web/src/replays/replays.css, web/src/evidence/ReplayPlayer.tsx, web/src/evidence/ReplayPlayer.test.tsx, web/src/mock/replays.ts, web/src/App.tsx
- note: list + filters (T430) and notes (T431) are carved out as components; compose them here, don't rewrite them.
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

### T416 — Local camera preview: real video + skeleton overlay, this device only
- status: done
- class: heavy
- priority: 0
- kind: feature
- source: ian
- deps: T424
- area: pipeline/src/routine_watch/capture.py, pipeline/src/routine_watch/preview.py, pipeline/tests/test_preview.py, scripts/camera.sh, web/src/live/LiveSession.tsx, web/src/live/LiveSession.test.tsx, docs/DEMO.md, SPEC.md
- owner: ian-claude-heavy-2
- claimed: 2026-10-17T21:04Z
- pr: #399
- rating: 4/5 clear: the only gap was that the split left the T424 component's video layout cropping the picture (object-fit: cover), so 'aligned to the same coordinates' needed a 3-line CSS fix outside the listed area; also worth saying the preview server starts with the camera, so the web probe has to wait for the first frame

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
- status: done
- class: standard
- priority: 0
- kind: improvement
- source: ian
- deps: T401
- area: web/src/ui/charts/LineChart.tsx, web/src/ui/charts/LineChart.test.tsx, web/src/ui/charts/RangeSelector.tsx, web/src/ui/charts/RangeSelector.test.tsx, web/src/ui/charts/scale.ts, web/src/ui/charts/scale.test.ts, web/src/ui/charts/charts.css
- owner: max_API_standard
- claimed: 2026-10-17T21:02Z
- pr: #397
- rating: 5/5 clear

What: Split from T402 so the chart kit is built in parallel. Dependency-free SVG `LineChart` per `docs/DESIGN.md`: thin 1.25–1.5px line, at most a faint gradient, a few hairline/dashed gridlines, tiny muted axis labels, **end-of-line value tag** (pill with the latest value), optional **baseline band** (mean ± threshold), optional dotted comparison series, hover/focus crosshair + tooltip, keyboard focus across points. `RangeSelector` (7D 14D 30D) on `SegmentedControl`. `scale.ts`: linear/time scales and "nice" ticks. Check Fey chart refs via the mobbin MCP (see T401).
Acceptance: accessible name + text alternative (summary line); tests for ticks, end tag = latest value, band drawn only when given, keyboard focus; `cd web && npm test && npm run build`.

### T418 — Chart kit: BarChart (paired bars + callout)
- status: done
- class: light
- priority: 0
- kind: improvement
- source: ian
- deps: T401
- area: web/src/ui/charts/BarChart.tsx, web/src/ui/charts/BarChart.test.tsx
- owner: Max_codex_light
- claimed: 2026-10-17T20:48Z
- pr: #394
- rating: 5/5 clear

What: Split from T402. Read only `docs/DESIGN.md`, `web/src/index.css` (tokens) and `web/src/ui/` primitives. SVG `BarChart`: slim rounded bars, optional second series muted/outlined beside each bar (e.g. this week vs usual), optional callout pill above one highlighted bar (`callout={{index, label: "2.4× usual"}}`), tiny muted labels, tokens only (no hex). Props: `data: {label: string, value: number, compare?: number}[]`, `ariaLabel`, `highlight?`. Self-contained (own min/max scaling; don't import `scale.ts`).
Acceptance: renders N bars; compare series only when present; callout shows its label; has an accessible name and a visually hidden data table; `cd web && npx vitest run src/ui/charts/BarChart.test.tsx`.

### T419 — Chart kit: MicroBars (14-day tick strip)
- status: done
- class: light
- priority: 0
- kind: improvement
- source: ian
- deps: T401
- area: web/src/ui/charts/MicroBars.tsx, web/src/ui/charts/MicroBars.test.tsx
- owner: ian-claude
- claimed: 2026-10-17T21:04Z
- pr: #398
- rating: 5/5 clear

What: Split from T402. Read only `docs/DESIGN.md` and `web/src/index.css`. A row of thin vertical ticks (like Fey's sector rows), one per day, height = score, colour by status token (normal / watch / flagged; missing day = faint hairline). Props: `days: {date: string, score: number | null, status: 'normal'|'watch'|'flagged'}[]`, `ariaLabel`. Fixed small size (~84×20) for list rows.
Acceptance: one tick per day; null days render as hairlines; status colours via tokens; accessible name summarises "14 days, 2 flagged"; `cd web && npx vitest run src/ui/charts/MicroBars.test.tsx`.

### T420 — Restyle: overview Sparkline → MicroBars
- status: todo
- class: light
- priority: 0
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
- status: claimed
- class: standard
- priority: 0
- kind: improvement
- source: ian
- deps: T417
- area: web/src/resident/BaselineChart.tsx, web/src/resident/BaselineChart.test.tsx, web/src/resident/*Drift*.tsx, web/src/resident/*Drift*.test.tsx
- owner: ian-claude-standard-4
- claimed: 2026-10-17T21:37Z
- pr: —

What: Split from T402. `BaselineChart` → `LineChart` with the personal baseline band, end-of-line tag and `RangeSelector`; the slow-drift card → `LineChart` with a dotted trend series. Same props and data as today.
Acceptance: existing tests pass (selectors only); before/after screenshot of Mrs. K in the PR; `cd web && npm test`.

### T422 — Restyle: HeatCalendar in the Fey palette
- status: done
- class: light
- priority: 0
- kind: improvement
- source: ian
- deps: T401
- area: web/src/resident/HeatCalendar.tsx, web/src/resident/HeatCalendar.test.tsx, web/src/resident/heatCalendar.css
- owner: ian-claude-standard
- claimed: 2026-10-17T21:27Z
- pr: #401
- note: released by ian-claude-standard-4: run ended without progress; partial work on branch task/T422-wip-2122: start from it (git switch task/T422-wip-2122 && git merge origin/main)
- rating: 5/5 clear

What: Split from T402. Read only `docs/DESIGN.md`, `web/src/index.css` and the HeatCalendar files. Muted Fey palette: tinted cells from the status tokens, hairline gaps, small rounded cells, muted weekday labels, legend as small pills. No hex in the component; behaviour unchanged.
Acceptance: existing HeatCalendar tests pass (selectors only); `cd web && npx vitest run src/resident/HeatCalendar.test.tsx`.

### T423 — Person view: person-facing wording for status and pattern notes
- status: done
- class: light
- priority: 1
- kind: feature
- source: orch (carved from T409)
- deps: —
- area: web/src/person/personNotes.ts, web/src/person/personNotes.test.ts
- owner: max_API_light
- claimed: 2026-10-17T20:45Z
- pr: #393
- rating: 5/5 clear

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
- status: done
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
- status: done
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

### T426 — Bug: integration check still flaky ("dashboard did not render" on a cold start)
- status: done
- class: standard
- priority: 0
- kind: bug
- source: ian
- deps: —
- area: scripts/integration.sh, scripts/dev.sh
- owner: ian-claude-standard
- claimed: 2026-10-17T21:00Z
- pr: #396
- rating: 5/5 clear, found a real latent gap in the render check while verifying the acceptance criterion

What: T367 didn't fully fix it. The hourly integration check and the tester both see `FAIL dashboard did not render (no 'Routine Watch' in DOM)` on the first run after `dev.sh up`, then pass on a re-run: Vite's cold dependency optimisation finishes after headless Chrome's 8 s budget.
Why: a red integration check the morning of the demo (due 13:00 UTC) hides real breakage.
Interface: in `scripts/integration.sh`, warm the dev server before the render check (fetch `/`, `/src/main.tsx` and wait until a second fetch of the page is fast) and retry the DOM check up to 3 times with a longer budget; or render against `vite preview` of a built `dist/` instead of the dev server. Don't weaken the check (it must still fail if the app really doesn't render).
Acceptance: `scripts/dev.sh down && scripts/integration.sh` passes 5 times in a row from cold; breaking `web/src/main.tsx` on purpose makes it fail.

### T428 — Handoff: delta chip onto the Pill primitive
- status: done
- class: light
- priority: 1
- kind: improvement
- source: orch (carved from T406)
- deps: —
- area: web/src/handoff/HandoffDelta.tsx, web/src/handoff/HandoffDelta.css, web/src/handoff/HandoffDelta.test.tsx
- owner: Max_codex_light
- claimed: 2026-10-17T21:17Z
- pr: #400
- rating: 5/5 clear

What: Render `<HandoffDelta>` with the redesign's `Pill` (`web/src/ui/Pill.tsx`) instead of its own CSS chip, so handoff rows get Fey-style delta pills.
Why: inherits T406 — the handoff screen is on the demo path and should match the redesign.
Read only: `web/src/handoff/HandoffDelta.tsx`, `web/src/handoff/HandoffDelta.test.tsx`, `web/src/ui/Pill.tsx`.
Interface: keep `HandoffDelta({flags, previousFlags})` and `handoffDeltaLabel(...)` signatures and every label string unchanged. Mapping: more → `<Pill tone="negative" direction="up">`, fewer → `tone="positive" direction="down"`, same → `tone="neutral"` (no direction). Keep a `handoff-delta` class on the pill (via `className`) so existing selectors in `Handoff.tsx` tests still find it. Delete `HandoffDelta.css` if nothing else imports it (`grep -r HandoffDelta.css web/src`).
Acceptance:
- Tests updated: each tone renders the matching `pill--<tone>` class and the same label text; nothing rendered when `previousFlags` is null/undefined.
- `cd web && npx vitest run src/handoff` and `scripts/ci.sh` pass.

### T429 — Person view: privacy card (pause, what's stored, who sees it)
- status: done
- class: light
- priority: 1
- kind: feature
- source: orch (carved from T409)
- deps: —
- area: web/src/person/PrivacyCard.tsx, web/src/person/PrivacyCard.test.tsx, web/src/person/privacyCard.css
- owner: max_API_standard
- claimed: 2026-10-17T21:28Z
- pr: #402
- rating: 5/5 clear

What: A self-contained card T409 ("My routine") will drop in. Not wired into any screen here.
Why: inherits T409 — "skeletons only, no video" is the privacy story judges ask about.
Read only: `web/src/ui/Card.tsx`, `web/src/ui/Button.tsx`, `web/src/ui/SectionHeader.tsx`, `web/src/person/personNotes.test.ts` (wording-check style).
Interface: `export function PrivacyCard({ paused, onTogglePause, supervisorNames }: { paused: boolean; onTogglePause: () => void; supervisorNames: string[] })`.
- Heading "Your privacy". Pause button: "Pause watching" / "Resume watching" (`aria-pressed={paused}`); when paused a line "Watching is paused. Nothing is recorded until you resume."
- "What's stored": "Body outlines (skeletons) and timings only. No video or photos ever leave this device or get saved."
- Who sees it: with names → "Lena and Sam see exactly what you see here." (join 1/2/3+ names naturally); with none → "Only you can see this."
- Own CSS in `privacyCard.css` using tokens from `web/src/index.css`.
Acceptance:
- Vitest: paused/unpaused text + `aria-pressed`, click calls `onTogglePause`, 0/1/2/3 supervisor names; no "diagnos", "patient", "danger", "warning", "emergency" in rendered text.
- `cd web && npx vitest run src/person/PrivacyCard.test.tsx` and `scripts/ci.sh` pass.

### T430 — Replays: list with error-type filter and empty state (component)
- status: claimed
- class: light
- priority: 0
- kind: feature
- deps: —
- area: web/src/replays/ReplayList.tsx, web/src/replays/ReplayList.test.tsx, web/src/replays/replayList.css
- owner: Max_codex_light
- claimed: 2026-10-17T21:43Z
- pr: —

What: Carved from T413 (Ian's replays library). A presentational list of a person's replays that T413's screen will drop in. No fetching, no routing.
Interface: `export function ReplayList(props: { replays: ReplaySummary[]; normal?: ReplaySummary | null; onOpen: (sessionId: string) => void })`. Rows newest first: date/time (from `started_at`), `task_id`, one `Pill` per `error_types` entry (labels from `web/src/ui/errorTypes.ts`), duration as "m:ss". Above the list a filter (`SegmentedControl` from `web/src/ui/`): "All" plus each error type that appears; filtering is local state. If `normal` is given, show it last, labelled "Most recent normal session (for comparison)". Empty state via `web/src/ui/EmptyState.tsx`: "No sessions with errors in the last 30 days". Each row is a button calling `onOpen(session_id)`.
Files to read: `web/src/contracts.ts` lines 425–535 (`PersonReplays`, `ReplaySummary`), `web/src/ui/Pill.tsx`, `web/src/ui/Row.tsx`, `web/src/ui/SegmentedControl.tsx`, `web/src/ui/EmptyState.tsx`, `web/src/ui/errorTypes.ts`, `docs/DESIGN.md` (tokens only). Use CSS vars from `web/src/index.css`; no new colours.
Acceptance:
- Vitest in `ReplayList.test.tsx`: newest-first order, filter narrows rows and "All" restores, empty state text, normal row shown last with its label, clicking a row calls `onOpen` with the id, rows reachable by Tab and activated by Enter.
- No "diagnos"/"patient" in copy. `cd web && npx vitest run src/replays/ReplayList` and `scripts/ci.sh` pass.

### T431 — Replays: supervisor notes on a replay (component, local only)
- status: claimed
- class: light
- priority: 1
- kind: feature
- deps: —
- area: web/src/replays/ReplayNotes.tsx, web/src/replays/ReplayNotes.test.tsx, web/src/replays/replayNotes.css
- owner: ian-claude-standard
- claimed: 2026-10-17T21:47Z
- pr: —

What: Carved from T413. Supervisors leave short notes on a replay, shown with author and time; the person sees the same notes (SPEC §17: they see exactly what supervisors see). Local state only, no API.
Interface: `export type ReplayNote = { id: string; author: string; at: string; text: string }`; `export function ReplayNotes(props: { notes: ReplayNote[]; canAdd: boolean; author: string; onAdd: (note: ReplayNote) => void; now?: () => Date })`. Lists notes oldest first ("Author · 21:40", time from `at`); when `canAdd`, a labelled textarea + "Add note" `Button` (disabled on empty/whitespace, trims text, clears after add). Empty: "No notes yet."
Files to read: `web/src/ui/Button.tsx`, `web/src/ui/Card.tsx`, `web/src/ui/SectionHeader.tsx`, `docs/DESIGN.md` (tokens only); CSS vars from `web/src/index.css`.
Acceptance:
- Vitest: notes in order with author + time, add flow calls `onAdd` with trimmed text and the given author, button disabled on blank input, `canAdd=false` hides the form, empty text shown.
- `cd web && npx vitest run src/replays/ReplayNotes` and `scripts/ci.sh` pass.

### T432 — Task map as a Postman Flows–style node graph
- status: todo
- class: standard
- priority: 0
- kind: improvement
- source: ian
- deps: T406
- area: web/src/live/TaskMap.tsx, web/src/live/TaskMap.test.tsx, web/src/live/taskMap.css, web/src/live/TaskMapLegend.tsx, web/src/live/TaskMapLegend.test.tsx
- owner: —
- claimed: —
- pr: —

What: Ian wants the task map to look like **Postman Flows** (node-graph canvas). Use the mobbin MCP (`search_screens` / `search_flows` "Postman Flows") to study 2–3 references first and name them in the PR. Render the task graph (steps + deps from the task YAML, already sent over /ws/live) as rounded node cards on a dotted canvas, connected by smooth curved edges with small ports; parallel branches side by side (e.g. fill kettle ∥ get cup), optional steps dashed. Live state on each node: pending (muted), done (green check), current (glow/pulse), error (red, with the error type pill: omission/sequence/repeat/substitution), unclear (grey). Edges into an errored step turn red/amber. Fits the Fey-style tokens from `docs/DESIGN.md`.
Why: the task map is the centrepiece of the live demo shot; a flow canvas makes "dependencies, not a fixed order" obvious at a glance.
Interface: dependency-free SVG/HTML (no graph libraries); a simple layered layout (topological levels left→right) computed from deps; same props and data as today's TaskMap; keyboard/screen-reader: nodes are a list with state in their accessible names.
Acceptance: renders tea and meds graphs without overlaps; state changes animate; existing TaskMap tests pass (selectors only) + a layout test (parallel steps share a level); screenshot in PR; `cd web && npm test && npm run build`.

### T433 — Redesign follow-up: pattern library onto the Fey system
- status: claimed
- class: light
- priority: 1
- kind: improvement
- deps: T401
- area: web/src/patterns/PatternLibrary.tsx, web/src/patterns/PatternLibrary.css, web/src/patterns/urgencyFilter.css, web/src/patterns/PatternLibrary.test.tsx, web/src/patterns/PatternLibrary.filters.test.tsx, web/src/patterns/PatternLibrary.keyboard.test.tsx
- owner: max_API_light
- claimed: 2026-10-17T21:58Z
- pr: —

What: The pattern library still uses the pre-redesign tokens (`--panel`, `--border`, `--muted`, `--accent`) and its own boxes. Rebuild its markup on the ui primitives (`Card`, `SectionHeader`, `Row`, `Pill`, `SegmentedControl` for the urgency filter) and the new tokens only. Read only `docs/DESIGN.md`, `web/src/ui/README.md`, `web/src/index.css` and the files in area.
Why: judges click into "consistent with" patterns from the alert; it's the one demo screen that still looks like the old app.
Interface: same exports/props as today; same data from `web/src/patterns/api.ts` and `mockPatterns.ts` (don't edit those).
Acceptance:
- no legacy tokens (`--panel`, `--border`, `--muted`, `--bg`) and no hex/px literals in the two CSS files;
- wording unchanged ("consistent with", never "diagnose");
- existing tests pass (update selectors only, keep behaviour); `cd web && npx vitest run src/patterns && npm run lint`.

### T434 — Redesign follow-up: guided tour card on the Fey system
- status: todo
- class: light
- priority: 2
- kind: improvement
- deps: T401
- area: web/src/tour/Tour.tsx, web/src/tour/tour.css, web/src/tour/Tour.test.tsx, web/src/tour/Tour.keyboard.test.tsx
- owner: —
- claimed: —
- pr: —

What: Restyle the guided-tour card: `--surface-raised`, `--hairline-strong`, `--radius-lg`, the one allowed float shadow (DESIGN.md principle 3), `Button` from `web/src/ui/Button.tsx` for next/back/close. Read only `docs/DESIGN.md`, `web/src/ui/README.md`, `web/src/index.css` and the files in area. Don't touch `steps.ts`.
Why: the tour is the first thing a judge sees on the dashboard; it should match the redesigned screens under it.
Interface: same `Tour` props/exports; behaviour and keyboard handling unchanged.
Acceptance:
- tokens only, no hex/px literals in `tour.css`;
- existing tests pass (selectors only); `cd web && npx vitest run src/tour && npm run lint`.

### T435 — Redesign follow-up: privacy panel + monitoring toggle on the Fey system
- status: todo
- class: light
- priority: 2
- kind: improvement
- deps: T401
- area: web/src/about/PrivacyPanel.tsx, web/src/about/MonitoringToggle.tsx, web/src/about/privacyPanel.css, web/src/about/PrivacyPanel.test.tsx, web/src/about/PrivacyPanel.keyboard.test.tsx, web/src/about/PrivacyPanel.mobile.test.tsx, web/src/about/MonitoringToggle.test.tsx, web/src/about/MonitoringToggle.keyboard.test.tsx
- owner: —
- claimed: —
- pr: —

What: Move the supervisor-side privacy panel and the pause-monitoring toggle onto the new tokens and primitives (`Card`, `SectionHeader`, `Row` for each "what's stored" line, `Button` for the toggle). Don't edit `monitoringApi.ts` or `ResidentDetail.tsx` (T404 owns it). Read only `docs/DESIGN.md`, `web/src/ui/README.md`, `web/src/index.css` and the files in area.
Why: privacy (skeletons only, no video) is a judging talking point; the panel that says so is still in the old style.
Interface: same exports/props; same text.
Acceptance:
- no legacy tokens (`--muted`, `--panel`, `--border`) and no hex/px literals in `privacyPanel.css`;
- existing tests pass (selectors only, keep the phone-width wrapping assertion meaningful); `cd web && npx vitest run src/about && npm run lint`.

### T436 — Review: camera preview MJPEG readable by any website open on the capture machine
- status: claimed
- class: light
- priority: 0
- kind: bug
- source: reviewer
- deps: —
- area: pipeline/src/routine_watch/preview.py, pipeline/tests/test_preview.py
- owner: max_API_standard
- claimed: 2026-10-17T21:56Z
- pr: —

What: `preview.py` sends `Access-Control-Allow-Origin: *` on every reply, including `/preview.mjpg`. The loopback/Host checks don't stop a cross-site `fetch('http://127.0.0.1:8765/preview.mjpg')`: the browser runs on this machine (client is loopback) and sends `Host: 127.0.0.1:8765` (passes). So any web page open in that browser can read live camera frames and upload them — raw video leaving the machine, against SPEC §8/§12.
Fix: in `response_for`, take the request's `Origin` header (pass it from `_Handler.do_GET`); if present and its host is not loopback (`is_loopback(urlparse(origin).hostname)`), return 403. Echo the allowed loopback origin in `Access-Control-Allow-Origin` (plus `Vary: Origin`) instead of `*`; send no CORS header when there's no Origin. `<img src>` in `CameraPreview` still works (no CORS needed).
Acceptance:
- Tests in `test_preview.py`: `Origin: https://evil.example` → 403 on `/preview.mjpg` and `/health`; `Origin: http://localhost:5173` → 200 with that origin echoed; no Origin → 200; the existing `== "*"` asserts updated.
- `scripts/ci.sh` passes.

### T437 — Routine builder backend: draft a routine from words or a setup video (Gemini)
- status: todo
- class: heavy
- priority: 0
- kind: feature
- source: ian
- deps: —
- area: pipeline/src/routine_watch/routine_builder.py, pipeline/src/routine_watch/api_routines.py, pipeline/src/routine_watch/api.py, pipeline/src/routine_watch/tasks/graph.py, pipeline/tests/test_routine_builder.py, pipeline/tests/fixtures/routine_builder/, .env.example
- owner: —
- claimed: —
- pr: —

What: Ian's routine builder (option 1): a person or supervisor creates a new routine either by describing it in words or by uploading **one setup clip** of themselves doing it. Gemini (video understanding) or Claude (text) drafts the steps; code turns the draft into a valid task graph (same schema as `tasks/tea.yaml`) that the task map, error classifier and scoring already read.
Why: shows the approach generalises beyond tea and makes strong use of Gemini (prize) in a 20-second demo shot.
Privacy (SPEC §8, §12): the clip is a **one-time, opt-in setup step**. The request must carry `consent: true`; the video is held in memory (or a temp file deleted in `finally`), sent to Gemini once, never written to `REPLAY_DIR`/`CAMERA_RECORD`/the repo, never logged. Daily monitoring stays skeleton-only. Add one line to SPEC §12 saying exactly this.
Interface:
- `routine_builder.py`: `draft_from_text(description) -> RoutineDraft`, `draft_from_video(bytes, mime) -> RoutineDraft`, `to_task_graph(draft) -> dict` (ids slugged, deps only to earlier-known steps, objects mapped to known detector classes where they match, unknown objects kept and listed as `needs_training`), validated by `tasks/graph.py`'s loader (`parse_task`). Prompt asks for JSON only: steps (label, objects, depends_on, optional, once_only). Both providers behind an interface with a **fake default**; real calls only with `LIVE_API=1` through `api_cache.cached_call`, cheapest models (`GEMINI_MODEL`, `ANTHROPIC_MODEL`). Video: inline for clips ≤20 MB, reject longer than ~60 s or larger.
- **Offline/demo:** with `LIVE_API` unset, return canned drafts from `pipeline/tests/fixtures/routine_builder/` (e.g. "brush teeth", "make toast") picked by keyword, so the demo works on the offline try-out link.
- `api_routines.py`: `POST /routines/draft` (multipart: `description` or `video` + `consent=true`) → `{draft, task_graph, needs_training, warnings}`; `POST /routines` saves a reviewed graph (in-memory + `ROUTINES_DIR` JSON, default `.data/routines/`); `GET /routines` lists built-in + saved; `GET /routines/{id}`.
Acceptance:
- Tests with the fake: text → valid graph; video without `consent` → 400; video bytes never touch disk outside a deleted temp file (privacy test asserts nothing new under the repo/data dirs); invalid LLM JSON → clear 422; unknown objects listed in `needs_training`.
- `scripts/ci.sh` passes without network.

### T438 — Routine builder UI: describe it or upload a setup clip → editable task map → save
- status: todo
- class: standard
- priority: 0
- kind: feature
- source: ian
- deps: —
- area: web/src/routines/, web/src/mock/routines.ts, web/src/App.tsx
- owner: —
- claimed: —
- pr: —

What: The front end for T437, built in parallel against the API shape in T437's Interface with a mock (`web/src/mock/routines.ts`) so it doesn't wait for T437. Follow `docs/DESIGN.md`; check 2–3 Mobbin references for "create from upload / AI builder" flows.
Interface (`web/src/routines/`):
- "New routine" entry from the shell (both roles).
- Two tabs: **Describe it** (textarea + examples) and **From a video** (file picker, max ~60 s; a consent checkbox that must be ticked: "This clip is sent once to Google Gemini to draft the steps. It is not stored. Day-to-day monitoring never sends video."). Progress state while drafting.
- Result: the drafted routine shown as a task map (reuse `web/src/live/TaskMap`), plus an editable step list (rename, reorder deps, toggle optional, delete, add) that updates the map live; a "needs training" note listing objects the detector doesn't know yet; **Save routine**. Saved routines appear in a "Routines" list (tea, meds, plus saved).
- Offline: the mock returns a believable draft ("Brush teeth") so the flow demos with no keys.
Acceptance: Vitest for both tabs (consent required before upload; text submit; edit updates preview; save adds to list); keyboard operable; screenshot in PR; `cd web && npm test && npm run build`.
