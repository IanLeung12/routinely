import { useId } from 'react'
import type { FeedbackVerdict } from '../contracts.ts'
import { Button } from '../ui/Button.tsx'
import type { ButtonVariant } from '../ui/Button.tsx'

const OPTIONS: { verdict: FeedbackVerdict; label: string }[] = [
  { verdict: 'confirmed', label: 'Confirmed' },
  { verdict: 'false_alarm', label: 'False alarm' },
]

const OTHER_CAUSE = 'other'

const CAUSE_LABEL = 'What was it? (optional)'

/** The two verdicts are the loud thing on this card: "Confirmed" is the main action
 * (primary) and "False alarm" the one that undoes a flag (danger, docs/DESIGN.md).
 * Once one is answered the other steps back to a quiet secondary, so which way it was
 * answered reads from weight and fill, not only from `aria-pressed` and the colour. */
function verdictVariant(verdict: FeedbackVerdict, value?: FeedbackVerdict | null): ButtonVariant {
  const loud: ButtonVariant = verdict === 'confirmed' ? 'primary' : 'danger'
  if (!value) return loud
  return value === verdict ? loud : 'secondary'
}

/** Lets a nurse record whether a flagged alert was real, so the threshold can learn from it.
 *
 * Once an alert is confirmed, `causeOptions` (the patterns this change was flagged as being
 * consistent with) turns into the "what was it?" picker from SPEC section 5, MVP 8: the
 * nurse's answer is reported through `onCauseChange` and stored with the feedback. */
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
  const causeLabelId = useId()
  return (
    <div className="feedback-buttons">
      <div role="group" aria-label="Nurse feedback" className="feedback-buttons__verdicts">
        {OPTIONS.map((option) => (
          <Button
            key={option.verdict}
            className="feedback-button"
            variant={verdictVariant(option.verdict, value)}
            aria-pressed={value === option.verdict}
            onClick={() => onChange(option.verdict)}
          >
            {option.label}
          </Button>
        ))}
        <p className="feedback-buttons__status" role="status" aria-live="polite">
          {value === 'confirmed' ? 'Marked as confirmed' : value === 'false_alarm' ? 'Marked as false alarm' : ''}
        </p>
      </div>
      {value === 'confirmed' && causeOptions && (
        <div role="group" aria-labelledby={causeLabelId} className="feedback-buttons__cause">
          <p className="feedback-buttons__cause-label" id={causeLabelId}>
            {CAUSE_LABEL}
          </p>
          {[...causeOptions, { id: OTHER_CAUSE, label: 'Other' }].map((option) => (
            <Button
              key={option.id}
              className="feedback-button feedback-button--cause"
              variant={cause === option.id ? 'primary' : 'secondary'}
              aria-pressed={cause === option.id}
              onClick={() => onCauseChange?.(option.id)}
            >
              {option.label}
            </Button>
          ))}
        </div>
      )}
    </div>
  )
}
