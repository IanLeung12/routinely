import type { TaskError } from '../contracts.ts'
import { describeError, ERROR_TYPE_TONE } from '../ui/errorTypes.ts'
import { Row } from '../ui/Row.tsx'

function formatTimestamp(t: number): string {
  const minutes = Math.floor(t / 60)
  const seconds = Math.floor(t % 60)
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

function errorPhrase(error: TaskError): string {
  const step = error.step_id ? error.step_id.replace(/_/g, ' ') : 'this step'
  return describeError(error.type, step)
}

/** The error-by-error detail behind an alert (SPEC section 9, screen 4): one dense,
 * hairline-separated row per error — type pill on the left (red omission/substitution,
 * amber sequence/repeat, grey unclear), what happened in the middle, the timestamp
 * right-aligned and tabular so the column scans. Each row opens that error's replay
 * through `onOpen`. */
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
            <Row
              className="error-row"
              leading={
                <span className={`error-chip error-chip--${ERROR_TYPE_TONE[error.type]}`}>
                  {error.type}
                </span>
              }
              title={<span className="error-list__phrase">{phrase}</span>}
              value={<span className="error-list__time tabular-nums">{time}</span>}
              trailing={
                <span className="error-list__open-hint" aria-hidden="true">
                  ›
                </span>
              }
              onSelect={() => onOpen(error)}
              selectLabel={`Open evidence: ${phrase} at ${time}`}
            />
          </li>
        )
      })}
    </ul>
  )
}

export default ErrorList
