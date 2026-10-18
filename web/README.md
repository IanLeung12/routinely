# web

Dashboard for Routinely. See `AGENTS.md` for the stack and conventions.

## Bundle size budget

`npm run check:bundle` guards the JS the dashboard loads before first paint —
the entry module script plus anything `vite build` marks `modulepreload` in
`dist/index.html`. It does **not** count lazy-loaded screens (handoff, pattern
library, tour, the alert screen, a resident's detail — see `App.tsx`): those
fetch on demand, so growing them doesn't slow down the first screen a nurse
sees.

```sh
npm run build
npm run check:bundle
```

It gzips each eager file the same way a browser would over the wire, prints
the size of each plus the total, and exits non-zero if the total is over
budget.

The budget lives in `BUDGET_BYTES` at the top of `scripts/check-bundle.mjs`,
originally 92,200 bytes gzipped — about 10% over the ~84.1 KB measured right
after #237 split the handoff, pattern library and tour screens into lazy
chunks. Raise it only alongside a PR that explains the growth (a new eager
dependency, a new always-on screen); don't raise it just to make the check
pass.

It is currently **89,000 bytes gzipped (T449)**, down from 99,000. The raises
before that all came from always-on screens: the redesign shell, the person
view and the replays added on 2026-10-17 measured 92,536 bytes together, over
the 92,200 budget before them; T421's eager resident-detail charts took that
to 94,908, T442 raised the budget to 96,000 with `main` at 95,204, the rest of
that day's screens took `main` to 95,899, T446's replay-player markers, speed
control and frame stepping added 345 bytes and T413's replays entry points
another 232 (budget 96,800), and T432's task-map node graph took `main` to
98,102 (budget 99,000).

T449 made the last two big eager screens `lazy()` instead. The alert screen
and a resident's detail are both drill-ins one tap off the overview, so the
shell no longer carries the replay player, the baseline chart or the heat
calendar at first paint. `main` measured **98,387 bytes before and 87,435
after** — about 11 KB less first-load JS — so the budget is 87,435 + ~1,500.
That is the same ~1.5 KB of headroom the raises kept buying: four PRs in a row
had to raise this line, and each one made `main` red for whoever landed next.
A new always-on screen still has to be `lazy()`, and a lazy screen has to own
its own imports — if the eager shell pulls one helper out of a feature module,
that whole module lands back in the first-load chunk.
