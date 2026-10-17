import type { ReactNode } from 'react'

/** Heading for a `Card`'s content: the title on the left, an optional muted
 * `caption` naming what the numbers are ("last 14 days"), and an optional
 * `action` (e.g. a button or a SegmentedControl) at the other end of the row. */
export function SectionHeader({
  title,
  caption,
  action,
}: {
  title: string
  caption?: string
  action?: ReactNode
}) {
  return (
    <div className="section-header">
      <h3 className="section-header__title">{title}</h3>
      {caption ? <span className="section-header__caption">{caption}</span> : null}
      {action}
    </div>
  )
}

export default SectionHeader
