# AGENTS.md

Hack the Valley 11 project: **Routine Watch** (see `SPEC.md`, read only the sections your task needs).
Several Claude Code and Codex agents work here at once. Nobody asks for permission; follow these rules instead.

## Roles
- **Orchestrator** (one, runs on Ian's VPS): writes tasks, reviews merged work, releases stuck claims, keeps `main` green. Never writes feature code. Prompt: `prompts/orchestrator.md`.
- **Tester** (one, runs on Ian's VPS when `main` changes): runs CI, replays recorded scenarios end to end, walks the dashboard in a real browser, files `Bug:` tasks. Never fixes code. Prompt: `prompts/tester.md`.
- **Reviewer** (one, on Ian's VPS, ~30 min when `main` moves): reviews the diff since its last run plus one rotating area, files `Review:` tasks. Never changes code. Prompt: `prompts/reviewer.md`.
- **Retro** (one, on Ian's VPS, ~3 h): reads `METRICS.md` (from `scripts/metrics.py`) and improves the loop itself (prompts, routing, task template, lessons) as logged experiments. Prompt: `prompts/retro.md`.
- **Workers** (Claude Code / Codex, any teammate): claim one task, ship one PR, repeat. Prompt: `prompts/worker.md`. Run via `scripts/worker.sh`.

## The board
- `TASKS.md` lives on the **`tasks` branch**, not `main`. Never edit it on `main`.
- Always use `scripts/tasks.py` to read or change it (it handles the `.tasks/` worktree and push races).
- Status flow: `todo → claimed → in-review → done` (or `blocked`). Only claim tasks at or below your class (`MODELS.md`).
- A claim is yours only if `tasks.py` says so. If it prints `LOST`, pick another task.

## Finding your way
- Your prompt includes a code map of your task's area. For anything else run `python3 scripts/codemap.py <path>` instead of exploring; architecture notes in `docs/CODEMAP.md`. Open only the files you need.
- If you add, move or remove a module or screen, update `docs/CODEMAP.md` in the same PR (only its notes; the file list is generated).

## Shipping a task
1. `git fetch && git switch -c task/T012-short-name origin/main`
2. Touch only the files/area the task lists. Need something outside it? Note it in the PR; don't widen scope.
3. Add or update tests. Run `scripts/ci.sh --changed` locally (fast, only what you touched); it must pass. PR CI runs the full `scripts/ci.sh` in parallel jobs.
4. PR title `T012: <title>`. Body: what changed (2–5 lines), how it was tested, `model:` and approximate tokens.
5. `gh pr merge --auto --squash --delete-branch`, then `tasks.py set T012 status=in-review pr=#N`.
6. If CI fails, fix it on the same branch. After 2 failed fix attempts: `tasks.py set T012 status=blocked note="..."` and stop.

## Code rules
- Shared types/schemas live in `contracts/`. Only `heavy` tasks may change them, and must update every consumer in the same PR.
- No secrets in git. Use `.env` (gitignored) and document new vars in `.env.example`.
- Never store raw video frames (privacy rule, SPEC §8). Skeletons, boxes, timestamps only.
- Paid APIs (Gemini, Anthropic, Roboflow, Supabase) are budgeted, not unlimited. Every external client sits behind an interface with a fake used by default; tests, CI, e2e and the tester never make real calls. Real calls only when `LIVE_API=1` is set, through an on-disk response cache (`.cache/api/`, keyed by request hash) and with the cheapest model that works (dev: Gemini Flash-Lite/Flash, Claude Haiku). Send the fewest/smallest images possible.
- Roboflow credits are scarce (50/month). Never call Roboflow's hosted inference API in code, tests or CI; run the detector locally from downloaded weights. Never start a Roboflow training run; humans do that.
- Users: a **person** (watches themselves) and their **supervisors** (family, carer or nurse); see SPEC §3, §17. Don't write nurse-only UI.
- Wording: the product **flags a change for review** and lists patterns it is **"consistent with"** plus what to rule out (SPEC §7.5). Never "diagnoses", never "has <condition>".
- Keep PRs small. Prefer boring, readable code over clever code.
- `main` is protected: PRs only, CI must pass. `scripts/mergeq.py` (host cron) sends PRs with merge conflicts back to the board so the next worker can fix them. Never force-push.
- Lessons: your prompt includes `LESSONS.md` from the board. Add one with `tasks.py lesson` when a gotcha costs you a retry.
- Tasks whose `area` overlaps work in flight aren't handed out until that work merges, so keep to your task's files.
