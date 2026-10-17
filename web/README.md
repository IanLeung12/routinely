# web

Dashboard for Routine Watch. See `AGENTS.md` for the stack and conventions.

## Bundle size budget

`npm run check:bundle` guards the JS the dashboard loads before first paint —
the entry module script plus anything `vite build` marks `modulepreload` in
`dist/index.html`. It does **not** count lazy-loaded screens (handoff, pattern
library, tour — see `App.tsx`): those fetch on demand, so growing them doesn't
slow down the first screen a nurse sees.

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

It is currently 96,500 bytes gzipped (T446): the redesign shell, the person
view and the replays added on 2026-10-17 are always-on screens and measured
92,536 bytes together, over the 92,200 budget before them; T421's eager
resident-detail charts took that to 94,908, T442 raised the budget to 96,000
with `main` at 95,204, and the rest of that day's screens took `main` to
95,899. T446's replay-player markers, speed control and frame stepping add
345 bytes on top of that (the alert screen, and the player with it, is eager —
see `App.tsx`), measured 96,244. That leaves ~250 bytes of headroom: a new
always-on screen has to be `lazy()`, and the alert screen is the next thing
worth making lazy if this keeps biting.
