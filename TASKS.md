# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: 02eed7c

## Tasks

### T411 — Wording pass: people, not just residents and nurses
- status: done
- class: light
- priority: 1
- kind: improvement
- source: ian
- deps: T408, T409, T410
- area: web/src/alert/, web/src/resident/, web/src/handoff/, web/src/landing/, web/src/wording.test.ts
- owner: ian-claude-heavy-3
- claimed: 2026-10-17T23:28Z
- pr: #428
- note: released by max_API_light: run ended without progress
- rating: 4/5 area list missed the files the new rule forces (about/, ui/DemoBanner, tour/) and the pipeline-written handoff summary; acceptance itself was clear

What: Make shared UI copy role-neutral per SPEC §17: "resident" → "person" (or the person's name), "nurse" only where it's specifically the care-home supervisor, never "patient". Landing page: say it's for anyone, alone or with family, a carer or a care home.
Acceptance: `web/src/wording.test.ts` extended to fail on "patient" and on "nurse" outside an allow-list of care-home-specific strings; all tests pass; `scripts/ci.sh` passes.

### T413 — Replays library for supervisors and the person
- status: claimed
- class: standard
- priority: 0
- kind: feature
- source: ian
- deps: T412, T427, T430, T431
- area: web/src/replays/Replays.tsx, web/src/replays/Replays.test.tsx, web/src/replays/replays.css, web/src/mock/replays.ts, web/src/App.tsx
- note: merge conflict with main on PR #429: check out its branch, merge origin/main, fix, push
- owner: ian-claude-standard
- claimed: 2026-10-17T23:56Z
- pr: #429
- rating: 4/5 clear, but the listed area (Replays.tsx/test/css, mock/replays.ts, App.tsx) didn't fit the entry-point work the spec asked for (a person's detail, an alert's error rows, My routine); ResidentDetail/AlertView/MyRoutine stayed untouched and entry points went into App.tsx's shell instead -- worth naming that tradeoff in the task next time

What: A "Replays" screen where a supervisor can browse a person's sessions that had errors and analyse them, and the person can see (and delete) their own (SPEC §17: they see exactly what supervisors see). Use the mobbin MCP for 2–3 references of video/recording libraries and timeline scrubbers; follow `docs/DESIGN.md` if merged.
Interface:
- List: per person, newest first, each row = date/time, task, error pills (omission/sequence/repeat/…), duration; filter by error type and date range; empty state ("No sessions with errors in the last 30 days").
- Player (extend `ReplayPlayer`): skeleton + object boxes, **timeline with error markers** (click to jump), play/pause/speed (0.5×/1×/2×), step labels as it plays, optional ghost overlay of the person's normal session, frame-by-frame with arrow keys.
- Supervisor notes on a replay (local/mock, shown with author + time); person view shows "Delete this replay".
- Entry points: from a person's detail ("Replays"), from an alert's error rows, and from "My routine" for the person.
- Offline/mock fallback in `web/src/mock/replays.ts`.
Acceptance: Vitest for list/filter/empty, marker jump, speed, delete, notes; keyboard operable; screenshot in PR; `scripts/ci.sh` passes.

### T432 — Task map as a Postman Flows–style node graph
- status: claimed
- class: standard
- priority: 0
- kind: improvement
- source: ian
- deps: T406
- area: web/src/live/TaskMap.tsx, web/src/live/TaskMap.test.tsx, web/src/live/taskMap.css, web/src/live/TaskMapLegend.tsx, web/src/live/TaskMapLegend.test.tsx
- owner: ian-claude-heavy-2
- claimed: 2026-10-17T23:18Z
- pr: —

What: Ian wants the task map to look like **Postman Flows** (node-graph canvas). Use the mobbin MCP (`search_screens` / `search_flows` "Postman Flows") to study 2–3 references first and name them in the PR. Render the task graph (steps + deps from the task YAML, already sent over /ws/live) as rounded node cards on a dotted canvas, connected by smooth curved edges with small ports; parallel branches side by side (e.g. fill kettle ∥ get cup), optional steps dashed. Live state on each node: pending (muted), done (green check), current (glow/pulse), error (red, with the error type pill: omission/sequence/repeat/substitution), unclear (grey). Edges into an errored step turn red/amber. Fits the Fey-style tokens from `docs/DESIGN.md`.
Why: the task map is the centrepiece of the live demo shot; a flow canvas makes "dependencies, not a fixed order" obvious at a glance.
Interface: dependency-free SVG/HTML (no graph libraries); a simple layered layout (topological levels left→right) computed from deps; same props and data as today's TaskMap; keyboard/screen-reader: nodes are a list with state in their accessible names.
Acceptance: renders tea and meds graphs without overlaps; state changes animate; existing TaskMap tests pass (selectors only) + a layout test (parallel steps share a level); screenshot in PR; `cd web && npm test && npm run build`.

### T435 — Redesign follow-up: privacy panel + monitoring toggle on the Fey system
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: T401
- area: web/src/about/PrivacyPanel.tsx, web/src/about/MonitoringToggle.tsx, web/src/about/privacyPanel.css, web/src/about/PrivacyPanel.test.tsx, web/src/about/PrivacyPanel.keyboard.test.tsx, web/src/about/PrivacyPanel.mobile.test.tsx, web/src/about/MonitoringToggle.test.tsx, web/src/about/MonitoringToggle.keyboard.test.tsx
- owner: max_API_standard
- claimed: 2026-10-17T22:29Z
- pr: #420
- note: released by ian-laptop-standard: run ended without progress
- rating: 5/5 clear

What: Move the supervisor-side privacy panel and the pause-monitoring toggle onto the new tokens and primitives (`Card`, `SectionHeader`, `Row` for each "what's stored" line, `Button` for the toggle). Don't edit `monitoringApi.ts` or `ResidentDetail.tsx` (T404 owns it). Read only `docs/DESIGN.md`, `web/src/ui/README.md`, `web/src/index.css` and the files in area.
Why: privacy (skeletons only, no video) is a judging talking point; the panel that says so is still in the old style.
Interface: same exports/props; same text.
Acceptance:
- no legacy tokens (`--muted`, `--panel`, `--border`) and no hex/px literals in `privacyPanel.css`;
- existing tests pass (selectors only, keep the phone-width wrapping assertion meaningful); `cd web && npx vitest run src/about && npm run lint`.

### T436 — Review: camera preview MJPEG readable by any website open on the capture machine
- status: done
- class: light
- priority: 0
- kind: bug
- source: reviewer
- deps: T442
- area: pipeline/src/routine_watch/preview.py, pipeline/tests/test_preview.py
- owner: Max_codex_light
- claimed: 2026-10-17T22:40Z
- pr: #411
- rating: 5/5 clear
- note: orch: bundle budget raised in #409; merged origin/main into PR, CI re-running with auto-merge

What: `preview.py` sends `Access-Control-Allow-Origin: *` on every reply, including `/preview.mjpg`. The loopback/Host checks don't stop a cross-site `fetch('http://127.0.0.1:8765/preview.mjpg')`: the browser runs on this machine (client is loopback) and sends `Host: 127.0.0.1:8765` (passes). So any web page open in that browser can read live camera frames and upload them — raw video leaving the machine, against SPEC §8/§12.
Fix: in `response_for`, take the request's `Origin` header (pass it from `_Handler.do_GET`); if present and its host is not loopback (`is_loopback(urlparse(origin).hostname)`), return 403. Echo the allowed loopback origin in `Access-Control-Allow-Origin` (plus `Vary: Origin`) instead of `*`; send no CORS header when there's no Origin. `<img src>` in `CameraPreview` still works (no CORS needed).
Acceptance:
- Tests in `test_preview.py`: `Origin: https://evil.example` → 403 on `/preview.mjpg` and `/health`; `Origin: http://localhost:5173` → 200 with that origin echoed; no Origin → 200; the existing `== "*"` asserts updated.
- `scripts/ci.sh` passes.

### T437 — Routine builder backend: draft a routine from words or a setup video (Gemini)
- status: done
- class: heavy
- priority: 0
- kind: feature
- source: ian
- deps: —
- area: pipeline/src/routine_watch/routine_builder.py, pipeline/src/routine_watch/api_routines.py, pipeline/src/routine_watch/api.py, pipeline/src/routine_watch/tasks/graph.py, pipeline/tests/test_routine_builder.py, pipeline/tests/fixtures/routine_builder/, .env.example
- owner: ian-claude
- claimed: 2026-10-17T22:03Z
- pr: #417
- rating: 5/5 clear

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
- status: done
- class: standard
- priority: 0
- kind: feature
- source: ian
- deps: —
- area: web/src/routines/, web/src/mock/routines.ts, web/src/App.tsx
- owner: —
- claimed: —
- pr: #414
- rating: 4/5 clear, though the two task-map interpretations (reorder-the-list vs edit-deps) under 'reorder deps' were ambiguous; implemented both
- note: merge conflict with main on PR #414: check out its branch, merge origin/main, fix, push

What: The front end for T437, built in parallel against the API shape in T437's Interface with a mock (`web/src/mock/routines.ts`) so it doesn't wait for T437. Follow `docs/DESIGN.md`; check 2–3 Mobbin references for "create from upload / AI builder" flows.
Interface (`web/src/routines/`):
- "New routine" entry from the shell (both roles).
- Two tabs: **Describe it** (textarea + examples) and **From a video** (file picker, max ~60 s; a consent checkbox that must be ticked: "This clip is sent once to Google Gemini to draft the steps. It is not stored. Day-to-day monitoring never sends video."). Progress state while drafting.
- Result: the drafted routine shown as a task map (reuse `web/src/live/TaskMap`), plus an editable step list (rename, reorder deps, toggle optional, delete, add) that updates the map live; a "needs training" note listing objects the detector doesn't know yet; **Save routine**. Saved routines appear in a "Routines" list (tea, meds, plus saved).
- Offline: the mock returns a believable draft ("Brush teeth") so the flow demos with no keys.
Acceptance: Vitest for both tabs (consent required before upload; text submit; edit updates preview; save adds to list); keyboard operable; screenshot in PR; `cd web && npm test && npm run build`.

### T439 — Bug: integration check failing on main
- status: done
- class: standard
- priority: 0
- kind: bug
- deps: —
- area: scripts/dev.sh, pipeline/src/routine_watch/api.py, web/src/
- owner: —
- claimed: —
- pr: —
- source: integration
- note: orch: integration PASS on main per TESTREPORT 2026-10-17T23:05Z (dev.sh up OK); closed as transient, tester will refile if it recurs

What: `scripts/integration.sh` (stack up offline → API endpoints → dashboard render → live WebSocket) fails on main @ 24033f5:
  FAIL dev.sh up: 
    api log: INFO:     Started server process [2099018] INFO:     Waiting for application startup. INFO:     Application startup complete. INFO:     Uvicorn running on http://0.0.0.0:8100 (Press CTRL+C to quit) 
Interface: reproduce with `scripts/integration.sh`; logs in `.dev/api.log` / `.dev/web.log`. Fix the cause (not the check) unless the check itself is wrong.
Acceptance:
- `scripts/integration.sh` prints OK; `scripts/ci.sh` passes.

### T440 — Bug: flaky unit test test_frames_in_thread_hands_over_every_record_in_order
- status: done
- class: light
- priority: 0
- kind: bug
- deps: —
- area: pipeline/tests/test_api_live_camera.py
- owner: ian-claude-heavy-3
- claimed: 2026-10-17T22:06Z
- pr: #419
- source: orchestrator
- rating: 5/5 clear - the diagnosis, the exact call to make and the 20x acceptance loop were all in the task; only extra was that main was separately red on the bundle budget (T442/T421), so the branch needed rebasing onto e34c2a5 before ci.sh could pass

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
- status: done
- class: light
- priority: 0
- kind: bug
- source: orchestrator
- deps: —
- area: web/scripts/check-bundle.mjs, web/README.md
- owner: ian-claude
- claimed: 2026-10-17T22:48Z
- pr: #422
- note: main green again: #418 raised the budget to 96,000 and merged; #422 recorded the measured 95,204/96,000 total and rewrapped the README note
- rating: 4/5 the note's premise was stale: #418 was already conflict-free and auto-merged mid-CI, and main's budget was 95_200 (T421) not 92_200, so the numbers in the task had to be re-measured

What: `main` CI fails at `npm run check:bundle`: first-load JS is 92536 bytes gzipped vs `BUDGET_BYTES = 92_200` (runs 39073873088, 39074550159). No single merge caused it; the redesign (T403/T407), person view (T409) and replays (T430/T431) each added always-on code. Open PRs (#409, #410) fail on this too.
Interface: in `web/scripts/check-bundle.mjs` raise `BUDGET_BYTES` to `96_000` and update the comment above it to say why (redesign shell + person view + replays are always-on screens added 2026-10-17; measured 92536 bytes). Add one line to the budget section of `web/README.md` with the new number and reason. Touch no other file.
Acceptance:
- `cd web && npm run build && npm run check:bundle` passes.
- `scripts/ci.sh` passes.

### T443 — Review: Routines screen crashes on the live API (GET /routines has no task_graph)
- status: done
- class: light
- priority: 0
- kind: bug
- source: reviewer
- deps: —
- area: web/src/routines/types.ts, web/src/routines/RoutinesScreen.tsx, web/src/routines/RoutinesScreen.test.tsx, web/src/mock/routines.ts
- owner: ian-claude-heavy-3
- claimed: 2026-10-17T22:58Z
- pr: #423
- note: released by ian-laptop-standard: run ended without progress
- rating: 4/5 clear on the fix; it didn't mention that saveRoutine's offline row and api.test.ts's whole-object assertion (T444's area) must change too, since POST /routines answers with detail() = summary + task_graph

What: `GET /routines` returns `Routine.summary()` (pipeline/src/routine_watch/routine_builder.py ~line 979): `id, title, task_id, built_in, source, step_count, needs_training` and NO `task_graph`. `web/src/routines/RoutinesScreen.tsx:77` reads `routine.task_graph.steps.length`, so with the API up the screen throws a TypeError (it only works on the offline mock, which includes `task_graph`).
Interface: in `types.ts` add a `RoutineSummary` type matching `summary()`; `fetchRoutines()` in api.ts returns `RoutineSummary[]` (change only its type annotation; its fallback logic is T444). `RoutinesScreen.tsx` renders `${routine.step_count} steps`. Make `mockBuiltInRoutines` and the localStorage fallback rows in `mock/routines.ts` carry `step_count` and the other summary fields. Do not change the pipeline.
Acceptance:
- RoutinesScreen test feeds a fetch response shaped exactly like `summary()` (no task_graph) and asserts "N steps" renders.
- `scripts/ci.sh` passes.

### T444 — Review: routine builder shows a canned draft / fake save when the API refuses
- status: done
- class: light
- priority: 1
- kind: bug
- source: reviewer
- deps: T443
- area: web/src/routines/api.ts, web/src/routines/api.test.ts, web/src/routines/RoutineBuilder.tsx, web/src/routines/RoutineBuilder.test.tsx
- owner: ian-claude-standard-4
- claimed: 2026-10-17T23:40Z
- pr: #427
- note: released by max_API_light: run ended without progress
- rating: 5/5 clear

What: `web/src/routines/api.ts` falls back to the mock on any non-ok response (same pattern as T441). A person's clip refused with 400/413/422/502 by `POST /routines/draft` comes back as a canned "make tea" draft as if Gemini had read their clip, and a `POST /routines` 422 (bad graph) / 409 (built-in id or library full) is silently "saved" to localStorage while the server never kept it.
Interface: fall back to mocks/localStorage only inside `catch` (fetch threw = API unreachable). If the API answered non-ok, throw `Error(detail)` using the JSON `detail` string (FastAPI `{detail: string}`), else a generic message. `RoutineBuilder.tsx` shows that message with the existing error UI from web/src/ui/ and keeps the user's draft/graph on screen.
Acceptance:
- api.test.ts: 413 on draftFromVideo rejects with the detail; 409 on saveRoutine rejects and writes nothing to localStorage; fetch throwing still returns the mock.
- `scripts/ci.sh` passes.

### T445 — Bug: flaky unit test MyRoutine "says nobody else can see this…" (lazy section not loaded within findBy's 1 s)
- status: done
- class: light
- priority: 0
- kind: bug
- deps: —
- area: web/src/people/MyRoutine.test.tsx
- source: tester
- owner: ian-claude-standard-4
- claimed: 2026-10-17T23:26Z
- note: released by max_API_standard: run ended without progress
- pr: #424
- rating: 5/5 clear

What: `scripts/ci.sh` on main @64ab65c failed in web tests: `src/people/MyRoutine.test.tsx > MyRoutine > says nobody else can see this when the person is watching themselves` → `Unable to find role="heading" and name "How this week looks"`; DOM still shows "Loading your week…". `MyRoutine.tsx` loads `RoutineSections` with `React.lazy` (line ~25), and the first test in the file pays the dynamic-import/transform cost, which exceeds `findByRole`'s default 1000 ms timeout on a loaded box. Repro: `cd web && for i in 1 2 3; do npx vitest run src/people/MyRoutine.test.tsx | grep "Tests "; done` failed 1 of 3 runs in isolation (plus the full ci.sh run). Expected: always passes. It's a test timing race, not a product bug.
Interface: test-only change. In `renderRoutine` in `MyRoutine.test.tsx`, wait longer (e.g. `findByRole(..., {}, { timeout: 5000 })`) or preload the lazy module in a `beforeAll` (`await import('../person/routine/RoutineSections.tsx')`). Do not change `MyRoutine.tsx`. Check other tests that render lazy screens with plain `findBy*` for the same race.
Acceptance:
- `cd web && for i in $(seq 20); do npx vitest run src/people/MyRoutine.test.tsx || break; done` with no failure.
- `scripts/ci.sh` passes.

### T446 — Replay player: error markers on the timeline, speed, arrow-key stepping
- status: done
- class: light
- priority: 0
- kind: feature
- source: ian
- deps: —
- area: web/src/evidence/ReplayPlayer.tsx, web/src/evidence/ReplayPlayer.markers.test.tsx, web/src/evidence/evidence.css
- owner: ian-claude
- claimed: 2026-10-17T23:20Z
- pr: #425
- rating: 4/5 clear on the interface; it didn't say the speed group can't use role=group (an existing unqualified getByRole('group') test pins the player) or that the eager first-load budget has ~100 B of headroom, so the feature needs a budget bump outside the area

What: Carved from T413 (Ian's replays library). Extend the existing skeleton `ReplayPlayer` so a supervisor can analyse a replay: error markers on the timeline that jump to the moment, a 0.5×/1×/2× speed control, and frame-by-frame stepping with arrow keys. Read only `web/src/evidence/ReplayPlayer.tsx`, `web/src/evidence/ReplayPlayer.test.tsx` (style reference) and `web/src/ui/Button.tsx`.
Interface: add optional props, existing callers unchanged: `markers?: { t: number; label: string; kind?: string }[]` (t in seconds, same clock as `frames[i].t`). Render each marker as a `<button>` positioned along the timeline (left = t / last frame t), accessible name `"Jump to <label> at m:ss"`, class `replay-player__marker` (+ `replay-player__marker--<kind>` if given; colours from existing tokens in evidence.css). Click → position = first frame with `t >= marker.t`, playback pauses. Speed: a labelled group of three `Button`s ("0.5×", "1×", "2×", `aria-pressed` on the active one, default 1×) multiplying the frame rate. On the player group: ArrowRight/ArrowLeft step one frame and pause; Space still plays/pauses. Mention arrow keys in the group `aria-label`.
Acceptance:
- New `ReplayPlayer.markers.test.tsx` (Vitest + Testing Library, fake timers): markers render with accessible names; clicking one moves the "Replay position" slider to the right frame; 2× advances twice as many frames as 1× over the same time; arrow keys step and pause; no `markers` prop → no marker buttons.
- Existing `ReplayPlayer*.test.tsx` pass unchanged.
- `cd web && npx vitest run src/evidence` and `scripts/ci.sh` pass.

### T447 — DEMO.md: click path for the new screens (people, My routine, routine builder, replays)
- status: done
- class: light
- priority: 1
- kind: docs
- deps: —
- area: docs/DEMO.md
- owner: ian-claude-standard
- claimed: 2026-10-17T23:37Z
- pr: #426
- source: proposed
- note: released by max_API_standard-2: run ended without progress
- rating: 5/5 clear

Why: Ian films the demo at 03:00 UTC from docs/DEMO.md, and its click path predates the people/supervisor roles, My routine, the routine builder and the replays screen, so he'd have no run order for them.
What: Extend the "Click path" section of `docs/DEMO.md` with short steps (same bullet style) for: "People I support" + add a person, the *Myself* view ("My routine": how this week looks, privacy card), the Routines screen + routine builder (describe it → editable task map → save; note it uses a canned fake draft unless `LIVE_API=1`), and the replays library if a nav entry for it exists on main (otherwise skip it). Keep the existing SPEC §10 order; put the new steps after "Shift handoff" and before "Close" as an optional segment.
Interface: read only `docs/DEMO.md`, `web/src/App.tsx` (nav labels), `web/src/people/PeopleISupport.tsx`, `web/src/people/MyRoutine.tsx`, `web/src/routines/RoutinesScreen.tsx`, `web/src/routines/RoutineBuilder.tsx` to get the exact button/heading text. Don't change code.
Acceptance:
- Every button/heading named in the new steps exists verbatim in those files.
- Wording: "flags a change for review", never "diagnoses".
- `scripts/ci.sh` passes.

### T448 — Smoke: check the routines and replays endpoints
- status: claimed
- class: light
- priority: 1
- kind: test
- deps: —
- area: scripts/smoke.sh
- owner: ian-claude
- claimed: 2026-10-17T23:50Z
- pr: —
- source: proposed
- note: released by max_API_standard-2: run ended without progress

Why: the demo now shows the routine builder and replays, but `scripts/smoke.sh` (preflight before filming) never calls them; T443 showed these paths can break on the live API unnoticed.
What: add checks to `scripts/smoke.sh` in the existing `get` / `check_json` / `fail` style: `GET /routines` is a non-empty JSON list whose items have `id` and `title`; `GET /routines/<first id>` has a `task_graph`; `POST /routines/draft` with a short text description returns 200 with a task graph (fake drafter by default; skip this check with a printed note if it answers 503/501); `GET /people/<a person id>/replays` returns a JSON object (take the id from the residents/people list the script already fetches, as `demo_room` is derived).
Interface: read `scripts/smoke.sh`, `pipeline/src/routine_watch/api_routines.py` (request shape of `/routines/draft`), `pipeline/src/routine_watch/api_residents.py` lines 175–240. No changes outside `scripts/smoke.sh`.
Acceptance:
- `scripts/dev.sh up && scripts/smoke.sh; scripts/dev.sh down` passes on main with all new checks listed.
- Never makes a real Gemini call (LIVE_API unset).
- `scripts/ci.sh` passes.

### T449 — Stability: lazy-load AlertView and ResidentDetail to restore first-load bundle headroom
- status: todo
- class: light
- priority: 1
- kind: improvement
- source: orchestrator
- deps: —
- area: web/src/App.tsx, web/scripts/check-bundle.mjs, web/README.md
- owner: —
- claimed: —
- pr: —

What: The first-load JS budget has been bumped three times today (92,200 → 96,000 → 96,500) and main sits ~250 B under it, so every remaining pre-freeze UI PR risks a red "first-load JS over budget" CI. Make `AlertView` and `ResidentDetail` lazy in `App.tsx` the same way `Handoff`/`RoutinesScreen` already are, then lower the budget to measured + ~1,500 B.
Why: stops bundle-budget CI failures from blocking demo-path PRs in the last 90 minutes before the 01:30 UTC freeze.
Interface: in `web/src/App.tsx` replace the eager `import { AlertView }` / `import { ResidentDetail }` with `lazy(() => import(...).then(m => ({ default: m.X })))` and render them inside the existing `<Suspense fallback={<Loading .../>}>` pattern used for `RoutinesScreen`. Read only `web/src/App.tsx`, `web/scripts/check-bundle.mjs` and the bundle section of `web/README.md`.
Acceptance:
- `cd web && npm run build && npm run check:bundle` passes; set `BUDGET_BYTES` to the new measured total + ~1,500 and record the measured number in the comment and in web/README.md.
- Existing App tests pass (if a test uses sync `getBy` on the alert/resident screen right after navigation, switch only that query to `findBy`).
- `scripts/ci.sh` passes.

### T450 — Safety check-in backend: alert → check-in countdown → supervisor alarm → escalation (Project KAZE)
- status: claimed
- class: heavy
- priority: 0
- kind: feature
- source: ian
- deps: —
- area: pipeline/src/routine_watch/checkin.py, pipeline/src/routine_watch/api_checkin.py, pipeline/src/routine_watch/api.py, pipeline/src/routine_watch/api_live.py, pipeline/tests/test_checkin.py, pipeline/tests/test_api_checkin.py, SPEC.md
- owner: ian-claude-heavy-3
- claimed: 2026-10-17T23:57Z
- pr: —

What: Ian is entering the **Project KAZE** challenge ("help when someone can't ask for it themselves"). Whenever an **alert** is raised for a person, the system asks the **person** to check in. If they don't within a window, it **sounds an alarm for their supervisor**, then escalates to the next supporter if nobody acknowledges. All simulated; never a real call or SMS.
Why: KAZE prize ($1,500); also makes alerts actionable when the person can't respond.
Interface:
- `checkin.py`: a pure state machine with an injectable clock. States: `pending` (waiting for the person) → `ok` (cancelled with the safety PIN) | `duress` (duress PIN: **looks exactly like ok to the person**, but raises a silent `alarm` to supervisors marked duress) | `alarm` (window expired: supporter #1 alarmed) → `escalated` (supporter #1 didn't acknowledge within the ack window: supporter #2, and so on down the list) → `acknowledged` (a supporter tapped "I'm on it") → `resolved` (a supporter or the person resolves it, with a reason: `false_alarm` | `helped` | `other`). Every transition is appended to an event log with a timestamp and actor.
- **The server owns the countdown**: deadlines are stored server-side, and a background tick (asyncio, every 1 s) advances them, so an alarm still fires if the person's device disconnects after the check-in started (KAZE "connectivity failure").
- Settings per person (in-memory + JSON under `.data/`, mock defaults for the demo people): check-in window (default 120 s, demo 20 s), ack window (default 120 s, demo 15 s), ordered supporter list (from the T408 people links), safety PIN + duress PIN (hashed, never returned or logged), and **sharing permissions** per supporter: `location` (a simulated room/address string), `alert_details` (errors and evidence) and `replay`. Supervisor payloads include only what that supporter is allowed to see; the test proves it.
- Hook: when an alert is created (`api_alerts` / `alerts.py` path), start a check-in for that person (idempotent per alert). `POST /checkins/demo` starts one by hand, for the demo.
- API (`api_checkin.py`): `GET /checkins/active?person=` · `POST /checkins/{id}/respond {pin}` (same 200 response for the safety and duress PINs, wrong PIN → 401 and the countdown keeps running) · `POST /checkins/{id}/ack {supporter}` · `POST /checkins/{id}/resolve {by, reason}` · `GET/PUT /people/{id}/safety` (settings; PINs write-only) · `POST /checkins/{id}/simulate {event: "disconnect"|"reconnect"}` (marks the person's device offline; the countdown carries on). Push state changes on the existing live WebSocket (`checkin` messages) so the UIs update instantly.
- Wording (SPEC §12): "check in", "alarm", "is everyone okay?"; never diagnostic.
- SPEC: a short §18 "Safety check-ins (Project KAZE)": the flow, the 7 scenarios, and what is real vs simulated (no real calls/SMS, simulated location, demo timings).
Acceptance: tests with a fake clock for all 7 KAZE scenarios: safe; no response → alarm; duress (person sees "ok", supervisor gets a silent duress alarm); disconnect after start → alarm still fires; unacknowledged → escalates to #2; false alarm resolved by a supporter and by the person; permissions (a supporter without `location` never gets it). The duress and safety responses are byte-identical. PINs never appear in any response or log. `scripts/ci.sh` passes.

### T451 — Check-in UI (person side): countdown, "I'm okay" + PIN pad
- status: claimed
- class: standard
- priority: 0
- kind: feature
- source: ian
- deps: —
- area: web/src/checkin/CheckInCard.tsx, web/src/checkin/CheckInCard.test.tsx, web/src/checkin/PinPad.tsx, web/src/checkin/PinPad.test.tsx, web/src/checkin/checkin.css, web/src/checkin/api.ts, web/src/checkin/types.ts, web/src/mock/checkins.ts, web/src/people/MyRoutine.tsx
- owner: ian-claude-standard-4
- claimed: 2026-10-17T23:57Z
- pr: —

What: The person's half of T450, built in parallel against T450's API shape with a mock (`web/src/mock/checkins.ts`). Follow `docs/DESIGN.md`. In "for myself" mode (`MyRoutine`), when a check-in is active, a calm full-width card appears: "Quick check-in: are you okay?", a large countdown ring, one big **I'm okay** button that opens a large-key PIN pad (works with shaky hands: big targets, no time pressure shown beyond the ring). After any accepted PIN, safety or duress, it shows the **same** "Thanks, you're checked in" screen (duress must be indistinguishable). A wrong PIN says "Try again" and the countdown continues. Accessible: focus moves to the card, `aria-live` announcements, keyboard only.
Acceptance: Vitest: the card shows for an active check-in; a wrong PIN keeps it pending; the safety and duress paths render identical DOM; countdown text updates; `cd web && npm test && npm run build`.

### T452 — Supervisor alarm UI: alarm banner + sound, acknowledge, escalation timeline, resolve
- status: todo
- class: standard
- priority: 0
- kind: feature
- source: ian
- deps: —
- area: web/src/checkin/AlarmBanner.tsx, web/src/checkin/AlarmBanner.test.tsx, web/src/checkin/EscalationTimeline.tsx, web/src/checkin/EscalationTimeline.test.tsx, web/src/checkin/alarmSound.ts, web/src/checkin/SafetySettings.tsx, web/src/checkin/SafetySettings.test.tsx, web/src/checkin/alarm.css, web/src/App.tsx
- owner: —
- claimed: —
- pr: —

What: The supervisor's half of T450, against the same mock as T451 (reuse `web/src/checkin/api.ts` / `types.ts` if T451 has landed; otherwise add them identically, since T451 owns them). In "supporting someone" mode, an `alarm` / `escalated` check-in shows a prominent, dismiss-proof **alarm banner** on every screen: "Mrs. K hasn't checked in (2 min)", plus "silent help request" for duress. It plays a repeating alarm tone made with Web Audio (no audio file), with a mute toggle and the browser's autoplay rule handled by an "Enable sound" control. Buttons: **I'm on it** (ack) and **Resolve** (false alarm / helped / other). An **escalation timeline** shows each step with times: alert → check-in sent → no answer → you were alarmed → escalated to {next} → acknowledged by → resolved. It shows only the fields the payload carries (respect T450's sharing permissions: no location line if it isn't shared). **SafetySettings**: an ordered supporter list, windows, and what each supporter may see; PINs are set but never displayed.
Acceptance: Vitest: the banner appears for an alarm and clears on resolve; duress shows "silent help request"; the timeline renders the events; no location when it's absent; sound starts/stops (mock AudioContext); `cd web && npm test && npm run build`.

### T453 — KAZE demo: scenario runner + docs (what's real vs simulated)
- status: todo
- class: light
- priority: 1
- kind: improvement
- source: ian
- deps: T450
- area: scripts/kaze_demo.py, docs/KAZE.md, tests/scenarios/kaze/
- owner: —
- claimed: —
- pr: —

What: `scripts/kaze_demo.py <scenario>` drives a running local stack through each of the 7 KAZE scenarios using only T450's HTTP API (`safe`, `no-response`, `duress`, `disconnect`, `unacknowledged`, `false-alarm`, `privacy`), with demo timings, printing each state change. `docs/KAZE.md` covers: the challenge mapping (each scenario → what to click or run), and a "What the prototype demonstrates / What is simulated / Assumptions / What needs validation" section (real push/SMS providers, location, wearable signals, false-alarm rates).
Acceptance: each scenario exits 0 against `scripts/dev.sh up`; `python3 scripts/kaze_demo.py --help` works; read only T450's API, nothing else.

### T454 — Impact evaluation on synthetic data: catch rate, false alarms, hours earlier (docs/EVAL.md)
- status: todo
- class: standard
- priority: 0
- kind: feature
- source: ian
- deps: —
- area: scripts/eval.py, pipeline/tests/test_eval.py, docs/EVAL.md, docs/eval/
- owner: —
- claimed: —
- pr: —
- note: released by max_API_standard-2: run ended without progress

What: Measurable impact for the "AI for Social Impact" track. `scripts/eval.py` runs the real pipeline (scoring, change detection, patterns; offline fakes, no paid calls) over a seeded synthetic cohort: about 50 people x 60 days generated with the existing generator (`pipeline/src/routine_watch/synth`), with labelled ground truth: a sudden change at a known onset (about 30%), a slow drift (about 15%), and normal with realistic noise (the rest). Report:
- **sudden changes caught** / missed (sensitivity), and **false alarms per person per month** on the normal group;
- **hours from onset to flag** (median, p90);
- versus a **weekly screening check** baseline (catches a change at the next weekly check if it is present then): median hours earlier;
- drift reported as a trend, not an alarm (count);
- a sensitivity sweep of the threshold (3 points) showing the false-alarm vs catch trade-off.
Write `docs/EVAL.md`: the numbers, one SVG/PNG chart in `docs/eval/` (hours earlier vs weekly check, or the trade-off curve; matplotlib only if it's already a dependency, otherwise a hand-made SVG), the method in 5 lines, and **limits stated plainly** (synthetic data, error rates from the literature, not clinical validation; what a real pilot would measure). Add a one-line "impact estimate" with its assumption shown (e.g. "if 1 in N caught changes avoids an ER visit...").
Why: the track asks for measurable societal impact; right now the pitch has no numbers.
Acceptance: deterministic (seeded, same numbers every run); finishes in < 60 s; a test runs a 5-person cohort and checks the metric keys and ranges; `scripts/ci.sh` passes.
