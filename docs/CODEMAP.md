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
          alerts.py + checks.py + explain.py ─► Alert ─► api.py (REST + live.py WebSocket) ─► web/
```

## Where things live
- Contracts — source of truth is the pydantic models in `pipeline/src/routine_watch/contracts.py`; `contracts/*.schema.json` and `web/src/contracts.ts` are generated (`cd pipeline && uv run python -m routine_watch.contracts`). Never hand-edit generated files. Heavy tasks only.
- `pipeline/src/routine_watch/` — one module per stage. `replay.py` runs the whole pipeline offline; `demo.py` and `synth/` make synthetic residents, history and care records.
- `pipeline/src/routine_watch/api.py` — FastAPI: `/health`, `/residents[/{id}]`, `/alerts[/{id}]`, `POST /alerts/{id}/feedback`, WebSocket `/ws/live` (`live.py`). `api_cache.py` guards every paid API call (`LIVE_API`).
- `web/src/` — one folder per screen (SPEC §9): `overview/`, `resident/`, `live/`, `alert/`, `evidence/`, `about/`. Each has its own `api.ts` with an offline mock fallback from `mock/`.
- `web/src/ui/` + `web/src/index.css` — the design system (tokens, Card, StatusChip, Button, states). Use these; don't restyle per screen.
- `tests/scenarios/` — end-to-end cases (`expected.yaml` + `frames.jsonl` or `steps.jsonl`), run by `scripts/e2e.sh`.
- `scripts/` — `ci.sh` (CI), `dev.sh` (local stack), `e2e.sh`, `codemap.py`, plus agent tooling `tasks.py`, `worker.sh`.
- `prompts/` — agent prompts; `prompts/areas/` guides attached per task area.

## Adding things
- New pipeline stage or rule → its own module, pure functions, a unit test, and a scenario if behaviour changes.
- New screen → new folder under `web/src/`, built from `web/src/ui/`, with mock data and loading/empty/error states.
- New shared shape → `contracts.py` first (heavy task), then regenerate schemas + TS.
