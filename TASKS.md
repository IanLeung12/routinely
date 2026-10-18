# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: d759735

## Tasks

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
- status: done
- class: light
- priority: 1
- kind: test
- deps: —
- area: scripts/smoke.sh
- owner: ian-claude
- claimed: 2026-10-17T23:50Z
- pr: #430
- source: proposed
- note: released by max_API_standard-2: run ended without progress
- rating: 5/5 clear

Why: the demo now shows the routine builder and replays, but `scripts/smoke.sh` (preflight before filming) never calls them; T443 showed these paths can break on the live API unnoticed.
What: add checks to `scripts/smoke.sh` in the existing `get` / `check_json` / `fail` style: `GET /routines` is a non-empty JSON list whose items have `id` and `title`; `GET /routines/<first id>` has a `task_graph`; `POST /routines/draft` with a short text description returns 200 with a task graph (fake drafter by default; skip this check with a printed note if it answers 503/501); `GET /people/<a person id>/replays` returns a JSON object (take the id from the residents/people list the script already fetches, as `demo_room` is derived).
Interface: read `scripts/smoke.sh`, `pipeline/src/routine_watch/api_routines.py` (request shape of `/routines/draft`), `pipeline/src/routine_watch/api_residents.py` lines 175–240. No changes outside `scripts/smoke.sh`.
Acceptance:
- `scripts/dev.sh up && scripts/smoke.sh; scripts/dev.sh down` passes on main with all new checks listed.
- Never makes a real Gemini call (LIVE_API unset).
- `scripts/ci.sh` passes.

### T449 — Stability: lazy-load AlertView and ResidentDetail to restore first-load bundle headroom
- status: done
- class: light
- priority: 1
- kind: improvement
- source: orchestrator
- deps: —
- area: web/src/App.tsx, web/scripts/check-bundle.mjs, web/README.md
- owner: ian-claude-heavy-3
- claimed: 2026-10-18T00:57Z
- pr: #439
- note: orch: T432 (#431) raised BUDGET_BYTES to 99_000 (measured 98,102); after lazy-loading AlertView/ResidentDetail lower it to new measured + ~1,500
- rating: 5/5 clear — the note named the exact measurement and the budget formula, and the existing tests already used findBy so none needed changing

What: The first-load JS budget has been bumped three times today (92,200 → 96,000 → 96,500) and main sits ~250 B under it, so every remaining pre-freeze UI PR risks a red "first-load JS over budget" CI. Make `AlertView` and `ResidentDetail` lazy in `App.tsx` the same way `Handoff`/`RoutinesScreen` already are, then lower the budget to measured + ~1,500 B.
Why: stops bundle-budget CI failures from blocking demo-path PRs in the last 90 minutes before the 01:30 UTC freeze.
Interface: in `web/src/App.tsx` replace the eager `import { AlertView }` / `import { ResidentDetail }` with `lazy(() => import(...).then(m => ({ default: m.X })))` and render them inside the existing `<Suspense fallback={<Loading .../>}>` pattern used for `RoutinesScreen`. Read only `web/src/App.tsx`, `web/scripts/check-bundle.mjs` and the bundle section of `web/README.md`.
Acceptance:
- `cd web && npm run build && npm run check:bundle` passes; set `BUDGET_BYTES` to the new measured total + ~1,500 and record the measured number in the comment and in web/README.md.
- Existing App tests pass (if a test uses sync `getBy` on the alert/resident screen right after navigation, switch only that query to `findBy`).
- `scripts/ci.sh` passes.

### T450 — Safety check-in backend: alert → check-in countdown → supervisor alarm → escalation (Project KAZE)
- status: done
- class: heavy
- priority: 0
- kind: feature
- source: ian
- deps: —
- area: pipeline/src/routine_watch/checkin.py, pipeline/src/routine_watch/api_checkin.py, pipeline/src/routine_watch/api.py, pipeline/src/routine_watch/api_live.py, pipeline/tests/test_checkin.py, pipeline/tests/test_api_checkin.py, SPEC.md
- owner: ian-claude-heavy-3
- claimed: 2026-10-17T23:57Z
- pr: #436
- rating: 4/5 clear on the state machine, windows, permissions and the 7 scenarios; the 'api_alerts/alerts.py' hook point does not exist in this codebase (alerts are derived from flags on read, so the hook had to go on the flagged session_end in api_live.py), and the area left out contracts/ + the dashboard's live-message union, so the new checkin WS message is additive and undocumented in contracts/

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
- status: done
- class: standard
- priority: 0
- kind: feature
- source: ian
- deps: —
- area: web/src/checkin/CheckInCard.tsx, web/src/checkin/CheckInCard.test.tsx, web/src/checkin/PinPad.tsx, web/src/checkin/PinPad.test.tsx, web/src/checkin/checkin.css, web/src/checkin/api.ts, web/src/checkin/types.ts, web/src/mock/checkins.ts, web/src/people/MyRoutine.tsx
- owner: max_API_standard
- claimed: 2026-10-18T00:58Z
- pr: #437
- rating: 4/5 clear task, but T450/T452 merged mid-work which required reconciling guessed mock shapes against the real backend's field names (checkin_id/state/ask vs id/status/deadline) - unavoidable given parallel work, not a flaw in the task itself
- note: merge conflict with main on PR #437: check out its branch, merge origin/main, fix, push

What: The person's half of T450, built in parallel against T450's API shape with a mock (`web/src/mock/checkins.ts`). Follow `docs/DESIGN.md`. In "for myself" mode (`MyRoutine`), when a check-in is active, a calm full-width card appears: "Quick check-in: are you okay?", a large countdown ring, one big **I'm okay** button that opens a large-key PIN pad (works with shaky hands: big targets, no time pressure shown beyond the ring). After any accepted PIN, safety or duress, it shows the **same** "Thanks, you're checked in" screen (duress must be indistinguishable). A wrong PIN says "Try again" and the countdown continues. Accessible: focus moves to the card, `aria-live` announcements, keyboard only.
Acceptance: Vitest: the card shows for an active check-in; a wrong PIN keeps it pending; the safety and duress paths render identical DOM; countdown text updates; `cd web && npm test && npm run build`.

### T452 — Supervisor alarm UI: alarm banner + sound, acknowledge, escalation timeline, resolve
- status: done
- class: standard
- priority: 0
- kind: feature
- source: ian
- deps: —
- area: web/src/checkin/AlarmBanner.tsx, web/src/checkin/AlarmBanner.test.tsx, web/src/checkin/EscalationTimeline.tsx, web/src/checkin/EscalationTimeline.test.tsx, web/src/checkin/alarmSound.ts, web/src/checkin/SafetySettings.tsx, web/src/checkin/SafetySettings.test.tsx, web/src/checkin/alarm.css, web/src/App.tsx
- owner: max_API_standard
- claimed: 2026-10-18T00:25Z
- pr: #435
- note: released by max_API_standard: run ended without progress
- rating: 4/5 Shared API field names were unspecified while T450 and T451 were still unlanded; otherwise clear.

What: The supervisor's half of T450, against the same mock as T451 (reuse `web/src/checkin/api.ts` / `types.ts` if T451 has landed; otherwise add them identically, since T451 owns them). In "supporting someone" mode, an `alarm` / `escalated` check-in shows a prominent, dismiss-proof **alarm banner** on every screen: "Mrs. K hasn't checked in (2 min)", plus "silent help request" for duress. It plays a repeating alarm tone made with Web Audio (no audio file), with a mute toggle and the browser's autoplay rule handled by an "Enable sound" control. Buttons: **I'm on it** (ack) and **Resolve** (false alarm / helped / other). An **escalation timeline** shows each step with times: alert → check-in sent → no answer → you were alarmed → escalated to {next} → acknowledged by → resolved. It shows only the fields the payload carries (respect T450's sharing permissions: no location line if it isn't shared). **SafetySettings**: an ordered supporter list, windows, and what each supporter may see; PINs are set but never displayed.
Acceptance: Vitest: the banner appears for an alarm and clears on resolve; duress shows "silent help request"; the timeline renders the events; no location when it's absent; sound starts/stops (mock AudioContext); `cd web && npm test && npm run build`.

### T453 — KAZE demo: scenario runner + docs (what's real vs simulated)
- status: claimed
- class: light
- priority: 1
- kind: improvement
- source: ian
- deps: T450
- area: scripts/kaze_demo.py, docs/KAZE.md, tests/scenarios/kaze/
- owner: ian-claude
- claimed: 2026-10-18T00:57Z
- pr: —

What: `scripts/kaze_demo.py <scenario>` drives a running local stack through each of the 7 KAZE scenarios using only T450's HTTP API (`safe`, `no-response`, `duress`, `disconnect`, `unacknowledged`, `false-alarm`, `privacy`), with demo timings, printing each state change. `docs/KAZE.md` covers: the challenge mapping (each scenario → what to click or run), and a "What the prototype demonstrates / What is simulated / Assumptions / What needs validation" section (real push/SMS providers, location, wearable signals, false-alarm rates).
Acceptance: each scenario exits 0 against `scripts/dev.sh up`; `python3 scripts/kaze_demo.py --help` works; read only T450's API, nothing else.

### T454 — Impact evaluation on synthetic data: catch rate, false alarms, hours earlier (docs/EVAL.md)
- status: done
- class: standard
- priority: 0
- kind: feature
- source: ian
- deps: —
- area: scripts/eval.py, pipeline/tests/test_eval.py, docs/EVAL.md, docs/eval/
- owner: ian-claude-standard-3
- claimed: 2026-10-18T00:15Z
- pr: #432
- note: released by max_API_standard-2: run ended without progress
- rating: 5/5 clear

What: Measurable impact for the "AI for Social Impact" track. `scripts/eval.py` runs the real pipeline (scoring, change detection, patterns; offline fakes, no paid calls) over a seeded synthetic cohort: about 50 people x 60 days generated with the existing generator (`pipeline/src/routine_watch/synth`), with labelled ground truth: a sudden change at a known onset (about 30%), a slow drift (about 15%), and normal with realistic noise (the rest). Report:
- **sudden changes caught** / missed (sensitivity), and **false alarms per person per month** on the normal group;
- **hours from onset to flag** (median, p90);
- versus a **weekly screening check** baseline (catches a change at the next weekly check if it is present then): median hours earlier;
- drift reported as a trend, not an alarm (count);
- a sensitivity sweep of the threshold (3 points) showing the false-alarm vs catch trade-off.
Write `docs/EVAL.md`: the numbers, one SVG/PNG chart in `docs/eval/` (hours earlier vs weekly check, or the trade-off curve; matplotlib only if it's already a dependency, otherwise a hand-made SVG), the method in 5 lines, and **limits stated plainly** (synthetic data, error rates from the literature, not clinical validation; what a real pilot would measure). Add a one-line "impact estimate" with its assumption shown (e.g. "if 1 in N caught changes avoids an ER visit...").
Why: the track asks for measurable societal impact; right now the pitch has no numbers.
Acceptance: deterministic (seeded, same numbers every run); finishes in < 60 s; a test runs a 5-person cohort and checks the metric keys and ranges; `scripts/ci.sh` passes.

### T455 — Bug: "Draft routine" blanks the whole dashboard (API task_graph steps use `deps`, UI reads `depends_on`)
- status: done
- class: light
- priority: 0
- kind: bug
- deps: —
- area: web/src/routines/api.ts, web/src/routines/api.test.ts, web/src/routines/RoutineBuilder.test.tsx
- source: tester
- owner: max_API_light
- claimed: 2026-10-18T00:25Z
- pr: #434
- rating: 4/5 saved graph alias behavior required confirmation; otherwise clear

What: on main @2e488ba with the dev stack up (`OFFLINE_MODE=true scripts/dev.sh up`), click **New routine** → **Brushing teeth** example (any example) → **Draft routine**: the React root unmounts and the page goes blank. Console: `TypeError: can't access property "includes", step.depends_on is undefined` (StepEditor.tsx:65/130). Cause: `POST /routines/draft` answers 200 with `task_graph.steps[*].deps` (routine_builder.py ~847), but `web/src/routines/types.ts` `RoutineStep` and `StepEditor` expect `depends_on`. Before T444 this was hidden by the mock fallback; now the real (fake-drafter) response reaches the UI. Repro API side: `curl -s -X POST -F "description=Get the toothbrush, then brush" localhost:8000/routines/draft` → steps have `deps`, no `depends_on`. This is on docs/DEMO.md's click path (routine builder step).
Expected: draft renders the task map + step editor; Save routine works.
Interface: normalize in `web/src/routines/api.ts` (map `deps` → `depends_on`, default missing `objects`/`depends_on` to `[]`, `needs_training`/`warnings` to `[]`) for `draftFromText`, `draftFromVideo` and any fetched `SavedRoutine.task_graph`. Check that `POST /routines` accepts what the UI sends (backend accepts `depends_on`/`deps` aliases on draft steps; confirm for the saved graph). Don't change `contracts/` or the API.
Acceptance:
- api.test.ts: a draft response whose steps use `deps` comes back with `depends_on`.
- RoutineBuilder test: drafting with a `deps`-shaped response renders the step editor without throwing.
- Manual: the click path above shows the draft and saves it to the Routines list.
- `scripts/ci.sh` passes.

### T456 — Review: Replays delete swallows a failed delete (unhandled rejection, no message)
- status: done
- class: light
- priority: 0
- kind: bug
- source: reviewer
- deps: —
- area: web/src/replays/Replays.tsx, web/src/replays/Replays.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-18T00:32Z
- pr: #438
- note: —
- rating: 5/5 clear

What: In `web/src/replays/Replays.tsx`, `confirmDelete` awaits `deleteReplay` with no try/catch and is called as `void confirmDelete(...)`. When the delete is refused (already possible for "Replay not found"; every non-ok once T441 lands), the promise rejection is unhandled, the confirm box stays open and the person gets no feedback, so they can't tell whether their replay (SPEC §17 privacy control) was removed.
Interface: wrap the call in try/catch; on failure keep the replay in the list and on screen, close the confirm, and show the error with `ErrorState` from `web/src/ui/` (e.g. "This replay could not be deleted. It is still stored."). Only filter the list and close the session on success.
Acceptance:
- Replays.test.tsx: person role, `deleteReplay` mocked to reject → error message shown, replay still listed after going back; resolve → removed.
- `scripts/ci.sh` passes.

### T457 — Bug: supervisor alarm UI (T452) doesn't speak the real check-in API (T450)
- status: claimed
- class: standard
- priority: 0
- kind: bug
- deps: T450, T452
- area: web/src/checkin/api.ts, web/src/checkin/types.ts, web/src/checkin/AlarmBanner.tsx, web/src/checkin/AlarmBanner.test.tsx, web/src/checkin/SafetySettings.tsx, web/src/checkin/SafetySettings.test.tsx, web/src/checkin/EscalationTimeline.tsx, web/src/checkin/EscalationTimeline.test.tsx
- owner: ian-claude-standard-4
- claimed: 2026-10-18T01:18Z
- pr: —
- note: orch review of #435/#436; overlaps T451 (#437) files, so it waits for that merge. Keep T451's person-side changes intact.

What: T452 and T450 merged in parallel against different shapes, so with a live API the supervisor alarm banner and safety settings break (works only on the fake). Make `web/src/checkin/api.ts` + `types.ts` match `pipeline/src/routine_watch/api_checkin.py` / `checkin.py` (the backend is the source of truth; don't change it).
Interface (mismatches found):
- `GET /checkins/active` 422s when both `person` and `supporter` are sent; the supervisor banner must send only `?supporter=`. Response is `{"checkins": [...]}`, not a bare array.
- `/ack`, `/resolve` answer `{"checkin": {...}}`.
- Supporter view fields: `checkin_id` (not `id`), `state` (not `status`), `started_at` (not `created_at`), `person_name`, `seconds_left`, etc. (see `supporter_view` in checkin.py); map them in api.ts or change the types and consumers.
- Safety settings use `checkin_window_s` / `ack_window_s` (not `checkin_window`/`ack_window`), and `SafetyIn` is `extra="forbid"`, so the current PUT 422s.
Acceptance:
- api.ts tests stub `fetch` with payloads copied from the backend shapes (supporter_view, settings_payload) and pass; fake (offline) path still works.
- With `scripts/dev.sh up`, `POST /checkins/demo` then waiting past the window shows the alarm banner for a linked supporter; acknowledge and resolve work; safety settings save without 422.
- `scripts/ci.sh` passes.
