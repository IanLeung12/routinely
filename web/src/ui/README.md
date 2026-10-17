# Shared UI primitives

One visual language for every screen, built on the tokens in `../index.css`. Don't
hard-code hex/px values in components; add a token if one is missing.

- `Card` — panel surface for grouping content; pass `wide` inside a grid to span every column.
  Props: `children`, `wide?`, `className?`.
- `StatusChip` — colour-coded normal/watch/flagged chip for a resident's status.
  Props: `status: 'normal' | 'watch' | 'flagged'`.
- `Button` — `primary` (main action), `secondary` (default, everything else), `danger` (destructive or false-alarm).
  Props: all native `<button>` attributes plus `variant?: 'primary' | 'secondary' | 'danger'`.
- `SectionHeader` — a panel's uppercase label, with an optional action on the right.
  Props: `title: string`, `action?: ReactNode`.
- `EmptyState` — message for a list or chart with nothing to show yet.
  Props: `message: string`.
- `ErrorState` — message for a failed fetch or offline mode, announced as an alert.
  Props: `message: string`.
- `Loading` — placeholder shown while a screen's data is still being fetched.
  Props: `label?: string` (defaults to `"Loading…"`).
- `DemoBanner` — synthetic-data notice with an optional dismiss callback.
  Props: `onDismiss?: () => void` (shows a Dismiss button only when supplied).
- `errorTypes` — plain-language labels, tones (red/amber/grey) and phrasing for each
  `ErrorType`, used wherever an error needs to be shown without a chart. Exports
  `ERROR_TYPE_LABEL`, `ERROR_TYPE_TONE`, and `describeError(type, stepLabel)`.
