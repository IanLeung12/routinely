import type { ReactNode } from 'react'

/** The one container: a surface one step lighter than the page, a hairline
 * border and generous padding (docs/DESIGN.md). Pass `wide` inside a grid to
 * span every column (see `.resident-panels` in resident/ResidentDetail.tsx), and
 * `flush` when the content draws its own edges — a chart, or a list of `Row`s
 * that should run the full width of the card. */
export function Card({
  children,
  wide = false,
  flush = false,
  className,
}: {
  children: ReactNode
  wide?: boolean
  flush?: boolean
  className?: string
}) {
  const classes = ['card', wide && 'card--wide', flush && 'card--flush', className]
    .filter(Boolean)
    .join(' ')
  return <div className={classes}>{children}</div>
}

export default Card
