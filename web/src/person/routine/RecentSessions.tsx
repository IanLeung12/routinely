import { Card } from '../../ui/Card.tsx'
import { EmptyState } from '../../ui/EmptyState.tsx'
import { Pill } from '../../ui/Pill.tsx'
import { Row } from '../../ui/Row.tsx'
import { SectionHeader } from '../../ui/SectionHeader.tsx'
import { describeSession } from './sessionWords.ts'
import type { PersonRoutine } from './types.ts'
import './routine.css'

/** Enough to see the last few days without scrolling a phone forever. */
const DEFAULT_LIMIT = 5

/** The person's own recent attempts (SPEC section 17): what they were doing, when,
 * what went the way it usually does and what looked different. Never scored, never
 * ranked - a session is a morning, not a mark out of ten. */
export function RecentSessions({
  routine,
  limit = DEFAULT_LIMIT,
}: {
  routine: PersonRoutine
  limit?: number
}) {
  const sessions = routine.sessions.slice(0, limit)

  return (
    <Card>
      <SectionHeader title="Recent sessions" caption="Newest first" />
      {sessions.length === 0 ? (
        <EmptyState message="No sessions yet. They show up here as you go." />
      ) : (
        <ul className="routine-sessions">
          {sessions.map((session) => {
            const words = describeSession(session, routine.usual_minutes, routine.now)
            const detail = [words.different, words.smooth].filter(Boolean).join(' ')
            return (
              <li key={session.session_id}>
                <Row
                  title={session.task}
                  subtitle={`${words.when} · ${detail}`}
                  value={<span className="tabular-nums">{words.took}</span>}
                  trailing={
                    words.different === '' ? (
                      <Pill tone="positive">Like your usual</Pill>
                    ) : (
                      <Pill tone="watch">A bit different</Pill>
                    )
                  }
                />
              </li>
            )
          })}
        </ul>
      )}
    </Card>
  )
}

export default RecentSessions
