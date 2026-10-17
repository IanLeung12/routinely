# htv-2026 — Routine Watch

Hack the Valley 11. Spec: `SPEC.md`. Agent rules: `AGENTS.md`.

## Layout
```
pipeline/   Python 3.11 package (uv): capture → recogniser → task graph → errors → baseline, plus the FastAPI API
web/        Vite + React + TypeScript nurse dashboard
contracts/  schemas shared by pipeline/ and web/ (empty for now; `heavy` tasks only)
scripts/    ci.sh (the one CI entrypoint), tasks.py (the board), worker.sh (worker loop)
docs/       architecture and process-flow diagrams
```
- `pipeline/` — one module per stage of SPEC §6, each a placeholder a later task fills in. `cd pipeline && uv sync --all-extras`, then `uv run pytest` or `uv run uvicorn routine_watch.api:app --reload`.
- `web/` — `cd web && npm install && npm run dev`. Reads the API from `VITE_API_URL` (`src/config.ts`); screens come from SPEC §9.
- `contracts/` — one definition per shared shape, so the pipeline and the dashboard can't drift. See `contracts/README.md`.
- `.env.example` — every env var the project uses. Copy to `.env`; never commit `.env`.

Whole-repo checks: `scripts/ci.sh` (ruff + pytest for `pipeline/`, lint + test + build for `web/`).

## Run the stack
One command, no API keys needed (`OFFLINE_MODE=true`, mock data):

```bash
scripts/dev.sh up      # starts API (:8000) + dashboard (:5173) in the background, prints URLs
scripts/dev.sh status  # check what's running
scripts/dev.sh down    # stop both, free the ports
```

Logs: `.dev/api.log`, `.dev/web.log`. Override ports with `API_PORT` / `DASHBOARD_PORT`. `up` is idempotent — running it twice is fine.

## Run a worker (teammates)
Needs `git`, `gh` (logged in), `python3`, and `claude` or `codex`.

```bash
gh repo clone IanLeung12/htv-2026 && cd htv-2026
cp .env.example .env                               # fill in keys you need
python3 scripts/tasks.py list                      # see the board
AGENT=max TOOL=claude CLASS=light scripts/worker.sh  # loop: claim → PR → auto-merge
```

- `CLASS` is the most expensive task class you'll take (`light` / `standard` / `heavy`). Low on credits? Use `light`.
- `TOOL=codex` for Codex. `ONCE=1` does one task and exits.
- Model flags per class come from `MODELS.md`; override with `FLAGS="--model haiku"`.
- Two workers on one machine? Give each its own clone.
- On a usage-capped plan (e.g. ChatGPT Plus + Codex): `AGENT=you TOOL=codex CLASS=light BACKOFF=1800 scripts/worker.sh`. If a run hits the limit, the task is released and the worker waits instead of hogging it.

## How it works
- `TASKS.md` lives on the `tasks` branch. `scripts/tasks.py` claims tasks atomically (push races lose cleanly).
- Workers open PRs that auto-merge when CI (`scripts/ci.sh`) passes.
- An orchestrator on Ian's VPS runs every ~10 min: writes new tasks, reviews merges, frees stuck claims, keeps `main` green.
- A tester on Ian's VPS runs when `main` changes: CI, scenario replays (`scripts/e2e.sh`), a browser walkthrough of the demo, and files `Bug:` tasks. Report: `TESTREPORT.md` on the `tasks` branch.
