import { formatDayTime, formatDuration, formatErrors, formatScore } from './format.ts'
import type { ResidentSession, ScorePoint } from './types.ts'
import { EmptyState } from '../ui/EmptyState.tsx'

function time(ts: string): number {
  const parsed = Date.parse(ts)
  return Number.isNaN(parsed) ? 0 : parsed
}

/** This resident's recorded sessions, newest first (SPEC section 9, screen 2). Scores
 * come from the same `scores` series the chart draws, matched by timestamp. */
export function SessionList({
  sessions,
  scores,
  threshold,
}: {
  sessions: ResidentSession[]
  scores: ScorePoint[]
  threshold: number
}) {
  if (sessions.length === 0) {
    return <EmptyState message="No sessions recorded yet." />
  }

  const scoreByTs = new Map(scores.map((point) => [point.ts, point.score]))
  const newestFirst = [...sessions].sort((a, b) => time(b.ts) - time(a.ts))

  return (
    <ol className="session-list">
      {newestFirst.map((session) => {
        const score = scoreByTs.get(session.ts)
        const above = score !== undefined && score > threshold
        const errors = formatErrors(session.errors)

        return (
          <li key={session.ts} className={above ? 'session-row session-row--above' : 'session-row'}>
            <span className="session-when">{formatDayTime(session.ts)}</span>
            <span className="session-score">{score === undefined ? '—' : formatScore(score)}</span>
            <span className="session-detail">
              {session.assisted ? 'assisted, not counted' : errors || 'no errors'}
              {session.self_corrected > 0 && (
                <span className="session-note"> · {session.self_corrected} self-corrected</span>
              )}
              {above && <span className="session-note session-note--above"> · above threshold</span>}
            </span>
            <span className="session-duration">{formatDuration(session.duration_s)}</span>
          </li>
        )
      })}
    </ol>
  )
}
