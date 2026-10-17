# Pipeline guide (pipeline/)
- Python 3.11, uv, ruff, pytest. Pure functions where possible; I/O at the edges.
- Shared types come from `routine_watch.contracts` (generated from `contracts/`). Don't redefine them; contract changes are heavy-only.
- Everything must run offline from capture records (JSONL). Live camera, fallback and tests use the same path.
- External services (Gemini, Claude, Roboflow, Supabase) only via their client interface with a fake as default; never in tests.
- Deterministic: seed every random generator; timestamps from the input, not the wall clock.
- If you change pipeline behaviour, add or update a scenario in `tests/scenarios/` and run `scripts/e2e.sh`.
- Error rules follow SPEC §7 exactly; low-confidence events are `unclear`, never errors.
