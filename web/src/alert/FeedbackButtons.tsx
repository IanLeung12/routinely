import type { FeedbackVerdict } from '../contracts.ts'

const OPTIONS: { verdict: FeedbackVerdict; label: string }[] = [
  { verdict: 'confirmed', label: 'Confirmed' },
  { verdict: 'false_alarm', label: 'False alarm' },
]

/** Lets a nurse record whether a flagged alert was real, so the threshold can learn from it. */
export function FeedbackButtons({
  value,
  onChange,
}: {
  value?: FeedbackVerdict | null
  onChange: (v: FeedbackVerdict) => void
}) {
  return (
    <div className="feedback-buttons" role="group" aria-label="Nurse feedback">
      {OPTIONS.map((option) => (
        <button
          key={option.verdict}
          type="button"
          className="feedback-button"
          aria-pressed={value === option.verdict}
          onClick={() => onChange(option.verdict)}
        >
          {option.label}
        </button>
      ))}
      <p role="status" aria-live="polite">
        {value === 'confirmed' ? 'Marked as confirmed' : value === 'false_alarm' ? 'Marked as false alarm' : ''}
      </p>
    </div>
  )
}
