# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: 5d23e21

## Tasks

### T062 — Nurse shift handoff summary (separate screen)
- status: todo
- class: heavy
- priority: 3
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/handoff.py, pipeline/src/routine_watch/api.py (add the route only), pipeline/tests/test_handoff.py, web/src/handoff/, web/src/App.tsx (one nav entry)
- owner: —
- claimed: —
- pr: —
- source: proposed

What: Rationale: a nurse starting a shift wants one view of "who changed in the last 12 h" (Usefulness/Clarity, Use-of-AI hook). `GET /handoff?hours=12` lists residents with flags, pending-review alerts and drift trends in that window, plus a short plain-language summary from the existing `Explainer` interface (fake by default, no real call without `LIVE_API=1`). Wording: "flagged for review", never "diagnosed".
Interface: `handoff.build_handoff(now, hours) -> {"window_hours": int, "residents": [{"resident_id", "name", "flags": int, "pending_review": int, "trending": bool}], "summary": str}`; web screen `web/src/handoff/Handoff.tsx` reachable from one button in `App.tsx`, off the main demo path.
Acceptance:
- pytest: Mrs. K appears with her flag in the demo window; stable resident has 0 flags; summary comes from the fake explainer and contains no "diagnos".
- Web test renders the list and summary from mock data.
- `scripts/ci.sh` passes.

### T068 — Show the demo-data banner in the app
- status: todo
- class: light
- priority: 3
- kind: feature
- deps: T052, T063
- area: web/src/App.tsx, web/src/App.test.tsx
- owner: —
- claimed: —
- pr: —

What: Render the `DemoBanner` component from T052 (`web/src/ui/DemoBanner.tsx`) once, at the top of `App.tsx` above the header, on every screen.
Interface: read only `App.tsx`, `App.test.tsx`, `ui/DemoBanner.tsx`.
Acceptance:
- App test: banner visible on overview and after opening a resident.
- `scripts/ci.sh` passes.

### T071 — Tests for useLiveSession and mockLiveStream
- status: claimed
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/live/useLiveSession.test.ts, web/src/live/mockLiveStream.test.ts
- owner: max-codex-light-1
- claimed: 2026-10-17T06:01Z
- pr: —

What: The live screen's state hook and mock stream are untested. Read only `web/src/live/useLiveSession.ts`, `web/src/live/mockLiveStream.ts`, `web/src/live/LiveSession.test.tsx` (how it fakes the socket) and `.tasks/LESSONS.md` (pending effects after teardown break CI).
Interface: new test files only; use `vi.useFakeTimers()` and a fake WebSocket; no real network.
Acceptance:
- mockLiveStream: emits messages in order, ends with a session-ended message, and the returned stop function stops further messages.
- useLiveSession (renderHook): step states update from messages, the end message sets the ended state, and the socket closes on unmount.
- `cd web && npm run lint && npm test && npm run build` passes, run twice with no flakes.

### T076 — Tests for ContextTimeline and BaselineChart
- status: claimed
- class: light
- priority: 2
- kind: test
- deps: —
- area: web/src/resident/ContextTimeline.test.tsx, web/src/resident/BaselineChart.test.tsx
- owner: max-codex-light-2
- claimed: 2026-10-17T06:07Z
- pr: —

What: Both resident-detail components have no tests. Add focused render tests; do not change the components.
Interface: read only web/src/resident/ContextTimeline.tsx, web/src/resident/BaselineChart.tsx, web/src/resident/types.ts, and web/src/resident/format.test.ts (for test style). Use vitest + @testing-library/react like the existing tests.
Acceptance:
- ContextTimeline: empty list shows "No care records for this resident."; records render newest first; temperature/fluid_intake/med_change get their readable labels ("Temperature 37.9 °C", "Fluid intake 800 ml", "Medication change: ...").
- BaselineChart: renders without crashing for typical props and for an empty series (no NaN in rendered attributes).
- `cd web && npm test -- --run` and `scripts/ci.sh` pass.

### T088 — Alert screen shows ranked possible patterns
- status: todo
- class: standard
- priority: 1
- kind: feature
- deps: T084, T085
- area: web/src/alert/AlertView.tsx, web/src/alert/AlertView.test.tsx, web/src/alert/PatternList.tsx, web/src/mock/alerts.ts
- owner: —
- claimed: —
- pr: —

What: SPEC §9 screen 4 / demo step 5: the alert view shows "Possible patterns" right under the summary, from `Alert.patterns`.
Interface: switch `PatternList` to the generated `PatternMatch` type from `web/src/contracts.ts` (drop the local `PatternView` or alias it); render it in `AlertView` between summary and error list; give mock Mrs. K alert a `sudden_change` top pattern with evidence and rule-out checks.
Acceptance:
- Vitest: AlertView renders the top pattern name and its checks; an alert with `patterns: []` shows "no clear pattern".
- `scripts/ci.sh` passes.

### T089 — Unit overview shows the top pattern for flagged/watch residents
- status: todo
- class: standard
- priority: 2
- kind: feature
- deps: T084
- area: pipeline/src/routine_watch/demo.py, pipeline/src/routine_watch/api.py, pipeline/tests/test_api_residents.py, web/src/overview/, web/src/mock/residents.ts
- owner: —
- claimed: —
- pr: —

What: SPEC §9 screen 1 and demo step 6 ("Mr. D on watch, slow drift"): each flagged or watch resident row shows its top pattern name next to the status chip.
Interface: `GET /residents` items gain `top_pattern: {pattern_id, name, urgency} | null` from T084's scorer; `web/src/overview/types.ts` `ResidentSummary.top_pattern`; `UnitOverview` renders it as text (not colour alone); normal residents show nothing.
Acceptance:
- pytest: Mrs. K's `top_pattern.pattern_id == "sudden_change"`, drift resident's is `slow_drift`, normal residents `null`.
- Vitest: row shows pattern text for flagged resident, none for normal.
- `scripts/ci.sh` passes.

### T096 — Scenario: teabag added three times is perseveration, stirring twice is not
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/tea_teabag_three_times/
- owner: ian-claude-light-2
- claimed: 2026-10-17T07:21Z
- pr: #97
- note: rewritten by orchestrator: stir is once_only:false in tea.yaml by design (repeat stirring is normal), so use teabag_in_cup (once_only default true) instead.

What: Repeating a once-only step after other steps is the signal behind the executive pattern (SPEC §7.5, perseveration with intact order). Add a steps-level scenario: a complete, correctly ordered tea session where `teabag_in_cup` is done again after `pour` and once more after `stir`, and `stir` itself happens twice (which must NOT count). Read only `pipeline/src/routine_watch/tasks/tea.yaml` (the `once_only` comment at the top), `tests/scenarios/tea_kettle_twice/` and `tests/scenarios/tea_substitution/` (copy their shape). Do not edit `tests/scenarios/README.md` or `tea.yaml`.
Interface: `tests/scenarios/tea_teabag_three_times/{expected.yaml,steps.jsonl}` with a comment saying what it's for; no history, so `flag: false`.
Acceptance:
- `scripts/e2e.sh tests/scenarios/tea_teabag_three_times` passes and asserts perseveration error(s) on `teabag_in_cup` only, none on `stir`, and no omission/sequence errors.
- `scripts/ci.sh` passes.

### T097 — Scenario: two bad sessions 60 h apart do not flag
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/tea_bad_sessions_far_apart/
- owner: ian-claude-light-2
- claimed: 2026-10-17T07:17Z
- pr: #95

What: Guards the 48 h window end to end: today's bad session (teabag skipped) plus one bad session 60 hours ago and quiet older history must **not** flag. Read only `tests/scenarios/README.md` (the `history:` section) and `tests/scenarios/tea_skip_teabag_pour_twice/` (copy its shape; that one flags with a bad session 30 h ago). Do not edit `tests/scenarios/README.md`.
Interface: `tests/scenarios/tea_bad_sessions_far_apart/{expected.yaml,steps.jsonl}` with a comment saying what it's for; `history:` has at least three quiet sessions plus the 60 h bad one; `flag: false`.
Acceptance:
- `scripts/e2e.sh tests/scenarios/tea_bad_sessions_far_apart` passes; changing 60 to 30 makes it flag (check locally, mention in PR).
- `scripts/ci.sh` passes.

### T098 — scripts/smoke.sh: hit every API route of a running stack
- status: done
- class: standard
- priority: 2
- kind: test
- deps: —
- area: scripts/smoke.sh (new)
- owner: ian-claude-standard-2
- claimed: 2026-10-17T06:29Z
- pr: #79

What: The tester and the demo-day checklist need one command that proves a running `scripts/dev.sh up` stack answers correctly, without a browser. Read `scripts/dev.sh`, `scripts/e2e.sh` (style) and the route list in `pipeline/src/routine_watch/api.py`.
Interface: `scripts/smoke.sh [API_URL]` (default `http://localhost:${API_PORT:-8000}`): checks `GET /health`, `GET /residents` (non-empty, `mrs-k` present), `GET /residents/mrs-k`, `GET /alerts`, `GET /alerts/<first id>`, and that the dashboard URL (`DASHBOARD_PORT`, default 5173) returns HTML. Uses `curl` + `python3 -c` for JSON (no `jq`). Prints PASS/FAIL per check, exits non-zero on any failure. Never sets `LIVE_API`. Does not POST feedback (it mutates state).
Acceptance:
- `scripts/dev.sh up && scripts/smoke.sh; scripts/dev.sh down` passes locally (paste output in PR); with the stack down it fails fast (≤10 s) with a clear message.
- `shellcheck scripts/smoke.sh` clean if available; `scripts/ci.sh` passes.

### T099 — Unit overview: one-line status summary at the top
- status: in-review
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/overview/UnitOverview.tsx, web/src/overview/UnitOverview.test.tsx
- owner: ian-claude-light-2
- claimed: 2026-10-17T07:25Z
- pr: #100

What: For the 10-second read (SPEC §9), the overview should say up front how many residents need attention. Read only the two files in `area`, `web/src/overview/types.ts` and `web/src/ui/SectionHeader.tsx`.
Interface: above the list render `<p role="status">` with e.g. "2 flagged for review · 1 on watch · 3 normal" (counts from the fetched residents; omit zero parts; "All residents normal" when nothing is flagged or on watch). Nothing while loading. No new fetches.
Acceptance:
- Vitest (stub `fetch` and `await screen.findBy…` per LESSONS): mixed statuses give the right counts; all-normal gives "All residents normal"; existing tests pass.
- `cd web && npm run lint && npm test && npm run build` passes.

### T100 — Feedback store records "what was it?" causes per resident
- status: done
- class: standard
- priority: 2
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/feedback.py, pipeline/tests/test_feedback.py
- owner: ian-claude-standard
- claimed: 2026-10-17T06:29Z
- pr: #80

What: The dashboard now has a "What was it?" picker (#76, SPEC §5 MVP 8). Prepare the backend half without touching contracts or the API (both busy): the store keeps an optional cause per alert and counts causes per resident, which the pattern feedback loop (Nice to have 8) will use later.
Interface: `FeedbackStore.record(alert_id, resident_id, feedback, cause: str | None = None)` (existing callers unchanged); `FeedbackStore.cause_of(alert_id) -> str | None`; `FeedbackStore.cause_counts(resident_id) -> dict[str, int]` counting only `confirmed` alerts; re-recording an alert replaces its cause. Cause ids are free strings (pattern ids or `"other"`). Thresholds behave exactly as before.
Acceptance:
- pytest: cause stored and replaced; false alarms don't count; counts are per resident; existing threshold tests unchanged and passing.
- `scripts/ci.sh` passes.

### T101 — Evidence players: keyboard and screen-reader pass
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/evidence/ReplayPlayer.tsx, web/src/evidence/ReplayPlayer.test.tsx, web/src/evidence/GhostReplay.tsx, web/src/evidence/GhostReplay.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T06:52Z
- pr: #86

What: The skeleton replay and ghost replay are the evidence a nurse opens "one tap away" (SPEC §9); make them usable without a mouse and honest to screen readers. Read only the files in `area` and `web/src/ui/Button.tsx`.
Interface: play/pause is a real `<button>` with `aria-pressed` or a changing label; the scrubber (if any) has `aria-valuetext` like "12.0 s of 40.0 s"; Space toggles play when the player is focused; the drawing has `role="img"` with an `aria-label` saying what is shown (e.g. "Skeleton replay, today vs usual routine"); respect `prefers-reduced-motion` by not auto-playing. No prop changes that break current callers.
Acceptance:
- Vitest: keyboard toggle works; accessible names present; no autoplay when `matchMedia('(prefers-reduced-motion: reduce)')` matches (stub it).
- note: released by ian-claude-standard-2: run ended without progress
- `cd web && npm run lint && npm test && npm run build` passes.

### T102 — Docs: README quickstart for teammates and judges
- status: todo
- class: light
- priority: 2
- kind: docs
- deps: —
- area: README.md
- owner: —
- claimed: —
- pr: —

What: Make the top-level README a 1-minute quickstart. Read only `README.md`, `scripts/dev.sh`, `scripts/e2e.sh`, `scripts/ci.sh` (headers only) and SPEC.md §1 and §12.
Interface: sections: what it is (2 lines, "flags a change for review"; never any form of "diagnos*"), run it (`scripts/dev.sh up|down`, ports), test it (`scripts/ci.sh`, `scripts/e2e.sh`), offline by default (`OFFLINE_MODE`, `LIVE_API` unset = fakes, no paid calls), privacy (skeletons and boxes only, no video stored), where things are (pointers to `docs/CODEMAP.md`, `tests/scenarios/README.md`). Under ~80 lines.
Acceptance:
- Every command in it works from a fresh clone (say which you ran in the PR).
- `scripts/ci.sh` passes (test_privacy.py scans wording).

### T103 — Room monitoring pause toggle (component only)
- status: todo
- class: light
- priority: 3
- kind: feature
- deps: —
- area: web/src/about/MonitoringToggle.tsx (new), web/src/about/MonitoringToggle.test.tsx (new)
- source: proposed
- owner: —
- claimed: —
- pr: —

What: Responsible design made visible for judges (SPEC §12: "per room and can be turned off"): a per-room monitoring on/paused switch. Component only; wiring and API are later tasks. Read only `web/src/about/PrivacyPanel.tsx` (style) and `web/src/ui/Button.tsx`.
Interface: `export function MonitoringToggle({ room, on, onChange }: { room: string; on: boolean; onChange: (on: boolean) => void })` renders `<button role="switch" aria-checked={on}>` labelled "Monitoring in room {room}" with visible text "On" / "Paused", plus when paused a note "No camera data is processed while paused." CSS vars only.
Acceptance:
- Vitest: role switch with correct `aria-checked`; click calls `onChange(!on)`; paused note shows only when off.
- `cd web && npm run lint && npm test && npm run build` passes.

### T104 — Session quality: mostly-unclear sessions are unclear, not scored
- status: done
- class: standard
- priority: 2
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/quality.py (new), pipeline/tests/test_quality.py (new)
- owner: ian-claude-standard
- claimed: 2026-10-17T06:33Z
- pr: #82

What: SPEC §12/§13: pose and detection are less reliable with walkers, wheelchairs or bad lighting; low-confidence sessions must be treated as unclear rather than as errors, so they never push a resident toward a flag. Add the pure rule now; wiring it into replay/live is a later task (those files are busy).
Interface: `session_quality(events: list[StepEvent], *, unclear_fraction: float = 0.4, min_events: int = 3) -> Literal["ok", "unclear"]`: `unclear` when there are fewer than `min_events` events or more than `unclear_fraction` of them are unclear / below confidence 0.6 (import an existing threshold constant from `recogniser.py` or `verifier.py` if one exists; don't copy it). Module docstring cites SPEC §12. Read `contracts.py` (`StepEvent` only) and `recogniser.py` / `verifier.py` for the constant. Add a one-line note for `docs/CODEMAP.md` in the PR description (don't edit it; it's busy).
Acceptance:
- pytest: clean session → ok; half unclear → unclear; too few events → unclear; exactly at the fraction → ok.
- `scripts/ci.sh` passes.

### T105 — Review: Claude summary guard lets spelled-out numbers through
- status: todo
- class: light
- priority: 2
- kind: bug
- deps: —
- area: pipeline/src/routine_watch/explain_claude.py, pipeline/tests/test_explain_claude.py
- source: reviewer

What: `_passes_guard` only checks digit tokens (`_NUMBER_RE`), so a reply like "Mrs. K made three errors" when she made 2 passes and a nurse sees a wrong count (SPEC §6.4: never state a number not in the facts).
Interface: in `explain_claude.py`, map number words `one`..`twenty` (whole-word, case-insensitive) to digits before the allowed-number check, so they must also be in `_allowed_numbers`. Nothing else changes.
Acceptance:
- tests: fake client replying "three errors" with observed=2 → template fallback; "two errors" with observed=2 → Claude reply kept; "someone" / "once" are not treated as numbers.
- owner: —
- `cd pipeline && uv run pytest -q` passes.

### T106 — Evidence replay: stop fetching the alert twice
- status: todo
- class: light
- priority: 3
- kind: improvement
- deps: —
- area: web/src/evidence/api.ts, web/src/evidence/api.test.ts, web/src/alert/AlertView.tsx
- owner: —
- claimed: —
- pr: —

What: Since T080 (#84), `AlertView` loads the alert with `fetchAlert`, then `fetchReplay(alertId)` calls `fetchAlert` again for the same alert. Change `fetchReplay` to take the already-loaded `Alert` so the screen makes one alert request.
Interface: `fetchReplay(alert: Alert): Promise<EvidenceReplay | null>` in `web/src/evidence/api.ts`; in `AlertView.tsx`, run the replay effect once the alert has loaded (keyed on alert id). Read only these three files plus `web/src/alert/AlertView.test.tsx`.
Acceptance:
- `api.test.ts` updated to pass an `Alert`; no `fetchAlert` call inside `evidence/api.ts`.
- AlertView still shows Loading / Empty / replay states as before (existing tests pass unchanged in behaviour).
- `cd web && npm test` and `scripts/ci.sh` pass.

### T107 — Review: evidence ghost layer replays the same frames as "today"
- status: done
- class: standard
- priority: 0
- kind: bug
- source: reviewer
- deps: —
- area: pipeline/src/routine_watch/evidence.py, pipeline/tests/test_evidence.py, tests/scenarios/tea_normal/frames.jsonl
- owner: ian-claude-standard-2
- claimed: 2026-10-17T07:02Z
- pr: #93

What: `evidence.py` sets both `_ALERT_SCENARIO` and `_NORMAL_SCENARIO` to `tea_no_kettle`, so `GET /residents/{id}/normal_replay` returns exactly the frames of `GET /sessions/{id}/replay` (only `session_id` differs). On the alert screen the ghost overlay sits perfectly on top of today's skeleton, so demo step 5 ("compare against her normal routine") shows no difference.
Fix: add a frame-level `tests/scenarios/tea_normal/frames.jsonl` (same capture format and timing as `tea_no_kettle/frames.jsonl`, but with the fill-kettle and boil contacts, so the recogniser reads all tea steps; check `tea_normal/expected.yaml` still passes via `scripts/e2e.sh`) and point `_NORMAL_SCENARIO` at `tea_normal`.
Acceptance:
- New test in `test_evidence.py`: for the same window, `normal_replay_frames` and `replay_frames` return different landmark/object data.
- `scripts/ci.sh` passes (including e2e on `tea_normal`).

### T108 — Review: smoke.sh skips the evidence replay routes and isn't syntax-checked in CI
- status: done
- class: light
- priority: 1
- kind: test
- source: reviewer
- deps: —
- area: scripts/smoke.sh, scripts/ci.sh
- owner: ian-claude-light-2
- claimed: 2026-10-17T07:01Z
- pr: #88

What: T037/T080 added `GET /sessions/{session_id}/replay` and `GET /residents/{resident_id}/normal_replay` (`pipeline/src/routine_watch/api.py`), which the alert screen's evidence card depends on, but `scripts/smoke.sh` only checks health/residents/alerts, so a broken replay route passes the demo-day checklist. `scripts/ci.sh` also runs `bash -n` on other scripts but not `smoke.sh`.
Fix: in `smoke.sh`, after fetching the first alert, read its `errors[0].session_id`, `t_start`, `t_end` and `resident_id` (same inline python3 JSON parsing the script already uses) and check both replay routes return a non-empty `frames` list; add `bash -n scripts/smoke.sh` to the "repo tooling" block of `ci.sh`. Read only these two files plus the two route handlers in `api.py`.
Acceptance:
- PASS/FAIL lines for both new checks; FAIL (non-zero exit) on 404 or empty frames.
- `scripts/ci.sh` passes.

### T109 — Resident detail: not-found, API-down and no-sessions states
- status: todo
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/ResidentDetail.tsx, web/src/resident/ResidentDetail.test.tsx
- owner: —
- claimed: —
- pr: —
- note: released by ian-claude-standard: run ended without progress

What: The resident screen must stay legible when things go wrong: an unknown resident id, the API being unreachable, or a resident with no sessions yet. A nurse should understand each state in 10 s.
Interface: `ResidentDetail` only; reuse the existing `web/src/resident/api.ts` fetch (do not change it) and existing CSS classes/design tokens.
Acceptance:
- 404 → "Resident not found" with a link back to the unit overview.
- network/5xx error → short plain message + a "Try again" button that refetches.
- zero sessions → empty-state copy instead of blank charts (no crash in BaselineChart/HeatCalendar).
- Tests for all three states in ResidentDetail.test.tsx; `scripts/ci.sh` passes.

### T110 — Live task map: step state not conveyed by colour alone
- status: done
- class: standard
- priority: 2
- kind: improvement
- deps: —
- area: web/src/live/TaskMap.tsx, web/src/live/TaskMap.test.tsx, web/src/live/TaskMapLegend.tsx, web/src/live/TaskMapLegend.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T07:14Z
- pr: #96

What: The red/amber flashes in the live task map (demo beat 3) are colour-only. Add a text/icon cue and an accessible name per step so the state reads for colour-blind judges and screen readers.
Interface: each `role="listitem"` step gets an accessible name like "Add teabag — missed" / "Pour water — repeated" / "Boil kettle — done"; a visible icon or short label per non-pending state; legend uses the same icons.
Acceptance:
- Tests query steps by accessible name for each state (pending, active, done, omission, repeat/sequence).
- No behaviour change to state transitions; existing tests still pass.
- `scripts/ci.sh` passes.

### T111 — Demo residents: evening-only worsening and motor slowing
- status: done
- class: standard
- priority: 1
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/demo.py, pipeline/tests/test_demo.py
- owner: ian-claude-standard-2
- claimed: 2026-10-17T07:23Z
- pr: #98

What: SPEC §8 wants 5–6 demo residents, one per pattern. The generators for `"evening"` (T086) and `"motor"` (T087) exist but no demo resident uses them. Add two residents to the demo config with pinned seeds.
Interface: two new entries in the resident config list in `demo.py` (`scenario: "evening"` and `scenario: "motor"`, new ids/names/rooms); no API or contract change.
Acceptance:
- pytest in `test_demo.py`: both new residents appear in `demo_residents()`, deterministic across calls; the evening resident's evening (≥16:00) sessions in the last 7 days average ≥3× the errors of its morning ones; the existing four residents keep their current status (the T091 status test still passes unchanged).
- `scripts/ci.sh` and `scripts/e2e.sh` pass.

### T112 — AlertContext: care-record context next to the alert (component only)
- status: todo
- class: light
- priority: 2
- kind: feature
- deps: —
- area: web/src/alert/AlertContext.tsx (new), web/src/alert/AlertContext.test.tsx (new)
- owner: —
- claimed: —
- pr: —

What: SPEC §5 Nice to have 5: show care-record context (new meds, temperature, fluids) beside an alert. Build a small component that shows only the records from the 72 h before the alert time, newest first; not wired into AlertView yet.
Interface: `AlertContext({ records: CareRecord[], alertTs: string, windowHours?: number })`. Read only `web/src/resident/types.ts` (CareRecord), `web/src/resident/ContextTimeline.tsx` (copy its formatting; reuse its helpers if exported) and `web/src/ui/EmptyState.tsx`. Empty window → EmptyState "No care-record changes in the last 3 days".
Acceptance:
- vitest: filters to the window, orders newest first, med_change rows are labelled as medication, empty state shown when nothing is in the window.
- `scripts/ci.sh` passes.

### T113 — Pattern scenarios: one replayable scenario per pattern
- status: todo
- class: standard
- priority: 1
- kind: test
- deps: T084
- area: tests/scenarios/pattern_*/, tests/scenarios/README.md, pipeline/src/routine_watch/replay.py (expected top-pattern check only), pipeline/tests/test_replay.py
- owner: —
- claimed: —
- pr: —

What: SPEC §8: at least one scenario per MVP pattern (sudden change, slow drift) with the expected top pattern in `expected.yaml`, plus "no clear pattern" for a flag that matches none.
Interface: optional `top_pattern: <pattern id> | none` key in `expected.yaml`; `scripts/e2e.sh` fails when the scorer's top pattern differs. Scenarios without the key are unaffected.
Acceptance:
- ≥3 new scenarios (`pattern_sudden_change`, `pattern_slow_drift`, `pattern_none`), each with history context in the same format existing flagging scenarios use.
- pytest covers the new key (match, mismatch, absent); `scripts/e2e.sh` passes; README table updated.

### T114 — api.py: one resident lookup helper instead of copy-pasted loops
- status: todo
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: pipeline/src/routine_watch/api.py, pipeline/tests/test_api_residents.py
- owner: —
- claimed: —
- pr: —

What: `get_resident`, `resident_drift` and the replay routes each loop over `demo_residents()` and raise the same 404. Extract `_resident_or_404(resident_id) -> dict` and use it everywhere. No behaviour change.
Interface: private helper in `api.py`; routes and responses unchanged. Read only `api.py` and `pipeline/tests/test_api*.py`.
Acceptance:
- No remaining `for resident in demo_residents()` loops in route bodies.
- New test: every resident-scoped route returns 404 with `{"detail": "resident not found"}` for an unknown id.
- `scripts/ci.sh` passes.

### T115 — Docs: CODEMAP notes for drift endpoint, evidence sources, smoke.sh, feedback causes
- status: todo
- class: light
- priority: 2
- kind: docs
- deps: —
- area: docs/CODEMAP.md
- owner: —
- claimed: —
- pr: —

What: Recent merges (T050 drift endpoint, T107 evidence replays `tea_no_kettle` with a `tea_normal` ghost, T098/T108 `scripts/smoke.sh`, T100 feedback causes) aren't in the CODEMAP notes. Add 1–3 lines each.
Interface: notes only; read the module docstrings of `pipeline/src/routine_watch/{api,evidence,feedback,drift}.py` and the header of `scripts/smoke.sh`. Run `python3 scripts/codemap.py` to regenerate the file list.
Acceptance:
- Each of the four is described where a newcomer would look; no stale claims (e.g. "evidence replays one scenario").
- `scripts/ci.sh` passes.

### T116 — Scenario: pill taken before the water is poured is a sequence error
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/meds_pill_before_water/
- owner: —
- claimed: —
- pr: —

What: The second task has only a normal and an omission scenario. Add a step-level scenario where the pill is taken before the glass is filled, producing exactly one sequence error.
Interface: `steps.jsonl` + `expected.yaml` in the same format as `tests/scenarios/meds_skip_water/`. Read only `pipeline/src/routine_watch/tasks/meds.yaml`, `tests/scenarios/meds_skip_water/*` and `tests/scenarios/tea_sequence_error/*`.
Acceptance:
- `scripts/e2e.sh` passes with the new scenario listed; the error list is exactly one sequence error on the correct step.
- Note in the PR that `tests/scenarios/README.md` needs a row (outside area; the orchestrator will batch README rows).

### T117 — Web mock residents include the evening and motor residents
- status: todo
- class: light
- priority: 2
- kind: feature
- deps: T111
- area: web/src/mock/residents.ts, web/src/mock/residentDetail.ts
- owner: —
- claimed: —
- pr: —

What: The offline web fallback should show the same residents as the API after T111. Add the two new residents (same ids, names, rooms, status) to the web mocks.
Interface: mirror the ids/names from `pipeline/src/routine_watch/demo.py`; keep the existing mock shape.
Acceptance:
- vitest: mock list ids equal the API demo ids (hard-coded list in the test, with a comment pointing at demo.py).
- `scripts/ci.sh` passes.

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

### T119 — Bug: API sends no CORS headers, so the dashboard silently shows mock data
- status: claimed
- class: light
- priority: 0
- kind: bug
- deps: —
- area: pipeline/src/routine_watch/api.py (middleware only), pipeline/tests/test_api_cors.py (new)
- owner: ian-claude-standard-2
- claimed: 2026-10-17T07:29Z
- pr: —
- source: tester

What: With `scripts/dev.sh up` (dashboard :5173, API :8000), every `fetch` from the dashboard to the API fails in the browser with `TypeError: NetworkError` because API responses have no `access-control-allow-origin` header. The web clients catch that and fall back to `web/src/mock/*`, so overview, Mrs. K detail and the alert screen show mock data (e.g. Mr. Chen "watch" vs API "normal"; alert threshold 1.2 vs API 4.09), and "Confirmed" only updates the local mock, so the threshold never visibly changes (SPEC §10 last step). The WebSocket works (not subject to CORS), so the live session is real while everything else is fake.
Repro: `scripts/dev.sh up`; `curl -si -H "Origin: http://localhost:5173" localhost:8000/residents | head -5` → no `access-control-allow-origin`. In the browser on :5173: `fetch('http://localhost:8000/alerts/alert-mrs-k')` → NetworkError while api.log shows 200.
Expected: API answers with CORS headers for the dashboard origin; dashboard shows API data; "Confirmed" lowers the shown threshold (the API already does: 4.09 → 3.88).
Interface: FastAPI `CORSMiddleware`; allowed origins from env `CORS_ORIGINS` (comma-separated, default `http://localhost:5173`); note in the PR that `.env.example` needs the var if outside area.
Acceptance:
- pytest: a GET with `Origin: http://localhost:5173` returns `access-control-allow-origin`; a preflight OPTIONS for `POST /alerts/{id}/feedback` succeeds.
- `scripts/ci.sh` passes.

### T120 — Bug: live task map overflows; the red/amber steps are hidden off to the right
- status: todo
- class: light
- priority: 0
- kind: bug
- deps: —
- area: web/src/live/TaskMap.tsx, web/src/live/*.css
- owner: —
- claimed: —
- pr: —
- source: tester

What: In a 1920×984 window the task map card is 406 px wide but its content is 1502 px (`overflow-x: auto`), so only "Fill the kettle", "Boil the kettle" and half of "Get a cup" are visible. The steps that turn red/amber in the demo scenario (`tea_skip_teabag_pour_twice`: teabag missed, pour repeated) are off-screen, so "errors flash" (SPEC §10 step 3) can't be seen without scrolling.
Repro: `scripts/dev.sh up`, open http://localhost:5173, wait for the live session to finish, look at the Task map card.
Expected: all 9 tea steps visible in the card at 1920 px without scrolling (wrap into rows or a vertical list), error colours visible.
Acceptance:
- vitest: steps render in a wrapping/vertical layout; existing TaskMap tests still pass.
- `scripts/ci.sh` passes.

### T121 — Bug: demo alert lists placeholder errors ("skipped the task at 0:00" ×4) and grows on every page load
- status: todo
- class: standard
- priority: 1
- kind: bug
- deps: —
- area: pipeline/src/routine_watch/alerts.py, pipeline/tests/test_alerts*.py
- owner: —
- claimed: —
- pr: —
- source: tester

What: `GET /alerts/alert-mrs-k` builds errors via `_task_errors` with `step_id=None` and fake times 0:00/0:10 in every session, so the summary reads "Flagged for review: 8 errors this session (skipped the task at 0:00, repeated the task at 0:10, skipped the task at 0:00, ...)", and says "this session" while counting across 3–4 sessions. Each dashboard load runs the live session (T081), which appends another `mrs-k-NN` session, so the alert keeps growing during a demo. Currently hidden only because the dashboard is on mock data (T119).
Repro: `scripts/dev.sh up`; load http://localhost:5173 twice; `curl -s localhost:8000/alerts/alert-mrs-k | python3 -m json.tool`.
Expected: alert errors name real steps with plausible timestamps, the summary counts correctly with no repeated clauses, and reloading the page doesn't keep adding sessions to the alert.
Acceptance:
- pytest: demo alert errors all have a non-null `step_id`; summary has no duplicate clauses; running the live session twice leaves at most one live session on the alert.
- `scripts/ci.sh` passes.

### T122 — Bug: live skeleton view stays "Waiting for camera" for the whole demo replay
- status: todo
- class: light
- priority: 1
- kind: bug
- deps: —
- area: tests/scenarios/tea_skip_teabag_pour_twice/ (add frames.jsonl)
- owner: —
- claimed: —
- pr: —
- source: tester

What: The dashboard's live session uses scenario `tea_skip_teabag_pour_twice`, which has only `steps.jsonl` (no `frames.jsonl`), so `/ws/live` sends 0 `frame` messages (probe: session_start 1, step 7, step_state 8, error 2, frame 0) and the skeleton panel next to the task map stays empty. SPEC §10 step 3 shows the skeleton next to the task map.
Repro: `scripts/dev.sh up`, open http://localhost:5173, watch the "Skeleton view" card for the whole session.
Expected: a synthetic skeleton/object-box `frames.jsonl` aligned with the step timestamps so the skeleton animates (no raw video). Note in the PR that `tests/scenarios/README.md` needs updating.
Acceptance:
- `scripts/e2e.sh` still passes; a check that `/ws/live?scenario=tea_skip_teabag_pour_twice` emits at least one `frame` message.
- `scripts/ci.sh` passes.

### T123 — Bug: smoke.sh always fails the evidence replay check (alert body is overwritten)
- status: todo
- class: light
- priority: 1
- kind: bug
- deps: —
- area: scripts/smoke.sh
- owner: —
- claimed: —
- pr: —
- source: tester

What: `scripts/smoke.sh` stores the alert JSON in `body` (~line 83), then the dashboard check (~line 92) reuses `body` for the HTML, so the replay block parses HTML and reports "no alert error to derive session/resident/time window from". The routes themselves work (`/sessions/mrs-k-20/replay?t_start=0&t_end=5` and `/residents/mrs-k/normal_replay` return frames).
Repro: `scripts/dev.sh up && scripts/smoke.sh` → `FAIL: GET /sessions/<id>/replay ...`, exit 1.
Expected: keep the alert body in its own variable; smoke passes against a fresh stack.
Acceptance:
- `scripts/smoke.sh` exits 0 against `scripts/dev.sh up`; `scripts/ci.sh` passes.
