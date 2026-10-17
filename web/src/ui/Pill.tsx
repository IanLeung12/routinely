import type { ReactNode } from 'react'

/** `neutral` for a plain value, the other three for the status they are named
 * after (SPEC section 9): `positive` = within the usual range, `watch`, `negative`. */
export type PillTone = 'neutral' | 'positive' | 'watch' | 'negative'

const ARROWS = { up: '↑', down: '↓' } as const

/** Small tinted value pill: a number, a delta or a short label on a 15%-alpha
 * tint of its own colour (docs/DESIGN.md). Colour is never the only signal — the
 * pill always carries its own text, and `direction` adds an arrow on top. */
export function Pill({
  tone = 'neutral',
  direction,
  title,
  className,
  children,
}: {
  tone?: PillTone
  direction?: 'up' | 'down'
  title?: string
  className?: string
  children: ReactNode
}) {
  const classes = ['pill', `pill--${tone}`, className].filter(Boolean).join(' ')
  return (
    <span className={classes} title={title}>
      {direction ? (
        <span className="pill__arrow" aria-hidden="true">
          {ARROWS[direction]}
        </span>
      ) : null}
      {children}
    </span>
  )
}

export default Pill
