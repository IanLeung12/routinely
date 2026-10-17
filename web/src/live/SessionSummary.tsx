import { Card } from '../ui/Card.tsx'
import { SectionHeader } from '../ui/SectionHeader.tsx'

export type SessionSummaryProps = {
  durationS: number
  errorCount: number
  /** This resident's own normal, from their recorded sessions. Omitted parts
   * (no history yet) are left out rather than shown as a guess. */
  usualDurationS?: number
  usualErrors?: number
}

function formatDuration(seconds: number): string {
  const whole = Math.max(0, Math.round(seconds))
  const minutes = Math.floor(whole / 60)
  const secs = whole % 60
  return minutes > 0 ? `${minutes}m ${secs}s` : `${secs}s`
}

function formatCount(value: number): string {
  const rounded = Math.round(value * 10) / 10
  return rounded % 1 === 0 ? String(rounded) : rounded.toFixed(1)
}

function pluralize(count: number): string {
  return count === 1 ? 'error' : 'errors'
}

/** The live session's close (SPEC section 9, screen 3): one glance at how this
 * session compares with the resident's own normal, shown above the flag banner
 * when `session_end` arrives. Leaves out the "usually" half of either line when
 * that baseline isn't available, rather than guessing. */
export function SessionSummary({ durationS, errorCount, usualDurationS, usualErrors }: SessionSummaryProps) {
  return (
    <Card className="session-summary">
      <style>{`
        .session-summary__line { margin: 0; font-size: var(--text-base); }
        .session-summary__usual { color: var(--muted); }
      `}</style>
      <SectionHeader title="Session summary" />
      <p className="session-summary__line">
        {`Finished in ${formatDuration(durationS)}`}
        {usualDurationS !== undefined && (
          <span className="session-summary__usual">{` (usually ~${formatDuration(usualDurationS)})`}</span>
        )}
        {' · '}
        {`${errorCount} ${pluralize(errorCount)}`}
        {usualErrors !== undefined && (
          <span className="session-summary__usual">{` (usually ~${formatCount(usualErrors)})`}</span>
        )}
      </p>
    </Card>
  )
}

export default SessionSummary
