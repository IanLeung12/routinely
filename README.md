# htv-2026 — Routine Watch

Hack the Valley 11. Spec: `SPEC.md`. Agent rules: `AGENTS.md`.

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

## How it works
- `TASKS.md` lives on the `tasks` branch. `scripts/tasks.py` claims tasks atomically (push races lose cleanly).
- Workers open PRs that auto-merge when CI (`scripts/ci.sh`) passes.
- An orchestrator on Ian's VPS runs every ~20 min: writes new tasks, reviews merges, frees stuck claims, keeps `main` green.
