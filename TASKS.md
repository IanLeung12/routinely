# TASKS

Board for htv-2026. Edit only through `scripts/tasks.py` (workers) or `.tasks/` + `tasks.py commit` (orchestrator).
Format and rules: `prompts/orchestrator.md`, `MODELS.md`.

- last-reviewed: 02e89fa

## Tasks

### T050 — Drift endpoint for a resident
- status: todo
- class: standard
- priority: 2
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/api.py (add the route only), pipeline/src/routine_watch/demo.py (expose daily scores only if needed), pipeline/tests/test_api_drift.py
- owner: —
- claimed: —
- pr: —

What: Back the drift card (T049) with data: `GET /residents/{resident_id}/drift` runs `routine_watch.drift.drift` over that resident's demo sessions, one point per day (mean score per date). The demo "slow drift" resident must come out `trending: true`, Mrs. K and the stable resident `false`.
Interface: response `{"resident_id": str, "slope_per_day": float, "days": int, "trending": bool}`; 404 for unknown resident, same style as `get_resident`.
Acceptance:
- pytest via FastAPI TestClient: 200 shape, 404, drift resident trending, stable resident not trending.
- `scripts/ci.sh` passes.

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

### T075 — Review: error-type labels and colours defined three times in the web app
- status: in-review
- class: light
- priority: 2
- kind: improvement
- deps: T064
- area: web/src/ui/errorTypes.ts (new), web/src/ui/errorTypes.test.ts (new), web/src/live/LiveSession.tsx, web/src/alert/ErrorList.tsx, web/src/resident/format.ts
- source: reviewer
- owner: ian-claude-standard
- claimed: 2026-10-17T06:59Z
- pr: #89

What: `LiveSession.tsx` (`ERROR_LABELS`, `ERROR_COLOR`), `alert/ErrorList.tsx` (phrase + colour maps) and `resident/format.ts` (plain names) each map `ErrorType` separately, so the same error can read or colour differently across screens.
Interface: `web/src/ui/errorTypes.ts` exports `ERROR_TYPE_LABEL: Record<ErrorType, string>`, `ERROR_TYPE_TONE: Record<ErrorType, 'red' | 'amber' | 'grey'>` (SPEC §9 colours) and `describeError(type, stepLabel): string`. The three files import from it; delete their local maps. Visible text may only change where screens disagreed today; note any such change in the PR.
Acceptance:
- Unit test covers every `ErrorType` in all three exports.
- `scripts/ci.sh` passes.

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

### T081 — Live session result counts toward the resident's flag (demo step 4)
- status: done
- class: heavy
- priority: 1
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/live.py, pipeline/src/routine_watch/session_log.py, pipeline/src/routine_watch/demo.py, pipeline/tests/test_live_flag.py, docs/CODEMAP.md (notes only)
- owner: ian-claude
- claimed: 2026-10-17T06:46Z
- pr: #87

What: SPEC §10 step 4: when a live (or fallback pre-recorded) session for Mrs. K finishes with qualifying errors, it must become one of her sessions, so her sparkline spikes and, being the second qualifying session in the window, the "possible delirium" flag and alert appear on the next `/residents` and `/alerts` fetch. Today `live.py` scores the session but nothing records it.
Interface: new `session_log.py` (in-memory, process-local) `record(resident_id, session: Session) -> None`, `sessions_for(resident_id) -> list[Session]`, `reset()`; `live.py` records the finished session; `demo.py` merges logged sessions into the resident's history before scoring/flagging. Keep it swappable for T038's store later (same shape, no DB here).
Acceptance:
- pytest: playing `tea_skip_teabag_pour_twice` for Mrs. K via `session_messages` then calling `/residents` and `/alerts` (TestClient) shows her flagged with the new session listed; playing `tea_normal` does not flag; `reset()` restores the seeded demo.
- `scripts/e2e.sh` and `scripts/ci.sh` pass.

### T083 — Docs: CODEMAP notes for the Claude explainer and Gemini verifier
- status: done
- class: light
- priority: 3
- kind: docs
- deps: —
- area: docs/CODEMAP.md (notes only)
- owner: ian-claude-standard-2
- claimed: 2026-10-17T06:23Z
- pr: #77

What: `docs/CODEMAP.md` notes don't mention `explain_claude.py` (T032) or how `get_explainer()` / `get_verifier()` choose the fake vs the real client. Add 2–4 lines: both default to offline fakes, real calls only with `LIVE_API=1` + key, through `api_cache.py`, models from `ANTHROPIC_MODEL` / `GEMINI_MODEL`. Read only `docs/CODEMAP.md`, the top docstrings of `explain_claude.py`, `verifier.py`, `api_cache.py`.
Acceptance:
- Notes only (generated file list untouched); `scripts/ci.sh` passes.

### T084 — Pattern library + scorer + Alert.patterns contract (SPEC §7.5)
- status: todo
- class: heavy
- priority: 1
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/contracts.py, pipeline/src/routine_watch/patterns.py, pipeline/src/routine_watch/patterns_library.py, pipeline/src/routine_watch/alerts.py, pipeline/tests/test_patterns.py, contracts/, web/src/contracts.ts
- owner: —
- claimed: —
- pr: —

What: The pivot in SPEC §7.5 (decision D): every flag ranks the patterns the change is consistent with. Deterministic rules over features, library as data, LLM never adds patterns.
Interface:
- Contract: `PatternMatch {pattern_id, name, confidence (0–1), urgency: routine|next_round|same_shift|urgent, evidence: [str], checks: [SuggestedCheck or str]}`; `Alert.patterns: list[PatternMatch]` (empty = "no clear pattern"). Regenerate schemas + `web/src/contracts.ts`; keep existing fields working.
- `patterns_library.py`: the six patterns from §7.5 as data (signals + weights, time profile, checks, urgency, source citation). Only `sudden_change` and `slow_drift` need to score well now; others present with conservative weights.
- `patterns.py`: `extract_features(sessions, baseline, care_records) -> Features` and `score_patterns(features, library) -> list[PatternMatch]` (top 3 above threshold, sorted).
- `alerts.py`: fill `Alert.patterns` from the scorer.
Acceptance:
- Unit tests: a sudden-spike history ranks `sudden_change` first; a gradual rise ranks `slow_drift` first; flat noise → no pattern; a new sedating med raises the medication pattern.
- Wording in evidence/checks uses "consistent with" / "rule out", never "diagnosis".
- `scripts/ci.sh` passes; update `docs/CODEMAP.md` data-flow notes.

### T085 — PatternList component for ranked "possible patterns" (not wired yet)
- status: done
- class: light
- priority: 1
- kind: feature
- deps: —
- area: web/src/alert/PatternList.tsx, web/src/alert/PatternList.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T06:15Z
- pr: #73

What: SPEC §9 screen 4 now shows "Possible patterns", ranked. Build the presentational component now so T088 only has to wire it once T084 lands the contract.
Interface: `export interface PatternView { pattern_id: string; name: string; confidence: number /*0-1*/; urgency: 'routine'|'next_round'|'same_shift'|'urgent'; evidence: string[]; checks: string[] }` and `export function PatternList({ patterns }: { patterns: PatternView[] })`. Each item: name, "consistent with" phrasing (e.g. heading "Consistent with: Sudden change (delirium)"), confidence as a percentage, urgency label, evidence bullets, "Consider ruling out:" checks. `urgent` items get a distinct class (`pattern--urgent`) and an "Urgent" label (not colour alone). Empty list renders "Change detected, no clear pattern". Read for style only: `web/src/alert/SuggestedChecks.tsx`, `web/src/ui/Card.tsx`. Do not import from contracts.ts and do not edit any other file.
Acceptance:
- Vitest: renders items in the given order with name, % confidence, evidence and checks; urgent item has the urgent class and visible "Urgent" text; empty list shows "no clear pattern"; no text contains "diagnos".
- `cd web && npm test` and `scripts/ci.sh` pass.

### T086 — Synthetic history: evening-only worsening resident scenario
- status: todo
- class: light
- priority: 2
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/synth/history.py, pipeline/tests/test_history.py
- owner: —
- claimed: —
- pr: —

What: SPEC §8 needs a resident whose errors are concentrated in late-day sessions (sundowning pattern, §7.5). Add an `"evening"` scenario to the history generator.
Interface: `generate_history(resident_id, days, seed, scenario="evening")`; add `"evening"` to `SCENARIOS`. Sessions whose local hour (from `ts`) is ≥ 16 in the last ~7 days get 1–3 errors (sequence/omission/hesitation); morning sessions stay like `"normal"`. Read only `pipeline/src/routine_watch/synth/history.py` and `pipeline/tests/test_history.py`; don't touch `demo.py`.
Acceptance:
- pytest: deterministic for a fixed seed; mean errors of evening sessions in the last 7 days ≥ 3× morning sessions; morning sessions look like `normal`; at least one session before and after 16:00 exists each day (adjust session times only for this scenario if needed).
- `scripts/ci.sh` passes.

### T087 — Synthetic history: motor slowing after a sedating medication
- status: done
- class: standard
- priority: 2
- kind: feature
- deps: —
- area: pipeline/src/routine_watch/synth/history.py, pipeline/src/routine_watch/synth/care_records.py, pipeline/tests/test_history.py, pipeline/tests/test_care_records.py
- owner: ian-claude-standard
- claimed: 2026-10-17T06:12Z
- pr: #72

What: SPEC §7.5/§8 motor slowing pattern: after a new sedating med (e.g. diphenhydramine) ~5 days before the end, step durations and gaps rise while sequencing errors stay rare. Sessions need a duration signal for T084's feature extractor.
Interface: new `"motor"` scenario in `generate_history` and `generate_care_records`. Add a per-session `duration_s` (total task seconds) to every generated session (all scenarios; normal ≈ 150–200 s), and for `"motor"` raise it ~40–60 % after the med start with mostly `hesitation` errors. Care records: a `medication` entry for the sedating med on the start day. Keep existing keys unchanged so `demo.py` keeps working.
Acceptance:
- pytest: `motor` durations after the med start average ≥ 1.4× before; sequence/omission errors stay ≤ normal rate; care record present on the right day; all existing history/care-record tests still pass.
- `scripts/ci.sh` passes.

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

### T090 — "What was it?" picker in the feedback buttons (UI only)
- status: done
- class: light
- priority: 2
- kind: feature
- deps: —
- area: web/src/alert/FeedbackButtons.tsx, web/src/alert/FeedbackButtons.test.tsx
- owner: ian-claude-standard-2
- claimed: 2026-10-17T06:19Z
- pr: #76

What: SPEC §5 MVP 8: after "Confirmed", the nurse can optionally say what it turned out to be. Add the picker to the component only; posting it is a later task.
Interface: new optional props `causeOptions?: {id: string; label: string}[]`, `cause?: string | null`, `onCauseChange?: (id: string) => void`. When `value === 'confirmed'` and `causeOptions` is given, render a labelled group "What was it? (optional)" with one toggle button per option plus "Other" (`id: 'other'`), `aria-pressed` on the selected one. Without these props the component behaves exactly as today. Read only those two files.
Acceptance:
- Vitest: picker hidden before confirming and when `causeOptions` is absent; shown after confirmed; clicking an option calls `onCauseChange` with its id; existing tests unchanged and passing.
- `cd web && npm test` and `scripts/ci.sh` pass.

### T091 — Tests: demo residents land on their intended status
- status: done
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_demo.py
- owner: ian-claude
- claimed: 2026-10-17T06:22Z
- pr: #78

What: `pipeline/src/routine_watch/demo.py` pins seeds so each resident gets its intended status, but no test guards it; upcoming pattern work (T084, T089) will change this file.
Interface: new `pipeline/tests/test_demo.py` only. Read `pipeline/src/routine_watch/demo.py`. Don't edit source.
Acceptance:
- pytest: `demo_residents()` is deterministic (two calls equal); `mrs-k` status is `flagged`; `mrs-ahmed` and `mr-silva` are `normal`; `mr-chen` is not `normal`; every resident has 14 days of score points sorted by `ts`; no resident has an empty name or room.
- `scripts/ci.sh` passes.

### T092 — PatternList styles: urgent patterns visually distinct
- status: done
- class: light
- priority: 1
- kind: improvement
- deps: —
- area: web/src/alert/PatternList.tsx, web/src/alert/PatternList.css (new), web/src/alert/PatternList.test.tsx
- owner: ian-claude
- claimed: 2026-10-17T06:27Z
- pr: #81

What: `PatternList` (merged in #73) uses class names (`pattern`, `pattern--urgent`, `pattern__urgency--*`, `pattern__confidence`) that no stylesheet defines, so urgent patterns look like every other one (SPEC §9 screen 4: "Urgent patterns are visually distinct"). Read only the files in `area`, `web/src/index.css` (tokens) and `web/src/alert/alert.css` (style reference; do not edit it).
Interface: new `PatternList.css` imported from `PatternList.tsx`. CSS vars from `index.css` only, no hex colours (dark theme). Urgent: a thick left border and the red error token; `same_shift`: amber token; others: muted. Confidence as a small pill. Also add `aria-label="Possible patterns"` on the outer `<ul>`.
Acceptance:
- Vitest: the urgent item has class `pattern--urgent` and the non-urgent does not; the list has accessible name "Possible patterns"; existing tests still pass.
- No hex colours in `PatternList.css`.
- `cd web && npm run lint && npm test && npm run build` passes.

### T093 — Heat calendar: weekday headers and a legend
- status: done
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/resident/HeatCalendar.tsx, web/src/resident/HeatCalendar.test.tsx
- owner: ian-claude-standard
- claimed: 2026-10-17T06:37Z
- pr: #83

What: The heat calendar grid has no weekday labels and no key, so a nurse can't tell which column is Monday or what a darker cell means. Read only the two files in `area` and `web/src/index.css` (tokens).
Interface: keep `export default function HeatCalendar({ days })`. Add a header row of seven `role="columnheader"` cells (`Mon` … `Sun`) above the day cells (shift day rows down by one), and below the grid a one-line legend `<p>`: "Darker = more errors that day. Grey = no session." CSS vars only.
Acceptance:
- Vitest: seven column headers in Monday-first order; legend text present; a day still lands in the right weekday column; empty `days` still renders nothing.
- `cd web && npm run lint && npm test && npm run build` passes.

### T094 — Tests: change-detection edge cases
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_change_detection_edges.py (new)
- owner: —
- claimed: —
- pr: —

What: `pipeline/tests/test_change_detection.py` covers the happy paths of the flag rule (SPEC §7: two or more sessions above the baseline threshold within 48 h; one bad session never alerts) but not the boundaries. Read only `pipeline/src/routine_watch/change_detection.py` and the existing test file. Don't edit source; if a boundary case reveals a bug, mark that test `xfail(strict=True, reason=...)` and say so in the PR.
Interface: new test file only.
Acceptance:
- pytest cases: two bad sessions exactly 48 h apart (assert what the code defines and name the test after it); unsorted input gives the same result as sorted; fewer than three history scores gives no baseline/flag; a score exactly equal to the threshold never counts; three bad sessions in 48 h flag.
- `scripts/ci.sh` passes.

### T095 — Tests: hesitation edge cases
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: pipeline/tests/test_hesitation_edges.py (new)
- owner: —
- claimed: —
- pr: —

What: Hesitation (a step or gap much longer than this resident's own average) has five tests; boundaries are untested. Read only `pipeline/src/routine_watch/hesitation.py` and `pipeline/tests/test_hesitation.py`. Don't edit source; if a case reveals a bug, mark it `xfail(strict=True, reason=...)` and say so in the PR.
Interface: new test file only.
Acceptance:
- pytest cases: a step id with no history is never flagged; empty input returns an empty list; a duration just above vs just below the threshold; zero-length durations; history for one step doesn't affect another step.
- `scripts/ci.sh` passes.

### T096 — Scenario: stirring three times is perseveration
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/tea_stir_three_times/
- owner: —
- claimed: —
- pr: —

What: Repeating a step is the signal behind the executive pattern (SPEC §7.5, perseveration with intact order). Add a steps-level scenario: a complete, correctly ordered tea session where `stir` happens three times in a row. Read only `tests/scenarios/README.md` and `tests/scenarios/tea_substitution/` (copy its shape). Do not edit `tests/scenarios/README.md` (a later docs task adds the rows).
Interface: `tests/scenarios/tea_stir_three_times/{expected.yaml,steps.jsonl}` with a comment saying what it's for; no history, so `flag: false`.
Acceptance:
- `scripts/e2e.sh tests/scenarios/tea_stir_three_times` passes and asserts the perseveration error(s) on `stir` and no omission/sequence errors.
- `scripts/ci.sh` passes.

### T097 — Scenario: two bad sessions 60 h apart do not flag
- status: todo
- class: light
- priority: 2
- kind: test
- deps: —
- area: tests/scenarios/tea_bad_sessions_far_apart/
- owner: —
- claimed: —
- pr: —

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
- status: todo
- class: light
- priority: 2
- kind: improvement
- deps: —
- area: web/src/overview/UnitOverview.tsx, web/src/overview/UnitOverview.test.tsx
- owner: —
- claimed: —
- pr: —

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
- status: claimed
- class: standard
- priority: 0
- kind: bug
- source: reviewer
- deps: —
- area: pipeline/src/routine_watch/evidence.py, pipeline/tests/test_evidence.py, tests/scenarios/tea_normal/frames.jsonl
- owner: ian-claude-standard-2
- claimed: 2026-10-17T07:02Z
- pr: —

What: `evidence.py` sets both `_ALERT_SCENARIO` and `_NORMAL_SCENARIO` to `tea_no_kettle`, so `GET /residents/{id}/normal_replay` returns exactly the frames of `GET /sessions/{id}/replay` (only `session_id` differs). On the alert screen the ghost overlay sits perfectly on top of today's skeleton, so demo step 5 ("compare against her normal routine") shows no difference.
Fix: add a frame-level `tests/scenarios/tea_normal/frames.jsonl` (same capture format and timing as `tea_no_kettle/frames.jsonl`, but with the fill-kettle and boil contacts, so the recogniser reads all tea steps; check `tea_normal/expected.yaml` still passes via `scripts/e2e.sh`) and point `_NORMAL_SCENARIO` at `tea_normal`.
Acceptance:
- New test in `test_evidence.py`: for the same window, `normal_replay_frames` and `replay_frames` return different landmark/object data.
- `scripts/ci.sh` passes (including e2e on `tea_normal`).

### T108 — Review: smoke.sh skips the evidence replay routes and isn't syntax-checked in CI
- status: in-review
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
