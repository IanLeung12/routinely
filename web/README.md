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
currently 92,200 bytes gzipped — about 10% over the ~84.1 KB measured right
after #237 split the handoff, pattern library and tour screens into lazy
chunks. Raise it only alongside a PR that explains the growth (a new eager
dependency, a new always-on screen); don't raise it just to make the check
pass.
