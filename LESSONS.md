# LESSONS

One line each, learned the hard way. Every worker sees these. Max 40; oldest drop off.

- Run scripts/ci.sh before pushing; ruff --fix (uv run --with ruff ruff check --fix .) clears most lint failures (e.g. UP017 datetime.UTC). (ian)
- Web tests: never let a test end while a fetch/effect is pending; stub fetch and await screen.findBy... or React updates after jsdom teardown ('window is not defined'). (ian)
- Use web/src/ui components and index.css tokens; never hard-code hex colours in components (dark theme). (ian)
