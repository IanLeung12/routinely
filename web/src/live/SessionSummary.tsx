import { Card } from '../ui/Card.tsx'
import { SectionHeader } from '../ui/SectionHeader.tsx'
import type { SessionQuality } from './useLiveSession.ts'
import './sessionSummary.css'

export type SessionSummaryProps = {
  durationS: number
  errorCount: number
  /** This resident's own normal, from their recorded sessions. Omitted parts
   * (no history yet) are left out rather than shown as a guess. */
  usualDurationS?: number
  usualErrors?: number
  /** `session_end.quality` (SPEC section 12). `unclear` capture replaces the
   * comparison below with why this session wasn't scored: the duration and the
   * error count are read off the same capture, so with too little of it readable
   * they are not numbers to put beside this resident's normal. Defaults to `ok`,
   * which is what a `session_end` that carries no quality means. */
  quality?: SessionQuality
}

// Local, not ../resident/format.ts: that formatDuration always includes "0m"
// and pads seconds (e.g. "0m 30s"), but this screen drops the minutes part
// entirely under a minute (e.g. "30s").
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
 * that baseline isn't available, rather than guessing.
 *
 * Unclear capture gets the notice instead of the comparison (SPEC section 12):
 * the pipeline scores such a session 0.0 and keeps it out of this resident's
 * history, so a comparison here would read as a session that went perfectly. */
export function SessionSummary({
  durationS,
  errorCount,
  usualDurationS,
  usualErrors,
  quality = 'ok',
}: SessionSummaryProps) {
  if (quality === 'unclear') {
    return (
      <Card className="session-summary">
        <SectionHeader title="Session summary" />
        {/* Grey and in words, the way "unclear" reads everywhere else in the
            dashboard (SPEC section 7: never counted as an error). A live region, so
            a nurse who isn't watching the screen hears it rather than only the
            "nothing flagged" banner below it. */}
        <div role="status">
          <p className="session-summary__unclear">Capture unclear — this session wasn't scored</p>
          <p className="session-summary__why">
            The camera couldn't see enough of it: low light, the view blocked, or a walker or
            wheelchair in the way. Nothing in it is counted as an error.
          </p>
        </div>
      </Card>
    )
  }

  return (
    <Card className="session-summary">
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
