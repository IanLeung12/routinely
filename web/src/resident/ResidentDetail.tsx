import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { Button } from '../ui/Button.tsx'
import { EmptyState } from '../ui/EmptyState.tsx'
import { ErrorState } from '../ui/ErrorState.tsx'
import { Loading } from '../ui/Loading.tsx'
import { StatusChip } from '../ui/StatusChip.tsx'
import { MonitoringToggle } from '../about/MonitoringToggle.tsx'
import { fetchMonitoringHistory, fetchPausedRooms, setRoomMonitoring } from '../about/monitoringApi.ts'
import type { MonitoringChange } from '../about/monitoringApi.ts'
import { fetchDrift, fetchFeedbackHistory, fetchResident } from './api.ts'
import type { ResidentDrift } from './api.ts'
import { BaselineChart } from './BaselineChart.tsx'
import { ContextTimeline } from './ContextTimeline.tsx'
import { DriftCard } from './DriftCard.tsx'
import { FeedbackHistory } from './FeedbackHistory.tsx'
import type { FeedbackState } from './FeedbackHistory.tsx'
import HeatCalendar from './HeatCalendar.tsx'
import { MonitoringHistory } from './MonitoringHistory.tsx'
import { SessionList } from './SessionList.tsx'
import { dailyScores } from './days.ts'
import type { Resident } from './types.ts'
import './resident.css'
import './residentPrint.css'

const HEADING_ID = 'resident-detail-heading'

/** Which fetch a stored feedback answer came from: the resident, and which "Try
 * again" asked for it. */
function feedbackKeyFor(residentId: string, attempt: number): string {
  return `${residentId}#${attempt}`
}

/** Tagged with the id (and attempt) it was fetched for, so switching resident shows
 * the new one loading rather than the last one's chart, and "Try again" shows loading
 * rather than the stale error. */
type Loaded =
  | { residentId: string; status: 'ok'; resident: Resident | null; drift: ResidentDrift | null }
  | { residentId: string; status: 'error' }

/** Screen 2 (SPEC section 9): one resident's baseline chart, daily scores, sessions and
 * the care records a nurse reads next to them. Opened from the unit overview; the
 * evidence behind a flagged session stays one tap away on the alert screen. */
export function ResidentDetail({
  residentId,
  onBack,
  backLabel = 'Unit overview',
}: {
  residentId: string
  onBack: () => void
  /** Where Back goes, when it isn't the unit overview: a supervisor who supports one
   * person reaches this screen from their people list (SPEC section 17). */
  backLabel?: string
}) {
  const [loaded, setLoaded] = useState<Loaded | null>(null)
  const [attempt, setAttempt] = useState(0)
  const [monitoring, setMonitoring] = useState(true)
  const [monitoringMessage, setMonitoringMessage] = useState<string | null>(null)
  const [monitoringChanges, setMonitoringChanges] = useState<MonitoringChange[]>([])
  /** Tagged with the resident (and attempt) it was fetched for, like `loaded`: the
   * card shows the new resident loading rather than the last one's answers. */
  const [feedback, setFeedback] = useState<{ key: string; state: FeedbackState } | null>(null)
  const headingRef = useRef<HTMLHeadingElement>(null)
  /** Which resident focus has already landed on, so re-rendering after the monitoring
   * toggle changes (same resident, new data) doesn't steal focus back from the nurse. */
  const focusedResidentIdRef = useRef<string | null>(null)

  /** Moves focus to the `h1` as soon as a resident finishes loading, so a screen reader
   * announces whose page this is right when the screen opens (SPEC section 9). */
  useEffect(() => {
    if (
      loaded !== null &&
      loaded.residentId === residentId &&
      loaded.status === 'ok' &&
      loaded.resident !== null &&
      focusedResidentIdRef.current !== residentId
    ) {
      headingRef.current?.focus()
      focusedResidentIdRef.current = residentId
    }
  }, [residentId, loaded])

  useEffect(() => {
    let cancelled = false
    Promise.all([fetchResident(residentId), fetchDrift(residentId)])
      .then(([resident, drift]) => {
        if (!cancelled) {
          setLoaded({ residentId, status: 'ok', resident, drift })
        }
      })
      .catch(() => {
        if (!cancelled) {
          setLoaded({ residentId, status: 'error' })
        }
      })
    return () => {
      cancelled = true
    }
  }, [residentId, attempt])

  /** What her nurses have already answered, and the pattern ranking it changed
   * (SPEC Nice to have 8). Fetched on its own rather than with the resident: feedback
   * the API can't serve costs the card, not the whole screen. */
  useEffect(() => {
    let cancelled = false
    const key = feedbackKeyFor(residentId, attempt)
    fetchFeedbackHistory(residentId)
      .then((value) => {
        if (!cancelled) {
          setFeedback({ key, state: { status: 'ok', feedback: value } })
        }
      })
      .catch(() => {
        if (!cancelled) {
          setFeedback({ key, state: { status: 'error' } })
        }
      })
    return () => {
      cancelled = true
    }
  }, [residentId, attempt])

  /** Loads this room's real pause state and who changed it (SPEC §12) once the
   * resident (and so its room) is known. Keeps today's local-only "on" default and an
   * empty trail if the API can't be reached (mock mode). */
  useEffect(() => {
    if (loaded === null || loaded.residentId !== residentId || loaded.status !== 'ok' || loaded.resident === null) {
      return
    }
    const room = loaded.resident.room
    let cancelled = false
    fetchPausedRooms()
      .then((pausedRooms) => {
        if (!cancelled) {
          setMonitoring(!pausedRooms.includes(room))
        }
      })
      .catch(() => { /* API unreachable: keep the local-only "on" default. */ })
    fetchMonitoringHistory(room)
      .then((changes) => {
        if (!cancelled) {
          setMonitoringChanges(changes)
        }
      })
      .catch(() => { /* API unreachable: no trail to show. */ })
    return () => {
      cancelled = true
    }
  }, [residentId, loaded])

  let body: ReactNode
  if (loaded === null || loaded.residentId !== residentId) {
    body = <Loading label="Loading resident…" />
  } else if (loaded.status === 'error') {
    body = (
      <>
        <ErrorState message="Could not reach the server. This resident's data could not be loaded." />
        <Button variant="primary" onClick={() => { setLoaded(null); setAttempt((n) => n + 1) }}>
          Try again
        </Button>
      </>
    )
  } else if (loaded.resident === null) {
    body = <EmptyState message="Resident not found." />
  } else {
    const resident = loaded.resident
    const days = dailyScores(resident.scores)
    body = (
      <>
        <header className="resident-detail__header">
          <div className="resident-detail__title-row">
            <h1 id={HEADING_ID} ref={headingRef} tabIndex={-1}>{resident.name}</h1>
            <span className="resident-room">Room {resident.room}</span>
            <StatusChip status={resident.status} />
            <Button variant="secondary" className="no-print" onClick={() => window.print()}>
              Print
            </Button>
          </div>
          <div className="resident-detail__monitoring">
            <div className="no-print">
              <MonitoringToggle
                room={resident.room}
                on={monitoring}
                onChange={(next) => {
                  setMonitoring(next)
                  setMonitoringMessage(null)
                  setRoomMonitoring(resident.room, next)
                    .then(() =>
                      // The change is logged server side, so re-read the trail rather
                      // than guessing who the API wrote it down as.
                      fetchMonitoringHistory(resident.room)
                        .then(setMonitoringChanges)
                        .catch(() => { /* API unreachable: keep the trail we have. */ }),
                    )
                    .catch(() => {
                      setMonitoring(!next)
                      setMonitoringMessage("Couldn't change monitoring. Try again.")
                    })
                }}
              />
              <MonitoringHistory changes={monitoringChanges} />
              {monitoringMessage && (
                <p className="resident-detail__monitoring-message" role="alert">{monitoringMessage}</p>
              )}
            </div>
            {resident.consent && (
              <p className="resident-detail__consent">
                Consent: {resident.consent.given_by}, {resident.consent.on}
              </p>
            )}
          </div>
        </header>

        <div className="resident-panels">
          <section className="panel panel--wide">
            <h2>Baseline</h2>
            <BaselineChart scores={resident.scores} baseline={resident.baseline} />
          </section>

          {loaded.drift && (
            <DriftCard
              slopePerDay={loaded.drift.slope_per_day}
              days={loaded.drift.days}
              trending={loaded.drift.trending}
            />
          )}

          <section className="panel">
            <h2>Daily scores</h2>
            {days.length === 0 ? (
              <EmptyState message="No scored sessions yet." />
            ) : (
              <div className="heat-calendar">
                <HeatCalendar days={days} />
              </div>
            )}
          </section>

          <section className="panel">
            <h2>Sessions</h2>
            <SessionList
              sessions={resident.sessions}
              scores={resident.scores}
              threshold={resident.baseline.threshold}
            />
          </section>

          <FeedbackHistory
            state={
              feedback?.key === feedbackKeyFor(residentId, attempt)
                ? feedback.state
                : { status: 'loading' }
            }
          />

          <section className="panel">
            <h2>Care records</h2>
            <ContextTimeline records={resident.care_records} />
          </section>
        </div>
      </>
    )
  }

  return (
    <section
      className="resident-detail"
      aria-labelledby={loaded?.status === 'ok' && loaded.resident ? HEADING_ID : undefined}
    >
      <button type="button" className="back-button no-print" onClick={onBack}>
        ← {backLabel}
      </button>
      {body}
    </section>
  )
}
