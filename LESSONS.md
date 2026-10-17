# LESSONS

One line each, learned the hard way. Every worker sees these. Max 40; oldest drop off.

- Run scripts/ci.sh before pushing; ruff --fix (uv run --with ruff ruff check --fix .) clears most lint failures (e.g. UP017 datetime.UTC). (ian)
- Web tests: never let a test end while a fetch/effect is pending; stub fetch and await screen.findBy... or React updates after jsdom teardown ('window is not defined'). (ian)
- Use web/src/ui components and index.css tokens; never hard-code hex colours in components (dark theme). (ian)
- Paid APIs only through their client interface with a fake; tests and CI never set LIVE_API. (ian)
- Contracts are generated from pipeline/src/routine_watch/contracts.py; never hand-edit contracts/*.json or web/src/contracts.ts. (ian)
- Keep gh pr merge --auto on every PR; the merge queue only updates auto-merge PRs. (ian)
- Product copy must never contain 'diagnos*' in any form, even negated ('never a diagnosis'); tests/test_privacy.py rejects it. Say 'flagged for review'. (orchestrator)
