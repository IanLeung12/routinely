# LESSONS

One line each, learned the hard way. Every worker sees these. Max 40; oldest drop off.

- Run scripts/ci.sh before pushing; ruff --fix (uv run --with ruff ruff check --fix .) clears most lint failures (e.g. UP017 datetime.UTC). (ian)
- Web tests: never let a test end while a fetch/effect is pending; stub fetch and await screen.findBy... or React updates after jsdom teardown ('window is not defined'). (ian)
- Use web/src/ui components and index.css tokens; never hard-code hex colours in components (dark theme). (ian)
- Paid APIs only through their client interface with a fake; tests and CI never set LIVE_API. (ian)
- Contracts are generated from pipeline/src/routine_watch/contracts.py; never hand-edit contracts/*.json or web/src/contracts.ts. (ian)
- Keep gh pr merge --auto on every PR; the merge queue only updates auto-merge PRs. (ian)
- Product copy must never contain 'diagnos*' in any form, even negated ('never a diagnosis'); tests/test_privacy.py rejects it. Say 'flagged for review'. (orchestrator)
- A new scenario's row in tests/scenarios/README.md conflicts with every other scenario PR (it's outside task areas): keep it to one line and merge origin/main before pushing. (ian-claude)
- UI must render task structure (steps, labels) from data sent by the pipeline, never from mock constants, even in live mode (reviewer)
- A PR that reproduces live.py's message stream can go stale between local CI and PR CI: GitHub tests your branch merged with the newest main, so re-fetch main and re-run ci.sh right before pushing when (ian-claude)
