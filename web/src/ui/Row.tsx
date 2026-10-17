import type { ReactNode } from 'react'

/** One dense line in a list: who/what on the left, the number on the right, a
 * chip or pill after it (docs/DESIGN.md). Rows draw their own hairline against
 * the row above, so render them as siblings — bare, or one per `<li>`.
 *
 * Pass `onSelect` to make the whole row a button; `selectLabel` then says where
 * it goes, because the row's own text is rarely a sentence. */
export function Row({
  title,
  subtitle,
  value,
  leading,
  trailing,
  onSelect,
  selectLabel,
  className,
}: {
  title: ReactNode
  subtitle?: ReactNode
  value?: ReactNode
  leading?: ReactNode
  trailing?: ReactNode
  onSelect?: () => void
  selectLabel?: string
  className?: string
}) {
  const content = (
    <>
      {leading ? <span className="row__leading">{leading}</span> : null}
      <span className="row__main">
        <span className="row__title">{title}</span>
        {subtitle ? <span className="row__subtitle">{subtitle}</span> : null}
      </span>
      {value !== undefined ? <span className="row__value">{value}</span> : null}
      {trailing ? <span className="row__trailing">{trailing}</span> : null}
    </>
  )

  if (onSelect) {
    return (
      <button
        type="button"
        className={['row', 'row--interactive', className].filter(Boolean).join(' ')}
        onClick={onSelect}
        aria-label={selectLabel}
      >
        {content}
      </button>
    )
  }

  return <div className={['row', className].filter(Boolean).join(' ')}>{content}</div>
}

export default Row
