import type { ReactNode } from 'react'

/** Panel surface used to group related content. Pass `wide` inside a grid to span
 * every column (see `.resident-panels` in resident/ResidentDetail.tsx). */
export function Card({
  children,
  wide = false,
  className,
}: {
  children: ReactNode
  wide?: boolean
  className?: string
}) {
  const classes = ['card', wide && 'card--wide', className].filter(Boolean).join(' ')
  return <div className={classes}>{children}</div>
}

export default Card
