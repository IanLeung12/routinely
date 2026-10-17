import type { TaskError } from '../contracts.ts'
import { describeError, ERROR_TYPE_TONE } from '../ui/errorTypes.ts'

function formatTimestamp(t: number): string {
  const minutes = Math.floor(t / 60)
  const seconds = Math.floor(t % 60)
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

function errorPhrase(error: TaskError): string {
  const step = error.step_id ? error.step_id.replace(/_/g, ' ') : 'this step'
  return describeError(error.type, step)
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
        const phrase = errorPhrase(error)
        const time = formatTimestamp(error.t_start)
        return (
          <li key={error.error_id}>
            <button
              type="button"
              className="error-list__open"
              onClick={() => onOpen(error)}
              aria-label={`Open evidence: ${phrase} at ${time}`}
            >
              <span className={`error-chip error-chip--${ERROR_TYPE_TONE[error.type]}`}>
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
