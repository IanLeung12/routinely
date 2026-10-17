export type SegmentedOption<T extends string> = { value: T; label: string }

/** A row of mutually exclusive options — the time-range picker on a chart, or any
 * "pick one view" control. The chosen option sits on a raised chip and reports
 * `aria-pressed`, so it never relies on colour alone. Every option is tabbable,
 * matching the grouped-button pattern already used on the overview (T318). */
export function SegmentedControl<T extends string>({
  label,
  options,
  value,
  onChange,
  className,
}: {
  label: string
  options: readonly SegmentedOption<T>[]
  value: T
  onChange: (value: T) => void
  className?: string
}) {
  const classes = ['segmented', className].filter(Boolean).join(' ')
  return (
    <div className={classes} role="group" aria-label={label}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          className="segmented__option"
          aria-pressed={option.value === value}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}

export default SegmentedControl
