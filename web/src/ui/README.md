# Shared UI primitives

One visual language for every screen, built on the tokens in `../index.css`. Don't
hard-code hex/px values in components; add a token if one is missing.

- `Card` — panel surface for grouping content; pass `wide` inside a grid to span every column.
- `StatusChip` — colour-coded normal/watch/flagged chip for a resident's status.
- `Button` — `primary` (main action), `secondary` (default, everything else), `danger` (destructive or false-alarm).
- `SectionHeader` — a panel's uppercase label, with an optional action on the right.
- `EmptyState` — message for a list or chart with nothing to show yet.
- `ErrorState` — message for a failed fetch or offline mode, announced as an alert.
- `Loading` — placeholder shown while a screen's data is still being fetched.
- `DemoBanner` — synthetic-data notice with an optional dismiss callback.
