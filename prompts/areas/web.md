# Web guide (web/)
Who it's for: a busy charge nurse. Every screen must be understood in ~10 seconds (SPEC §9). Visual first; evidence one tap away.
- Stack: React + TS + Vite, plain CSS. No UI kits, no CSS frameworks, no new runtime deps without a reason in the PR.
- Use the design tokens in `web/src/index.css` (`--bg`, `--panel`, `--text`, `--muted`, status colours…). Never hard-code hex/px values in components; add a token if one is missing.
- Reuse shared components in `web/src/ui/` when they exist (chips, cards, buttons, section headers). New shared pieces go there.
- Class names: `block__element--modifier` (e.g. `task-map__step--error`). One CSS section per component.
- Status language and colours are fixed: normal / watch / flagged; errors red (omission, substitution), amber (sequence, repeat), grey (unclear). Always "possible change, review" wording, never "diagnosis".
- Accessible: semantic HTML, labels on controls, keyboard reachable, contrast ≥ 4.5:1, never colour alone (add icon or text).
- Every screen handles loading, empty and offline/error states, and works with mock data (`web/src/mock/`) and `OFFLINE_MODE`.
- Tests: Vitest + Testing Library for behaviour (what the nurse sees/clicks), not snapshots.
- Before the PR: `npm run lint && npm test && npm run build` in `web/`. If you changed a screen, run it (`scripts/dev.sh up`) and look at it; mention what you checked in the PR.
- Designing a new screen or page (or a major layout change)? If the `mobbin` MCP tools are available (`search_screens`, `search_flows`, `search_sections`), look at 2–3 real reference screens first and name the ones you drew from in the PR. Borrow structure and hierarchy, not branding. Skip this for small fixes.
