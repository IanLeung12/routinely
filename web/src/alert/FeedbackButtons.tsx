import type { FeedbackVerdict } from '../contracts.ts'

const OPTIONS: { verdict: FeedbackVerdict; label: string }[] = [
  { verdict: 'confirmed', label: 'Confirmed' },
  { verdict: 'false_alarm', label: 'False alarm' },
]

const OTHER_CAUSE = 'other'

/** Lets a nurse record whether a flagged alert was real, so the threshold can learn from it. */
export function FeedbackButtons({
  value,
  onChange,
  causeOptions,
  cause,
  onCauseChange,
}: {
  value?: FeedbackVerdict | null
  onChange: (v: FeedbackVerdict) => void
  causeOptions?: { id: string; label: string }[]
  cause?: string | null
  onCauseChange?: (id: string) => void
}) {
  return (
    <div className="feedback-buttons">
      <div role="group" aria-label="Nurse feedback">
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
      {value === 'confirmed' && causeOptions && (
        <div role="group" aria-label="What was it? (optional)" className="feedback-buttons__cause">
          {[...causeOptions, { id: OTHER_CAUSE, label: 'Other' }].map((option) => (
            <button
              key={option.id}
              type="button"
              className="feedback-button"
              aria-pressed={cause === option.id}
              onClick={() => onCauseChange?.(option.id)}
            >
              {option.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
