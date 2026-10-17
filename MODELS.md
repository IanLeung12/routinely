# Models

Every task has `class: light | standard | heavy`. The orchestrator picks the class, workers pick a model from this table.
`scripts/worker.sh` reads the `flags` lines below, so edit them here when better models come out.

## How the orchestrator picks a class
Score each task 0–2 on: context needed, ambiguity, modules touched, risk (core pipeline / shared contracts), testability (0 = has a clear test).
- 0–3 → `light`: one or two files, exact interface given, clear test. Cheap agents live here.
- 4–6 → `standard`: one module behind a fixed interface.
- 7+ or touches `contracts/` or cross-module integration → `heavy`.

## Flags
- claude/light: --disallowedTools Monitor ScheduleWakeup --model sonnet --effort low
- claude/standard: --disallowedTools Monitor ScheduleWakeup --model sonnet --effort high
- claude/heavy: --disallowedTools Monitor ScheduleWakeup --model opus --effort high
- codex/light: -c model_reasoning_effort=low
- codex/standard: -c model_reasoning_effort=medium
- codex/heavy: -c model_reasoning_effort=high

## Feedback loop
On every reconcile the orchestrator appends a line to `LOG.md` (tasks branch):
`T012 | light | claude-sonnet | merged first try | ~40k tok`
Outcomes: `merged first try`, `ci fixes: N`, `fix task Txx`, `reverted`, `released (stale)`.
If a kind of task fails twice at a class, new tasks of that kind go up one class. If heavy tasks keep landing trivially, similar ones go down.
