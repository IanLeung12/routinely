import { useEffect, useRef, useState } from 'react'
import { Card } from '../ui/Card.tsx'
import { EmptyState } from '../ui/EmptyState.tsx'
import { SectionHeader } from '../ui/SectionHeader.tsx'
import type { ErrorType, TaskError } from '../contracts.ts'
import { SkeletonView } from './SkeletonView.tsx'
import { TaskMap } from './TaskMap.tsx'
import { TaskMapLegend } from './TaskMapLegend.tsx'
import type { LiveStep, StepState } from './useLiveSession.ts'
import { useLiveSession } from './useLiveSession.ts'

/** Plain-language names for the error types in SPEC section 7. */
const ERROR_LABELS: Record<ErrorType, string> = {
  omission: 'Omission',
  sequence: 'Sequence',
  perseveration: 'Perseveration',
  substitution: 'Substitution',
  hesitation: 'Hesitation',
  abandonment: 'Abandonment',
}

/** Red = omission/substitution, amber = sequence/repeat, grey = anything softer
 * (SPEC section 9: never colour alone, so the label carries the meaning too). */
const ERROR_COLOR: Record<ErrorType, 'red' | 'amber' | 'grey'> = {
  omission: 'red',
  substitution: 'red',
  sequence: 'amber',
  perseveration: 'amber',
  hesitation: 'grey',
  abandonment: 'grey',
}

function formatClock(seconds: number): string {
  const whole = Math.max(0, Math.round(seconds))
  const minutes = Math.floor(whole / 60)
  const secs = String(whole % 60).padStart(2, '0')
  return `${minutes}:${secs}`
}

function stepLabel(steps: LiveStep[], stepId: string | null | undefined): string {
  return steps.find((step) => step.id === stepId)?.label ?? 'Session'
}

function errorText(steps: LiveStep[], error: TaskError): string {
  return `${ERROR_LABELS[error.type]} · ${stepLabel(steps, error.step_id)} · ${formatClock(error.t_start)}`
}

/** Drives the screen-reader-only live region: one short sentence per step completion,
 * raised flag, or connection change, so a nurse who isn't looking at the screen still
 * hears what just happened (SPEC section 9 says the screen must read in ~10 seconds,
 * which assumes sight; this is the non-visual equivalent). */
function useAnnouncement(
  steps: LiveStep[],
  states: Record<string, StepState>,
  errors: TaskError[],
  source: 'live' | 'mock',
): string {
  const [announcement, setAnnouncement] = useState('')
  const prevStates = useRef<Record<string, StepState>>({})
  const prevErrorCount = useRef(0)
  const prevSource = useRef(source)

  useEffect(() => {
    for (const [stepId, state] of Object.entries(states)) {
      if (state === 'done' && prevStates.current[stepId] !== 'done') {
        setAnnouncement(`Step done: ${stepLabel(steps, stepId)}`)
      }
    }
    prevStates.current = states
  }, [states, steps])

  useEffect(() => {
    if (errors.length > prevErrorCount.current) {
      setAnnouncement(`Flag raised: ${errorText(steps, errors[errors.length - 1])}`)
    }
    prevErrorCount.current = errors.length
  }, [errors, steps])

  useEffect(() => {
    if (source !== prevSource.current) {
      setAnnouncement(
        source === 'mock' ? 'Connection lost. Showing offline demo data.' : 'Connected to live session.',
      )
    }
    prevSource.current = source
  }, [source])

  return announcement
}

export type LiveSessionProps = {
  scenario: string
  speed?: number
}

/** Screen 3 (SPEC section 9): skeleton view next to the task-graph map. Steps turn green
 * as they're done; an error ticker lists omissions and repeats/sequence errors as they
 * happen; a flagged `session_end` opens a "flagged for review" banner. The product flags
 * a change for review; it never diagnoses. */
export function LiveSession({ scenario, speed = 1 }: LiveSessionProps) {
  const { steps, frame, states, errors, ended, source } = useLiveSession(scenario, speed)
  const announcement = useAnnouncement(steps, states, errors, source)

  return (
    <section className="live-session">
      <style>{`
        .live-session__layout { display: grid; gap: var(--space-4); grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr)); margin-bottom: var(--space-4); }
        .live-session__mock-badge { padding: var(--space-1) var(--space-2); border-radius: var(--radius-sm); background: var(--error-grey-bg); color: var(--error-grey-text); font-size: var(--text-xs); font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }
        .live-session__banner { margin: 0 0 var(--space-4); padding: var(--space-3) var(--space-4); border-radius: var(--radius-md); font-weight: 600; }
        .live-session__banner--flagged { background: var(--status-flagged-bg); color: var(--status-flagged-text); }
        .live-session__banner--clear { background: var(--status-normal-bg); color: var(--status-normal-text); }
        .live-session__error-list { display: flex; flex-direction: column; gap: var(--space-2); margin: 0; padding: 0; list-style: none; }
        .live-session__announcer { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; }
      `}</style>

      <p className="live-session__announcer" aria-live="polite">
        {announcement}
      </p>

      <SectionHeader
        title="Live session"
        action={source === 'mock' ? <span className="live-session__mock-badge">Mock data</span> : null}
      />

      {ended && (
        <p
          role="status"
          className={`live-session__banner live-session__banner--${ended.flag ? 'flagged' : 'clear'}`}
        >
          {ended.flag ? 'Flagged for review' : 'Session complete, nothing flagged'}
        </p>
      )}

      <div className="live-session__layout">
        <Card>
          <SectionHeader title="Skeleton view" />
          <SkeletonView frame={frame} />
        </Card>
        <Card>
          <SectionHeader title="Task map" />
          <TaskMap steps={steps} states={states} />
          <TaskMapLegend />
        </Card>
      </div>

      <Card>
        <SectionHeader title="Errors" />
        {errors.length === 0 ? (
          <EmptyState message="No errors yet." />
        ) : (
          <ul className="live-session__error-list">
            {errors.map((error) => (
              <li key={error.error_id} className={`error-chip error-chip--${ERROR_COLOR[error.type]}`}>
                {errorText(steps, error)}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </section>
  )
}

export default LiveSession
