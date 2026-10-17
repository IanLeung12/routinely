import { useEffect, useRef, useState } from 'react'
import './liveSession.css'
import { fetchResident } from '../resident/api.ts'
import type { Baseline } from '../resident/types.ts'
import { Card } from '../ui/Card.tsx'
import { EmptyState } from '../ui/EmptyState.tsx'
import { SectionHeader } from '../ui/SectionHeader.tsx'
import type { TaskError } from '../contracts.ts'
import { describeError, ERROR_TYPE_TONE } from '../ui/errorTypes.ts'
import { SessionSummary } from './SessionSummary.tsx'
import { SkeletonView } from './SkeletonView.tsx'
import { TaskMap } from './TaskMap.tsx'
import { TaskMapLegend } from './TaskMapLegend.tsx'
import type { LiveSessionEnded, LiveStep, StepState } from './useLiveSession.ts'
import { useLiveSession } from './useLiveSession.ts'

/** `routine_watch.demo.DEMO_RESIDENT`: whoever is on camera, the live WS always
 * records the session against this resident unless told otherwise, and nothing on
 * this screen tells it otherwise. */
const DEMO_RESIDENT_ID = 'mrs-k'

/** This resident's own normal, as the pipeline measures it: `GET /residents/{id}`
 * serves the duration and error count their sessions usually have, averaged over the
 * early window their baseline is anchored to (`routine_watch.demo`). Averaging their
 * recorded sessions here instead would fold in the recent bad days this screen is
 * flagging and quietly excuse them. Null until it loads, and when nobody - live or
 * offline - has that resident. */
function useResidentBaseline(residentId: string): Baseline | null {
  const [baseline, setBaseline] = useState<Baseline | null>(null)

  useEffect(() => {
    let cancelled = false
    fetchResident(residentId).then((resident) => {
      if (cancelled) return
      setBaseline(resident?.baseline ?? null)
    })
    return () => {
      cancelled = true
    }
  }, [residentId])

  return baseline
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
  return `${describeError(error.type, stepLabel(steps, error.step_id))} · ${formatClock(error.t_start)}`
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
  onOpenAlert?: (alertId: string) => void
  /** Called once per `session_end`, so the overview and alerts list can refetch
   * without a page reload (the dashboard has no other source of truth for them). */
  onSessionEnd?: (ended: LiveSessionEnded) => void
}

/** Screen 3 (SPEC section 9): skeleton view next to the task-graph map. Steps turn green
 * as they're done; an error ticker lists omissions and repeats/sequence errors as they
 * happen; a flagged `session_end` opens a "flagged for review" banner. The product flags
 * a change for review; it never diagnoses. */
export function LiveSession({ scenario, speed = 1, onOpenAlert, onSessionEnd }: LiveSessionProps) {
  const { steps, frame, states, errors, stepSpan, ended, source } = useLiveSession(scenario, speed)
  const announcement = useAnnouncement(steps, states, errors, source)
  const baseline = useResidentBaseline(DEMO_RESIDENT_ID)
  const handledEnded = useRef<LiveSessionEnded | null>(null)

  useEffect(() => {
    if (ended && ended !== handledEnded.current) {
      handledEnded.current = ended
      onSessionEnd?.(ended)
    }
  }, [ended, onSessionEnd])

  return (
    <section className="live-session">
      <p className="live-session__announcer" aria-live="polite">
        {announcement}
      </p>

      <SectionHeader
        title="Live session"
        action={source === 'mock' ? <span className="live-session__mock-badge">Mock data</span> : null}
      />

      {ended && (
        <>
          <SessionSummary
            durationS={stepSpan ? stepSpan.end - stepSpan.start : 0}
            errorCount={errors.length}
            usualDurationS={baseline?.usual_duration_s}
            usualErrors={baseline?.usual_errors}
          />
          <p
            role="status"
            className={`live-session__banner live-session__banner--${ended.flag ? 'flagged' : 'clear'}`}
          >
            {ended.flag ? 'Flagged for review' : 'Session complete, nothing flagged'}
            {ended.flag && ended.alert_id && onOpenAlert && (
              <button type="button" onClick={() => onOpenAlert(ended.alert_id as string)}>
                Open alert
              </button>
            )}
          </p>
        </>
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
              <li key={error.error_id} className={`error-chip error-chip--${ERROR_TYPE_TONE[error.type]}`}>
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
