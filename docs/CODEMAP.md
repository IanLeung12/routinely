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
- `patterns.py` + `patterns_library.py` — from a flag to likely patterns (SPEC §7.5). `extract_features` reads one resident's own sessions and care records (error rates by type against their own baseline, onset in days or weeks from `change_detection` and `drift`, time of day, durations, care-record context); `score_patterns` ranks the library against those features and fills `Alert.patterns`. The library is data — signals and weights, time profile, checks, urgency, citation — so a new pattern is a new entry and no code change. Features the pipeline does not record yet (step gaps, movement speed, per-hand shares) stay `None`, and a pattern whose signals are mostly unmeasurable is not scored at all. Deterministic: same features, same patterns; the LLM summariser never adds one.
- `pipeline/src/routine_watch/api.py` — FastAPI: `/health`, `/residents[/{id}]`, `/alerts[/{id}]`, `POST /alerts/{id}/feedback`, WebSocket `/ws/live` (`live.py`). `api_cache.py` guards every paid API call (`LIVE_API`).
- The live view has two sources of the same messages: `live.py` replays a recorded scenario (the demo's fallback), `live_camera.py` reads a live capture stream as it arrives. Same message types, same order, so the dashboard cannot tell them apart.
- `session_log.py` — the sessions this process has watched finish, in memory. `live.py` records one when a session ends (against the demo resident unless told otherwise); `demo.py` merges a resident's recorded sessions into their history, which is how a live session spikes their sparkline and counts toward their flag (SPEC §10 step 4). Same shape as `store.py`, which replaces it once a database is wired up. It is global state: a test that plays a live session must `session_log.reset()`.
- `explain_claude.py` (`get_explainer()`) and `verifier.py` (`get_verifier()`) each default to an offline fake (`TemplateExplainer`, `FakeVerifier`); they only build the real client when `LIVE_API=1` and the matching key (`ANTHROPIC_API_KEY` / `GEMINI_API_KEY`) is set. Both route real calls through `api_cache.cached_call` and take their model from an env var (`ANTHROPIC_MODEL`, `GEMINI_MODEL`), falling back to the cheapest default otherwise.
- `web/src/` — one folder per screen (SPEC §9): `overview/`, `resident/`, `live/`, `alert/`, `evidence/`, `about/`. Each has its own `api.ts` with an offline mock fallback from `mock/`.
- `web/src/ui/` + `web/src/index.css` — the design system (tokens, Card, StatusChip, Button, states). Use these; don't restyle per screen.
- `tests/scenarios/` — end-to-end cases (`expected.yaml` + `frames.jsonl` or `steps.jsonl`), run by `scripts/e2e.sh`.
- `scripts/` — `ci.sh` (CI), `dev.sh` (local stack), `e2e.sh`, `codemap.py`, plus agent tooling `tasks.py`, `worker.sh`.
- `prompts/` — agent prompts; `prompts/areas/` guides attached per task area.

## Adding things
- New pipeline stage or rule → its own module, pure functions, a unit test, and a scenario if behaviour changes.
- New screen → new folder under `web/src/`, built from `web/src/ui/`, with mock data and loading/empty/error states.
- New shared shape → `contracts.py` first (heavy task), then regenerate schemas + TS.
