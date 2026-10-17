import type { ErrorType, TaskError } from '../contracts.ts'

/** Same wording as `pipeline/src/routine_watch/explain.py`'s `_PHRASES`, so the
 * dashboard reads exactly like the plain-language summary it is built from. */
const PHRASES: Record<ErrorType, (step: string) => string> = {
  omission: (step) => `skipped ${step}`,
  perseveration: (step) => `repeated ${step}`,
  sequence: (step) => `${step} out of order`,
  substitution: (step) => `wrong object for ${step}`,
  hesitation: (step) => `long pause at ${step}`,
  abandonment: (step) => `stopped before ${step}`,
}

/** SPEC section 7/9: red = omission/substitution, amber = sequence/repeat,
 * grey = everything else (a pause or a stop is uncertain, not a clear mistake). */
const CHIP_COLOR: Record<ErrorType, 'red' | 'amber' | 'grey'> = {
  omission: 'red',
  substitution: 'red',
  sequence: 'amber',
  perseveration: 'amber',
  hesitation: 'grey',
  abandonment: 'grey',
}

function formatTimestamp(t: number): string {
  const minutes = Math.floor(t / 60)
  const seconds = Math.floor(t % 60)
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

function describeError(error: TaskError): string {
  const step = error.step_id ? error.step_id.replace(/_/g, ' ') : 'this step'
  return PHRASES[error.type](step)
}

/** The error-by-error detail behind an alert (SPEC section 9, screen 4). Each row
 * opens that error's replay through `onOpen`; the replay view itself is a later task. */
export function ErrorList({
  errors,
  onOpen,
}: {
  errors: TaskError[]
  onOpen: (error: TaskError) => void
}) {
  if (errors.length === 0) {
    return <p className="muted">No errors recorded for this alert.</p>
  }

  return (
    <ul className="error-list">
      {errors.map((error) => {
        const phrase = describeError(error)
        const time = formatTimestamp(error.t_start)
        return (
          <li key={error.error_id}>
            <button
              type="button"
              className="error-list__open"
              onClick={() => onOpen(error)}
              aria-label={`Open evidence: ${phrase} at ${time}`}
            >
              <span className={`error-chip error-chip--${CHIP_COLOR[error.type]}`}>
                {error.type}
              </span>
              <span className="error-list__phrase">{phrase}</span>
              <span className="error-list__time">{time}</span>
            </button>
          </li>
        )
      })}
    </ul>
  )
}

export default ErrorList
