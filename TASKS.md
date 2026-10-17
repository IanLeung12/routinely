# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: 3f1736c

## Tasks

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

### T410 — Supervisor side: "People I support" + add a person
- status: in-review
- class: standard
- priority: 0
- kind: feature
- source: ian
- deps: T408
- area: web/src/people/PeopleISupport.tsx, web/src/people/PeopleISupport.test.tsx, web/src/supporting/, web/src/overview/UnitOverview.tsx, web/src/overview/UnitOverview.test.tsx
- owner: ian-claude-standard-3
- claimed: 2026-10-17T22:02Z
- pr: #412
- note: T408 already shipped PeopleISupport (list + add by code) in web/src/people/; extend it there; Person.context already holds the context line; new CSS under web/src/supporting/, not people.css.
- rating: 4/5 clear, but T408 (merged before this task existed) had already implemented most of SPEC §17's supervisor routing in App.tsx outside this task's listed area, so the real gap was narrower (and less obvious) than the task text implied -- the note helped but didn't flag that

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
- status: done
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

### T420 — Restyle: overview Sparkline → MicroBars
- status: claimed
- class: light
- priority: 0
- kind: improvement
- source: ian
- deps: T419
- area: web/src/overview/Sparkline.tsx, web/src/overview/Sparkline.test.tsx
- owner: max_API_standard-2
- claimed: 2026-10-17T22:05Z
- pr: —

What: Split from T402. Make `Sparkline` render `MicroBars` (web/src/ui/charts/MicroBars.tsx) from the same input it takes today; keep its props and export so callers don't change. Read only those files and `web/src/overview/types.ts`.
Acceptance: existing Sparkline tests pass (update selectors only); `cd web && npx vitest run src/overview`.

### T421 — Restyle: BaselineChart + drift card on LineChart
- status: in-review
- class: standard
- priority: 0
- kind: improvement
- source: ian
- deps: T417
- area: web/src/resident/BaselineChart.tsx, web/src/resident/BaselineChart.test.tsx, web/src/resident/*Drift*.tsx, web/src/resident/*Drift*.test.tsx
- owner: ian-claude-standard-4
- claimed: 2026-10-17T21:37Z
- pr: #409
- rating: 4/5 mostly clear: DriftCard has no series data in its props (only slopePerDay/days/trending/minDays), so the acceptance's 'dotted trend series' and 'same props and data as today' had to be reconciled by synthesizing a 2-point fitted line from the slope rather than plotting real daily readings - worth saying explicitly next time if that's the intent
- note: CI fails only on check:bundle (over budget); rebase on main once T442 (bundle budget) merges.

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
- status: done
- class: light
- priority: 0
- kind: feature
- deps: —
- area: web/src/replays/ReplayList.tsx, web/src/replays/ReplayList.test.tsx, web/src/replays/replayList.css
- owner: Max_codex_light
- claimed: 2026-10-17T21:43Z
- pr: #408
- rating: 5/5 clear

What: Carved from T413 (Ian's replays library). A presentational list of a person's replays that T413's screen will drop in. No fetching, no routing.
Interface: `export function ReplayList(props: { replays: ReplaySummary[]; normal?: ReplaySummary | null; onOpen: (sessionId: string) => void })`. Rows newest first: date/time (from `started_at`), `task_id`, one `Pill` per `error_types` entry (labels from `web/src/ui/errorTypes.ts`), duration as "m:ss". Above the list a filter (`SegmentedControl` from `web/src/ui/`): "All" plus each error type that appears; filtering is local state. If `normal` is given, show it last, labelled "Most recent normal session (for comparison)". Empty state via `web/src/ui/EmptyState.tsx`: "No sessions with errors in the last 30 days". Each row is a button calling `onOpen(session_id)`.
Files to read: `web/src/contracts.ts` lines 425–535 (`PersonReplays`, `ReplaySummary`), `web/src/ui/Pill.tsx`, `web/src/ui/Row.tsx`, `web/src/ui/SegmentedControl.tsx`, `web/src/ui/EmptyState.tsx`, `web/src/ui/errorTypes.ts`, `docs/DESIGN.md` (tokens only). Use CSS vars from `web/src/index.css`; no new colours.
Acceptance:
- Vitest in `ReplayList.test.tsx`: newest-first order, filter narrows rows and "All" restores, empty state text, normal row shown last with its label, clicking a row calls `onOpen` with the id, rows reachable by Tab and activated by Enter.
- No "diagnos"/"patient" in copy. `cd web && npx vitest run src/replays/ReplayList` and `scripts/ci.sh` pass.

### T431 — Replays: supervisor notes on a replay (component, local only)
- status: done
- class: light
- priority: 1
- kind: feature
- deps: —
- area: web/src/replays/ReplayNotes.tsx, web/src/replays/ReplayNotes.test.tsx, web/src/replays/replayNotes.css
- owner: ian-claude-standard
- claimed: 2026-10-17T21:47Z
- pr: #406
- rating: 5/5 clear

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
- status: blocked
- class: light
- priority: 1
- kind: improvement
- deps: T401
- area: web/src/patterns/PatternLibrary.tsx, web/src/patterns/PatternLibrary.css, web/src/patterns/urgencyFilter.css, web/src/patterns/PatternLibrary.test.tsx, web/src/patterns/PatternLibrary.filters.test.tsx, web/src/patterns/PatternLibrary.keyboard.test.tsx
- owner: max_API_light
- claimed: 2026-10-17T21:58Z
- pr: #410
- rating: 5/5 clear
- note: PR #410 implemented; GitHub Python/web tests, lint and build pass, but first-load bundle budget is 342 bytes over (92542 vs 92200) after shared primitive adoption. Budget/shared chunk changes outside task area. Local Windows CI also fails unrelated preview port-binding test.

What: The pattern library still uses the pre-redesign tokens (`--panel`, `--border`, `--muted`, `--accent`) and its own boxes. Rebuild its markup on the ui primitives (`Card`, `SectionHeader`, `Row`, `Pill`, `SegmentedControl` for the urgency filter) and the new tokens only. Read only `docs/DESIGN.md`, `web/src/ui/README.md`, `web/src/index.css` and the files in area.
Why: judges click into "consistent with" patterns from the alert; it's the one demo screen that still looks like the old app.
Interface: same exports/props as today; same data from `web/src/patterns/api.ts` and `mockPatterns.ts` (don't edit those).
Acceptance:
- no legacy tokens (`--panel`, `--border`, `--muted`, `--bg`) and no hex/px literals in the two CSS files;
- wording unchanged ("consistent with", never "diagnose");
- existing tests pass (update selectors only, keep behaviour); `cd web && npx vitest run src/patterns && npm run lint`.

### T434 — Redesign follow-up: guided tour card on the Fey system
- status: in-review
- class: light
- priority: 2
- kind: improvement
- deps: T401
- area: web/src/tour/Tour.tsx, web/src/tour/tour.css, web/src/tour/Tour.test.tsx, web/src/tour/Tour.keyboard.test.tsx
- owner: Max_codex_light
- claimed: 2026-10-17T22:09Z
- pr: #413
- rating: 5/5 clear

What: Restyle the guided-tour card: `--surface-raised`, `--hairline-strong`, `--radius-lg`, the one allowed float shadow (DESIGN.md principle 3), `Button` from `web/src/ui/Button.tsx` for next/back/close. Read only `docs/DESIGN.md`, `web/src/ui/README.md`, `web/src/index.css` and the files in area. Don't touch `steps.ts`.
Why: the tour is the first thing a judge sees on the dashboard; it should match the redesigned screens under it.
Interface: same `Tour` props/exports; behaviour and keyboard handling unchanged.
Acceptance:
- tokens only, no hex/px literals in `tour.css`;
- existing tests pass (selectors only); `cd web && npx vitest run src/tour && npm run lint`.

### T435 — Redesign follow-up: privacy panel + monitoring toggle on the Fey system
- status: claimed
- class: light
- priority: 2
- kind: improvement
- deps: T401
- area: web/src/about/PrivacyPanel.tsx, web/src/about/MonitoringToggle.tsx, web/src/about/privacyPanel.css, web/src/about/PrivacyPanel.test.tsx, web/src/about/PrivacyPanel.keyboard.test.tsx, web/src/about/PrivacyPanel.mobile.test.tsx, web/src/about/MonitoringToggle.test.tsx, web/src/about/MonitoringToggle.keyboard.test.tsx
- owner: ian-laptop-standard
- claimed: 2026-10-17T22:28Z
- pr: —

What: Move the supervisor-side privacy panel and the pause-monitoring toggle onto the new tokens and primitives (`Card`, `SectionHeader`, `Row` for each "what's stored" line, `Button` for the toggle). Don't edit `monitoringApi.ts` or `ResidentDetail.tsx` (T404 owns it). Read only `docs/DESIGN.md`, `web/src/ui/README.md`, `web/src/index.css` and the files in area.
Why: privacy (skeletons only, no video) is a judging talking point; the panel that says so is still in the old style.
Interface: same exports/props; same text.
Acceptance:
- no legacy tokens (`--muted`, `--panel`, `--border`) and no hex/px literals in `privacyPanel.css`;
- existing tests pass (selectors only, keep the phone-width wrapping assertion meaningful); `cd web && npx vitest run src/about && npm run lint`.

### T436 — Review: camera preview MJPEG readable by any website open on the capture machine
- status: in-review
- class: light
- priority: 0
- kind: bug
- source: reviewer
- deps: —
- area: pipeline/src/routine_watch/preview.py, pipeline/tests/test_preview.py
- owner: max_API_standard
- claimed: 2026-10-17T21:56Z
- pr: #411
- rating: 5/5 clear

What: `preview.py` sends `Access-Control-Allow-Origin: *` on every reply, including `/preview.mjpg`. The loopback/Host checks don't stop a cross-site `fetch('http://127.0.0.1:8765/preview.mjpg')`: the browser runs on this machine (client is loopback) and sends `Host: 127.0.0.1:8765` (passes). So any web page open in that browser can read live camera frames and upload them — raw video leaving the machine, against SPEC §8/§12.
Fix: in `response_for`, take the request's `Origin` header (pass it from `_Handler.do_GET`); if present and its host is not loopback (`is_loopback(urlparse(origin).hostname)`), return 403. Echo the allowed loopback origin in `Access-Control-Allow-Origin` (plus `Vary: Origin`) instead of `*`; send no CORS header when there's no Origin. `<img src>` in `CameraPreview` still works (no CORS needed).
Acceptance:
- Tests in `test_preview.py`: `Origin: https://evil.example` → 403 on `/preview.mjpg` and `/health`; `Origin: http://localhost:5173` → 200 with that origin echoed; no Origin → 200; the existing `== "*"` asserts updated.
- `scripts/ci.sh` passes.

### T437 — Routine builder backend: draft a routine from words or a setup video (Gemini)
- status: claimed
- class: heavy
- priority: 0
- kind: feature
- source: ian
- deps: —
- area: pipeline/src/routine_watch/routine_builder.py, pipeline/src/routine_watch/api_routines.py, pipeline/src/routine_watch/api.py, pipeline/src/routine_watch/tasks/graph.py, pipeline/tests/test_routine_builder.py, pipeline/tests/fixtures/routine_builder/, .env.example
- owner: ian-claude
- claimed: 2026-10-17T22:03Z
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
- status: claimed
- class: standard
- priority: 0
- kind: feature
- source: ian
- deps: —
- area: web/src/routines/, web/src/mock/routines.ts, web/src/App.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T22:05Z
- pr: —

What: The front end for T437, built in parallel against the API shape in T437's Interface with a mock (`web/src/mock/routines.ts`) so it doesn't wait for T437. Follow `docs/DESIGN.md`; check 2–3 Mobbin references for "create from upload / AI builder" flows.
Interface (`web/src/routines/`):
- "New routine" entry from the shell (both roles).
- Two tabs: **Describe it** (textarea + examples) and **From a video** (file picker, max ~60 s; a consent checkbox that must be ticked: "This clip is sent once to Google Gemini to draft the steps. It is not stored. Day-to-day monitoring never sends video."). Progress state while drafting.
- Result: the drafted routine shown as a task map (reuse `web/src/live/TaskMap`), plus an editable step list (rename, reorder deps, toggle optional, delete, add) that updates the map live; a "needs training" note listing objects the detector doesn't know yet; **Save routine**. Saved routines appear in a "Routines" list (tea, meds, plus saved).
- Offline: the mock returns a believable draft ("Brush teeth") so the flow demos with no keys.
Acceptance: Vitest for both tabs (consent required before upload; text submit; edit updates preview; save adds to list); keyboard operable; screenshot in PR; `cd web && npm test && npm run build`.

### T439 — Bug: integration check failing on main
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

What: `scripts/integration.sh` (stack up offline → API endpoints → dashboard render → live WebSocket) fails on main @ 24033f5:
  FAIL dev.sh up: 
    api log: INFO:     Started server process [2099018] INFO:     Waiting for application startup. INFO:     Application startup complete. INFO:     Uvicorn running on http://0.0.0.0:8100 (Press CTRL+C to quit) 
Interface: reproduce with `scripts/integration.sh`; logs in `.dev/api.log` / `.dev/web.log`. Fix the cause (not the check) unless the check itself is wrong.
Acceptance:
- `scripts/integration.sh` prints OK; `scripts/ci.sh` passes.

### T440 — Bug: flaky unit test test_frames_in_thread_hands_over_every_record_in_order
- status: claimed
- class: light
- priority: 0
- kind: bug
- deps: —
- area: pipeline/tests/test_api_live_camera.py
- owner: ian-claude-heavy-3
- claimed: 2026-10-17T22:06Z
- pr: —
- source: orchestrator

What: Failed main CI run 39073146552 (@24033f5, unrelated .gitattributes commit). `frames_in_thread` drops the newest record once `max_pending` (default `MAX_PENDING_FRAMES = 30`, pipeline/src/routine_watch/live_camera.py:94) are waiting, and FakeCamera's clip has ~43 frames, so when the capture thread outruns the event loop on a loaded runner, frames get dropped and `drain(camera) == camera.frames` fails. That's a timing race in the test, not a product bug.
Interface: test-only change. In `test_frames_in_thread_hands_over_every_record_in_order` (line ~298), call `drain(camera, max_pending=len(camera.frames) + 1)` so nothing can be dropped. Check the other tests in the file that compare a full list (not `stop_after`/`max_pending=0`) for the same race and fix them the same way. Do not change live_camera.py.
Acceptance:
- `cd pipeline && python -m pytest tests/test_api_live_camera.py -q` passes; run the file 20 times in a loop (`for i in $(seq 20); do python -m pytest tests/test_api_live_camera.py -q -x || break; done`) with no failure.
- `scripts/ci.sh` passes.

### T441 — Review: deleteReplay reports success when the API refuses the delete
- status: claimed
- class: light
- priority: 1
- kind: bug
- source: reviewer
- deps: —
- area: web/src/replays/api.ts, web/src/replays/api.test.ts
- owner: ian-laptop-standard
- claimed: 2026-10-17T22:25Z
- pr: —

What: In `web/src/replays/api.ts`, `deleteReplay` (and the two fetches) fall back to the offline mock library on *any* non-ok response, not just a network error. A 500/403 from `DELETE /replays/{id}` on a mock-library id therefore resolves and hides the replay locally while the server still stores it (privacy: the person thinks their replay is gone, SPEC §17). A 404 for a real replay likewise turns into "Replay not found" only by accident.
Interface: keep the signatures. Fall back to the offline library only inside `catch` (fetch threw = API unreachable). If the API answered: `ok` → success; `404` → throw `Error('Replay not found')`; anything else → throw `Error('Could not delete replay')` and do NOT add the id to `deleted`. Apply the same rule to `fetchPersonReplays`/`fetchReplay` (non-ok response → throw, don't silently show mock data).
Acceptance:
- tests in `web/src/replays/api.test.ts`: DELETE returning 500 rejects and a following `fetchPersonReplays` (fetch throwing) still lists the replay; fetch throwing still deletes offline.
- `cd web && npm test -- replays` and `scripts/ci.sh` pass.

### T442 — Bug: main CI red — first-load JS 336 bytes over bundle budget
- status: claimed
- class: light
- priority: 0
- kind: bug
- source: orchestrator
- deps: —
- area: web/scripts/check-bundle.mjs, web/README.md
- owner: max_API_light
- claimed: 2026-10-17T22:24Z
- pr: —

What: `main` CI fails at `npm run check:bundle`: first-load JS is 92536 bytes gzipped vs `BUDGET_BYTES = 92_200` (runs 39073873088, 39074550159). No single merge caused it; the redesign (T403/T407), person view (T409) and replays (T430/T431) each added always-on code. Open PRs (#409, #410) fail on this too.
Interface: in `web/scripts/check-bundle.mjs` raise `BUDGET_BYTES` to `96_000` and update the comment above it to say why (redesign shell + person view + replays are always-on screens added 2026-10-17; measured 92536 bytes). Add one line to the budget section of `web/README.md` with the new number and reason. Touch no other file.
Acceptance:
- `cd web && npm run build && npm run check:bundle` passes.
- `scripts/ci.sh` passes.
