import type { ReactNode } from 'react'
import { Card } from '../../ui/Card.tsx'
import { EmptyState } from '../../ui/EmptyState.tsx'
import { Pill } from '../../ui/Pill.tsx'
import { SectionHeader } from '../../ui/SectionHeader.tsx'
import { personStatus } from '../personNotes.ts'
import type { PersonRoutine } from './types.ts'
import './routine.css'

/** Under half a minute either way is the same morning twice, not a change. */
const SAME_AS_USUAL_MINUTES = 0.5

function minutesLabel(minutes: number): string {
  return `${Math.max(1, Math.round(minutes))} min`
}

/** One number in the strip: the value first and large, its label above it, so today
 * and your usual can be compared without reading a sentence (docs/DESIGN.md). */
function Stat({ label, value, after }: { label: string; value: string; after?: ReactNode }) {
  return (
    <div className="routine-stat">
      <dt className="routine-stat__label">{label}</dt>
      <dd className="routine-stat__value">
        <span className="routine-stat__number tabular-nums">{value}</span>
        {after}
      </dd>
    </div>
  )
}

/** How today sits against their usual, in the person's words and never as a verdict:
 * a pill that carries its own sentence, so the colour is never the only signal. */
function DayPill({ minutes, usual }: { minutes: number; usual: number }) {
  const difference = minutes - usual
  if (Math.abs(difference) < SAME_AS_USUAL_MINUTES) {
    return <Pill tone="positive">About the same as usual</Pill>
  }
  if (difference > 0) {
    return (
      <Pill tone="watch" direction="up">
        {`about ${minutesLabel(difference)} longer`}
      </Pill>
    )
  }
  return (
    <Pill tone="positive" direction="down">
      {`about ${minutesLabel(-difference)} quicker`}
    </Pill>
  )
}

/** The person's status in plain words (SPEC section 17), with today's routine and
 * their own usual beside it. Calm on purpose: it says what their week looked like,
 * never what it means. */
export function RoutineStatus({ routine }: { routine: PersonRoutine }) {
  const today = routine.days[routine.days.length - 1]

  return (
    <Card>
      <SectionHeader title="How this week looks" caption="Your routine, next to your usual" />
      <p className="routine-status__headline">{personStatus(routine.status)}</p>
      <p className="routine-status__lead">
        This is your own routine next to your usual week. It is not a medical opinion:
        if something looks different, it is worth a mention rather than a worry.
      </p>
      {today === undefined ? (
        <EmptyState message="Nothing recorded yet. Your week shows up here after your first routine." />
      ) : (
        <dl className="routine-status__stats">
          <Stat
            label="Today"
            value={minutesLabel(today.minutes)}
            after={<DayPill minutes={today.minutes} usual={today.usual_minutes} />}
          />
          <Stat label="Your usual" value={minutesLabel(routine.usual_minutes)} />
        </dl>
      )}
    </Card>
  )
}

export default RoutineStatus
