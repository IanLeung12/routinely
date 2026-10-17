import { useEffect, useRef, useState } from 'react'
import './liveSession.css'
import { fetchResident } from '../resident/api.ts'
import type { Resident } from '../resident/types.ts'
import { Button } from '../ui/Button.tsx'
import { Card } from '../ui/Card.tsx'
import { EmptyState } from '../ui/EmptyState.tsx'
import { ErrorState } from '../ui/ErrorState.tsx'
import { SectionHeader } from '../ui/SectionHeader.tsx'
import type { TaskError } from '../contracts.ts'
import { describeError, ERROR_TYPE_TONE } from '../ui/errorTypes.ts'
import { SessionSummary } from './SessionSummary.tsx'
import { SkeletonView } from './SkeletonView.tsx'
import { TaskMap } from './TaskMap.tsx'
import { TaskMapLegend } from './TaskMapLegend.tsx'
import type { LiveCamera, LiveSessionEnded, LiveStep, StepState } from './useLiveSession.ts'
import { useLiveSession } from './useLiveSession.ts'

/** `routine_watch.demo.DEMO_RESIDENT`: whoever is on camera, the live WS always
 * records the session against this resident unless told otherwise, and nothing on
 * this screen tells it otherwise. */
const DEMO_RESIDENT_ID = 'mrs-k'

/** This resident's own record, as `GET /residents/{id}` serves it: their baseline (the
 * duration and error count their sessions usually have, averaged over the early window
 * it's anchored to in `routine_watch.demo` - averaging their recorded sessions here
 * instead would fold in the recent bad days this screen is flagging and quietly excuse
 * them) and their room, so the panel knows which room's pause/resume toggle is its own
 * (T275). Null until it loads, and when nobody - live or offline - has that resident. */
function useResident(residentId: string): Resident | null {
  const [resident, setResident] = useState<Resident | null>(null)

  useEffect(() => {
    let cancelled = false
    fetchResident(residentId).then((loaded) => {
      if (cancelled) return
      setResident(loaded)
    })
    return () => {
      cancelled = true
    }
  }, [residentId])

  return resident
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

/** Strips `?source=camera` (and `?camera=`) from the dashboard URL and reloads, landing
 * back on the recorded scenario this screen otherwise falls back to (T394). A full
 * reload, not a state change, because the camera is picked once from the URL when the
 * screen first mounts (`LiveScreen.tsx`). */
function watchRecordedSession() {
  const url = new URL(window.location.href)
  url.searchParams.delete('source')
  url.searchParams.delete('camera')
  window.location.assign(url.toString())
}

/** The verdict for a finished session, and nothing else. It is a `role="status"` live
 * region, so anything nested inside it is read out again with the banner text every
 * time the region updates - which is why the "Open alert" button sits beside it rather
 * than in it (T376). */
function FlagBanner({ flag }: { flag: boolean }) {
  return (
    <p role="status" className={`live-session__banner live-session__banner--${flag ? 'flagged' : 'clear'}`}>
      {flag ? 'Flagged for review' : 'Session complete, nothing flagged'}
    </p>
  )
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
  /** Watch this machine's camera instead of the recorded `scenario` (T356): set by
   * `?source=camera` on the dashboard URL, which `scripts/camera.sh` prints. The API
   * sends the same messages from either, so only the socket and the two lines below -
   * the badge and the object-detector note - know the difference. */
  camera?: LiveCamera | null
  onOpenAlert?: (alertId: string) => void
  /** Called once per `session_end`, so the overview and alerts list can refetch
   * without a page reload (the dashboard has no other source of truth for them). */
  onSessionEnd?: (ended: LiveSessionEnded) => void
}

/** Screen 3 (SPEC section 9): skeleton view next to the task-graph map. Steps turn green
 * as they're done; an error ticker lists omissions and repeats/sequence errors as they
 * happen; a flagged `session_end` opens a "flagged for review" banner. The product flags
 * a change for review; it never diagnoses. */
export function LiveSession({
  scenario,
  speed = 1,
  camera = null,
  onOpenAlert,
  onSessionEnd,
}: LiveSessionProps) {
  const {
    steps,
    frame,
    states,
    errors,
    stepSpan,
    ended,
    paused: wsPaused,
    objectsSeen,
    source,
    cameraUnavailable,
    retry,
  } = useLiveSession(scenario, speed, camera)
  const announcement = useAnnouncement(steps, states, errors, source)
  const resident = useResident(DEMO_RESIDENT_ID)
  const baseline = resident?.baseline ?? null
  const handledEnded = useRef<LiveSessionEnded | null>(null)

  // A pause/resume toggled from the resident's page while this panel is open (SPEC
  // section 12, T275): `setRoomMonitoring` fires `monitoring-changed` on `window` after
  // a successful PUT. Pausing shows the message right away - the toggle itself is
  // authoritative, no need to wait for the socket - but resuming reopens the socket
  // (the same path "Check again" uses, below) since only a fresh connection can say
  // what is actually playing now. Refs, not state, carry the latest room/retry into
  // the listener so it's only attached once and removed on unmount.
  const [pausedOverride, setPausedOverride] = useState<{ room: string } | null>(null)
  const paused = pausedOverride ?? wsPaused

  function recheck() {
    setPausedOverride(null)
    retryRef.current()
  }

  const ownRoomRef = useRef<string | null>(null)
  const retryRef = useRef(retry)
  const recheckRef = useRef(recheck)
  useEffect(() => {
    ownRoomRef.current = resident?.room ?? paused?.room ?? null
    retryRef.current = retry
    recheckRef.current = recheck
  })

  useEffect(() => {
    function handleMonitoringChanged(event: Event) {
      const { room, paused: nowPaused } = (event as CustomEvent<{ room: string; paused: boolean }>).detail
      if (room !== ownRoomRef.current) {
        return
      }
      if (nowPaused) {
        setPausedOverride({ room })
      } else {
        recheckRef.current()
      }
    }
    window.addEventListener('monitoring-changed', handleMonitoringChanged)
    return () => window.removeEventListener('monitoring-changed', handleMonitoringChanged)
  }, [])

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
        action={
          source === 'mock' ? (
            <span className="live-session__mock-badge">Mock data</span>
          ) : camera ? (
            <span className="live-session__camera-badge">Live camera</span>
          ) : null
        }
      />

      {/* `/ws/live?source=camera` closes with `live_camera.CAMERA_UNAVAILABLE` when no
          camera on this machine could be read (T356): no message was sent first, so
          falling back to mock data here would look like a camera is live when there is
          none. Say so plainly instead, distinct from a dropped connection or an unknown
          scenario (T394), with a way back to the recorded scenario this screen plays by
          default. */}
      {cameraUnavailable ? (
        <Card>
          <ErrorState message="No camera could be opened on this machine — run scripts/camera.sh, or watch a recorded session." />
          <Button onClick={watchRecordedSession}>Watch a recorded session</Button>
        </Card>
      ) : paused ? (
        <Card>
          <div role="status">
            <EmptyState message={`Monitoring is paused for room ${paused.room}`} />
            <p className="live-session__paused-hint">
              Turn it back on from the resident's page to watch their routines again.
            </p>
            <Button onClick={recheck}>Check again</Button>
          </div>
        </Card>
      ) : (
        <>
          {ended && (
            <>
              <SessionSummary
                durationS={stepSpan ? stepSpan.end - stepSpan.start : 0}
                errorCount={errors.length}
                usualDurationS={baseline?.usual_duration_s}
                usualErrors={baseline?.usual_errors}
              />
              {ended.flag && ended.alert_id && onOpenAlert ? (
                <div className="live-session__banner-row">
                  <FlagBanner flag />
                  <Button onClick={() => onOpenAlert(ended.alert_id as string)}>Open alert</Button>
                </div>
              ) : (
                <FlagBanner flag={ended.flag} />
              )}
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
              {/* A camera whose frames carry no object boxes: the local detector has no
                  weights to run (`DETECTOR_WEIGHTS`, SPEC section 6.1), and a step is a
                  hand on an object, so none will ever be recognised. The skeleton view
                  next to this is still live, so say which half is missing instead of
                  leaving a task map that looks stuck (T356). */}
              {camera && frame && !objectsSeen && (
                <p className="live-session__detector-note" role="status">
                  Waiting for object detector. The skeleton and hands are live; steps stay
                  pending until the detector reports the objects in view (set
                  DETECTOR_WEIGHTS to run it).
                </p>
              )}
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
        </>
      )}
    </section>
  )
}

export default LiveSession
