# Code map

Architecture notes that don't change often. For the current file list with each file's purpose and exports, run:

```
python3 scripts/codemap.py            # whole repo (generated live, never stale)
python3 scripts/codemap.py web/src    # one area
```

## Data flow (SPEC §6, §16)
```
camera ─► capture.py ─► capture records (JSONL, contracts.CaptureFrame)
                           │   (same stream for live, fallback, tests/scenarios)
                           ▼
          recogniser.py ─► StepEvent  ──(low confidence)──► verifier (Gemini, behind fake)
                           ▼
          tasks/graph.py (task graph data) + errors.py + hesitation.py ─► TaskError
                           ▼
          scoring.py ─► session score ─► change_detection.py (+ feedback.py thresholds) ─► flag
                           │                      drift.py ─► slow-drift trend (not an alert)
                           ▼
          patterns.py: extract_features ─► score_patterns (patterns_library.py, as data)
                           │                  ─► ranked PatternMatch ("consistent with …")
                           ▼
          alerts.py + checks.py + explain.py ─► Alert ─► api.py (REST + live.py WebSocket) ─► web/
```

## Where things live
- Contracts — source of truth is the pydantic models in `pipeline/src/routine_watch/contracts.py`; `contracts/*.schema.json` and `web/src/contracts.ts` are generated (`cd pipeline && uv run python -m routine_watch.contracts`). Never hand-edit generated files. Heavy tasks only.
- `pipeline/src/routine_watch/` — one module per stage. `replay.py` runs the whole pipeline offline; `demo.py` and `synth/` make synthetic residents, history and care records.
- `patterns.py` + `patterns_library.py` — from a flag to likely patterns (SPEC §7.5). `extract_features` reads one resident's own sessions and care records (error rates by type against their own baseline, onset in days or weeks from `change_detection` and `drift`, time of day, durations, care-record context); `score_patterns` ranks the library against those features and fills `Alert.patterns`. The library is data — signals and weights, time profile, checks, urgency, citation — so a new pattern is a new entry and no code change. Features the pipeline does not record yet (step gaps, movement speed, per-hand shares) stay `None`, and a pattern whose signals are mostly unmeasurable is not scored at all. `score_patterns(weights=..., answers=...)` multiplies each confidence by this resident's nurse-feedback weight for that pattern before the threshold and the sort, and says so in the evidence (SPEC Nice to have 8). Deterministic: same features and same past answers, same patterns; the LLM summariser never adds one.
- `pipeline/src/routine_watch/api.py` — FastAPI: `/health`, `/residents[/{id}]`, `/alerts[/{id}]`, `POST /alerts/{id}/feedback`, `GET /residents/{id}/drift` (daily score trend from `drift.drift`, backs the drift card), `GET /handoff` (`handoff.py`), WebSocket `/ws/live` (`live.py`). `api_cache.py` guards every paid API call (`LIVE_API`).
- `pipeline/src/routine_watch/evidence.py` — skeleton-only replay for an alert's "open evidence" view (never video, SPEC §8). Every alert replays `tests/scenarios/tea_no_kettle`, with a `tea_normal` ghost layer for comparison, until a real recording of the demo's actual bad session exists.
- `pipeline/src/routine_watch/feedback.py` — `FeedbackStore` nudges a resident's alert threshold on nurse feedback (false alarm raises it, confirmed lowers it) and records a per-alert `cause` plus the pattern the alert led with, so `cause_counts` tallies confirmed causes and `pattern_weights` / `pattern_answers` turn them into that resident's pattern weights (0.7-1.3, one answer worth 0.1) for `build_alerts(residents, feedback=store)`.
- `web/src/alert/FeedbackButtons.tsx` — once confirmed, offers the alert's patterns + "other" in the optional "What was it?" picker.
  The selection travels as `cause` in `POST /alerts/{id}/feedback`; `api.py` validates it against `KNOWN_CAUSES` (pattern ids + "other", otherwise 422).
  The API passes the accepted value to `FeedbackStore.record(..., cause=)`.
- `pipeline/src/routine_watch/live.py` — `session_messages` sends one push alert via `notify.get_notifier()` exactly when a session's end flips a resident from unflagged to flagged (`_resident_flagged`, read from `demo_residents()` before and after `_record`), not per session.
- `pipeline/src/routine_watch/notify.py` — `get_notifier` returns `FakeNotifier` unless `LIVE_API=1` and both `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` are set, so no test/CI/replay run ever sends a real push.
- `pipeline/src/routine_watch/alerts.py` — `_task_errors` invents a plausible step and timestamp per error from a session's error-type *counts* only (the demo history has no real per-instance step events), spreading them evenly over the session duration; `_distinct_clauses` then drops any error whose type/step/displayed-minute exactly repeats an earlier one so the explainer summary never shows a duplicate clause.
- `scripts/smoke.sh` — hits every API route (including `/alerts`, drift and feedback) and the dashboard against a running `scripts/dev.sh up` stack; first plays mrs-k's `tea_skip_teabag_pour_twice` live session so there's a flagged resident, then prints PASS/FAIL per check. Never sets `LIVE_API`, never POSTs feedback.
- The live view has two sources of the same messages: `live.py` replays a recorded scenario (the demo's fallback), `live_camera.py` reads a live capture stream as it arrives. Same message types, same order, so the dashboard cannot tell them apart.
- `handoff.py` — the shift handoff (`GET /handoff?hours=`): per resident, how many sessions in the window had a change flagged for review, how many alerts nobody has given a verdict on yet, and whether `drift.py` sees a slow rise, plus one summary from `explain.py`'s `Explainer`. Windows end at `demo.DEMO_NOW`, the clock the demo's history and its live session share.
- `session_log.py` — the sessions this process has watched finish, in memory. `live.py` records one when a session ends (against the demo resident unless told otherwise); `demo.py` merges a resident's recorded sessions into their history, which is how a live session spikes their sparkline and counts toward their flag (SPEC §10 step 4). Same shape as `store.py`, which replaces it once a database is wired up. It is global state: a test that plays a live session must `session_log.reset()`.
- `explain_claude.py` (`get_explainer()`) and `verifier.py` (`get_verifier()`) each default to an offline fake (`TemplateExplainer`, `FakeVerifier`); they only build the real client when `LIVE_API=1` and the matching key (`ANTHROPIC_API_KEY` / `GEMINI_API_KEY`) is set. Both route real calls through `api_cache.cached_call` and take their model from an env var (`ANTHROPIC_MODEL`, `GEMINI_MODEL`), falling back to the cheapest default otherwise.
- `web/src/` — one folder per screen (SPEC §9): `overview/`, `resident/`, `live/`, `alert/`, `evidence/`, `about/`, `handoff/`. Each has its own `api.ts` with an offline mock fallback, from `mock/` or from the screen's own folder (`live/mockLiveStream.ts`, `handoff/mockHandoff.ts`).
- `web/src/ui/` + `web/src/index.css` — the design system (tokens, Card, StatusChip, Button, states). Use these; don't restyle per screen.
- `tests/scenarios/` — end-to-end cases (`expected.yaml` + `frames.jsonl` or `steps.jsonl`), run by `scripts/e2e.sh`.
- `scripts/` — `ci.sh` (CI), `dev.sh` (local stack), `e2e.sh`, `codemap.py`, plus agent tooling `tasks.py`, `worker.sh`.
- `prompts/` — agent prompts; `prompts/areas/` guides attached per task area.

## Adding things
- New pipeline stage or rule → its own module, pure functions, a unit test, and a scenario if behaviour changes.
- New screen → new folder under `web/src/`, built from `web/src/ui/`, with mock data and loading/empty/error states.
- New shared shape → `contracts.py` first (heavy task), then regenerate schemas + TS.
