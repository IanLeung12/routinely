import type { ReactNode } from 'react'

/** Heading for a `Card`'s content, with an optional action (e.g. a button) at the
 * other end of the row. Matches the uppercase small-caps label style used across panels. */
export function SectionHeader({ title, action }: { title: string; action?: ReactNode }) {
  return (
    <div className="section-header">
      <h3 className="section-header__title">{title}</h3>
      {action}
    </div>
  )
}

export default SectionHeader
