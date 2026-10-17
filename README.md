# htv-2026 — Routine Watch

Hack the Valley 11. Spec: `SPEC.md`. Agent rules: `AGENTS.md`.

## What it is

A privacy-preserving camera system that watches care-home residents do everyday
tasks and **flags a change for review** when how they do a task changes against
their own normal. Alerts show the evidence and the patterns it's **consistent
with**, ranked, with what to rule out — never a diagnosis.

## Run it

```bash
gh repo clone IanLeung12/htv-2026 && cd htv-2026
scripts/dev.sh up      # starts API (:8000) + dashboard (:5173) in the background
scripts/dev.sh status  # check what's running
scripts/dev.sh down    # stop both, free the ports
```

Open the dashboard at `http://localhost:5173`. Logs: `.dev/api.log`,
`.dev/web.log`. Override ports with `API_PORT` / `DASHBOARD_PORT`. `up` is
idempotent — running it twice is fine. No API keys needed.

## Test it

```bash
scripts/ci.sh    # whole-repo checks: ruff + pytest for pipeline/, lint + test + build for web/
scripts/e2e.sh   # replays every recorded scenario in tests/scenarios/ through the pipeline, offline
```

## Offline by default

`OFFLINE_MODE` defaults to `true` and `LIVE_API` defaults to `0`: the pipeline
uses mock data and fakes for every paid API client (Gemini, Anthropic,
Roboflow, Supabase, Langfuse). No real calls, no cost, no network needed to
run, test, or replay scenarios. Real calls only happen when a human explicitly
sets `LIVE_API=1`, and go through an on-disk cache.

## Privacy

Skeletons, bounding boxes, and timestamps only — raw video frames are never
stored, and there's no face identification.

## Where things are

```
pipeline/   Python 3.11 package (uv): capture → recogniser → task graph → errors → baseline, plus the FastAPI API
web/        Vite + React + TypeScript nurse dashboard
contracts/  schemas shared by pipeline/ and web/
scripts/    ci.sh (the one CI entrypoint), dev.sh, e2e.sh, tasks.py (the board), worker.sh (worker loop)
docs/       architecture diagrams, docs/CODEMAP.md (module map)
```

- Architecture and module layout: `docs/CODEMAP.md`.
- Writing or reading a recorded scenario: `tests/scenarios/README.md`.
- Full spec: `SPEC.md`.

## Run a worker (teammates)

Needs `git`, `gh` (logged in), `python3`, and `claude` or `codex`.

```bash
cp .env.example .env                                 # fill in keys you need
python3 scripts/tasks.py list                         # see the board
AGENT=max TOOL=claude CLASS=light scripts/worker.sh   # loop: claim → PR → auto-merge
```

- `CLASS` is the most expensive task class you'll take (`light` / `standard` / `heavy`).
- `TOOL=codex` for Codex. `ONCE=1` does one task and exits.
- Model flags per class come from `MODELS.md`; override with `FLAGS="--model haiku"`.

## How it works

- `TASKS.md` lives on the `tasks` branch. `scripts/tasks.py` claims tasks atomically.
- Workers open PRs that auto-merge when CI (`scripts/ci.sh`) passes.
- An orchestrator on Ian's VPS runs every ~10 min: writes new tasks, reviews merges, frees stuck claims, keeps `main` green.
- A tester on Ian's VPS runs when `main` changes: CI, scenario replays, a browser walkthrough. Report: `TESTREPORT.md` on the `tasks` branch.
