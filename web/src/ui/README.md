# Shared UI primitives

One visual language for every screen, built on the tokens in `../index.css`. The brief
behind them — principles, the token table, chart rules, status mapping, do/don't — is
`docs/DESIGN.md`. Don't hard-code hex/px values in components; add a token if one is missing.

- `Card` — the one container: a surface one step lighter than the page, a hairline border and
  generous padding. `wide` spans every column of a grid; `flush` drops the padding for content
  that draws its own edges (a chart, or a list of `Row`s).
  Props: `children`, `wide?`, `flush?`, `className?`.
- `StatusChip` — tinted normal/watch/flagged pill for a resident's status, always with its word.
  Props: `status: 'normal' | 'watch' | 'flagged'`.
- `Pill` — small tinted pill for a value or a delta: the text on a 15% tint of its own colour.
  `direction` adds an `↑`/`↓` so direction never rests on colour.
  Props: `children`, `tone?: 'neutral' | 'positive' | 'watch' | 'negative'`, `direction?: 'up' | 'down'`, `title?`, `className?`.
- `SegmentedControl` — "pick one view" (time range, quarterly/annual). The chosen option sits on
  a raised chip and reports `aria-pressed`; every option is tabbable.
  Props: `label: string` (names the group), `options: {value, label}[]`, `value`, `onChange`, `className?`.
- `Row` — one dense list line: who/what left, the number right, a chip after it. Rows draw their
  own hairline against the row above, so render them as siblings (bare, or one per `<li>`).
  `onSelect` makes the whole row a button; `selectLabel` says where it goes.
  Props: `title`, `subtitle?`, `value?`, `leading?`, `trailing?`, `onSelect?`, `selectLabel?`, `className?`.
- `Button` — `primary` (main action), `secondary` (default, everything else), `danger` (destructive or false-alarm).
  Props: all native `<button>` attributes plus `variant?: 'primary' | 'secondary' | 'danger'`.
- `SectionHeader` — a card's title, with an optional muted `caption` naming what the numbers are
  and an optional action on the right.
  Props: `title: string`, `caption?: string`, `action?: ReactNode`.
- `EmptyState` — message for a list or chart with nothing to show yet.
  Props: `message: string`.
- `ErrorState` — message for a failed fetch or offline mode, announced as an alert.
  Props: `message: string`.
- `Loading` — placeholder shown while a screen's data is still being fetched.
  Props: `label?: string` (defaults to `"Loading…"`).
- `DemoBanner` — synthetic-data notice with an optional dismiss callback.
  Props: `onDismiss?: () => void` (shows a Dismiss button only when supplied).
- `tokens.test.ts` — not a component: it parses `:root` out of `../index.css` and fails if any
  text token drops below 4.5:1 on a surface or inside a tinted pill. Add a colour there too.
- `errorTypes` — plain-language labels, tones (red/amber/grey) and phrasing for each
  `ErrorType`, used wherever an error needs to be shown without a chart. Exports
  `ERROR_TYPE_LABEL`, `ERROR_TYPE_TONE`, and `describeError(type, stepLabel)`.
