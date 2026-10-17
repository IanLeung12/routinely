# Design

Routine Watch looks like a quiet, premium instrument panel: near-black, dense, numbers
first. The reference is **Fey** (links at the bottom) — we borrow its structure, density
and chart style, never its branding, logo or wording.

Tokens live in `web/src/index.css`; primitives in `web/src/ui/` (see its README for props).
Never hard-code a hex or a px in a component. If a token is missing, add it here first.

The unit overview on the tokens alone, before any screen was redesigned:
`design/overview-before.png` → `design/overview-after.png`.

The alert / evidence view, the first screen rebuilt on the system (same alert, same
data, half the scroll): `design/alert-before.png` → `design/alert-after.png`.

The live session — a dark media card beside the task map as a vertical step list with
a progress line — and the shift handoff as dense rows in one card:
`design/live-before.png` → `design/live-after.png`,
`design/handoff-before.png` → `design/handoff-after.png`.

## Principles

1. **Quiet by default.** A screen is grey text on near-black. Colour means something, so
   almost nothing is coloured.
2. **Numbers, then words.** The value is the headline; the sentence explains it. Numbers are
   right-aligned and `tabular-nums` so a column can be scanned without reading it.
3. **One container.** Everything sits in a `Card`: one step lighter than the page, a 1px
   hairline, 12px radius, generous padding, no shadow. Shadows are for things that float
   (the tour card), nothing else.
4. **Dense rows, not boxes.** Lists are hairline-separated `Row`s with the value on the
   right — not a grid of cards.
5. **Readable before pretty.** Fey's faintest greys fail WCAG. We keep the look and stop at
   4.5:1. `web/src/ui/tokens.test.ts` checks every text token against every surface it can
   land on, including inside a tinted pill.

## Tokens

| Group | Token | Value | Use |
|---|---|---|---|
| Surface | `--surface-page` | `#0b0b0d` | the page |
| | `--surface-card` | `#141416` | cards, panels |
| | `--surface-raised` | `#1c1c1f` | hovered rows, the chosen segment, the tour card |
| | `--hairline` / `--hairline-strong` | white 8% / 14% | card borders, row separators |
| | `--page-glow` | warm radial | one faint vignette behind the page; the only glow |
| Text | `--text` | `#f4f4f5` | headings, values, anything that carries the meaning |
| | `--text-secondary` | `#a8a8ad` | labels, supporting sentences |
| | `--text-muted` | `#8f8f99` | axis ticks, counters, timestamps |
| Status | `--status-normal` (+`-tint`) | green `#5fd98c` | within their usual range |
| | `--status-watch` (+`-tint`) | amber `#f5c451` | trending away from usual |
| | `--status-flagged` (+`-tint`) | red/pink `#ff7a85` | change flagged for review |
| | `--status-neutral` (+`-tint`) | grey `#a8a8ad` | a value with no sentiment; unclear readings |
| | `--accent` (+`-tint`) | purple `#b69cff` | focus ring, the comparison series |
| Chart | `--chart-line` | `#e9e9ec` | the primary series |
| | `--chart-comparison` | purple | the second series (their usual) |
| | `--chart-baseline` / `--chart-baseline-line` | white 7% / 24% | the usual-range band and its mean |
| | `--chart-forecast` + `--chart-forecast-dash` | grey, `3 4` | expected / projected series |
| | `--chart-grid` | white 6% | axes and gridlines |
| Shape | `--radius-xs` … `--radius-full` | 6 / 8 / 12 / 16px / pill | `xs` = pills, chips, buttons; `md` = cards |
| | `--space-1` … `--space-6` | 4 → 32px | the only gaps and paddings |
| Type | `--font-sans` | neutral system sans | everything |
| | `--text-xs` … `--text-2xl` | 12 → 32px | body 14 (`--text-md`), card title 16 (`--text-base`, 600) |
| | `.tabular-nums` | utility class | any number a reader compares down a column |

The old names (`--bg`, `--panel`, `--border`, `--muted`, `--alarm`, `--error-*`…) still exist
and point at the new ones, so screens keep working until their own redesign task. Don't add
new uses of them.

## Status mapping

| Status | Colour | Shown as | Words |
|---|---|---|---|
| normal | green | `StatusChip status="normal"` | "Within their usual range" |
| watch | amber | `StatusChip status="watch"` | "Worth watching: trending away from their usual routine" |
| flagged | red/pink | `StatusChip status="flagged"` | "Change flagged for review" |
| unclear | neutral grey | `Pill tone="neutral"` | say the capture was unclear; never score it |

Error categories keep their SPEC §7 mapping: red = omission/substitution,
amber = sequence/repeat, grey = unclear/low-confidence.

**Never colour alone.** Every chip and pill carries its own word or number; a delta also gets
an `↑`/`↓` arrow. A state a screen reader can hear (`aria-pressed`, `aria-label`) is part of
the design, not an extra.

## Charts

Full rules land with T402; these are the ones the tokens assume.

- One primary series in `--chart-line`, 1.5px, no fill, no markers except the latest point.
- A comparison series ("their usual") in `--chart-comparison`. Two series is the limit.
- The usual range is a `--chart-baseline` band behind the line, with a dashed mean. A reader
  should see "inside the band / outside the band" before reading any number.
- Anything **expected, projected or incomplete** is dotted (`--chart-forecast-dash`) — never a
  solid line, so a guess never looks like a measurement.
- Axes and gridlines are `--chart-grid`: present, never competing with the data.
- Points above the flag threshold turn `--status-flagged`, and the chart says so in text too.
- Label the latest value next to it in a `Pill`; don't make a reader hover to learn the number.

## Do / don't

- **Do** put the number on the right of a `Row` and the status chip after it.
- **Do** use `SegmentedControl` for "pick one view" (time range, quarterly/annual).
- **Do** give a card one `SectionHeader`: title left, `caption` for what the numbers are.
- **Don't** add a new colour. Four status colours, one accent, one chart comparison — that's all.
- **Don't** use gradients, glows, drop shadows or big rounded corners for emphasis. Emphasis is
  weight and position.
- **Don't** shrink text below `--text-xs` (12px) or lighten it past `--text-muted`.
- **Don't** write "diagnosis", "has <condition>" or "detected <condition>". The product flags a
  change for review and lists what it is **consistent with** (SPEC §7.5).

## References (Mobbin, Fey — look, don't copy)

Images stay on Mobbin; don't commit them.

- [Home / markets](https://mobbin.com/screens/8487cb92-3969-4f21-a847-26177466cf9a) — card density, the dock
- [Watchlist vs markets](https://mobbin.com/screens/7599e963-22f6-428c-b03e-f0438e2c3291) — dense rows, value pills
- [Financials charts](https://mobbin.com/screens/d70bd977-1898-4979-a799-bd2dcb94ab25) — dotted series, bar rows
- [Bar charts](https://mobbin.com/screens/f7d60fde-c660-4041-8c28-e381512275dd) — horizontal bars with the value on the right
- [Comparison](https://mobbin.com/screens/729ec564-7ed7-453d-a3f2-86f51b34c96a) — time-range segments, label pills on the line
- [Stock detail](https://mobbin.com/screens/4ac6daeb-a2ab-46ea-b8fe-7e328f2c493b) — page vignette, the stat strip
