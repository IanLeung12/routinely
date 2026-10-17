import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { Button } from '../ui/Button.tsx'
import { EmptyState } from '../ui/EmptyState.tsx'
import { ErrorState } from '../ui/ErrorState.tsx'
import { Loading } from '../ui/Loading.tsx'
import { StatusChip } from '../ui/StatusChip.tsx'
import { MonitoringToggle } from '../about/MonitoringToggle.tsx'
import { fetchDrift, fetchResident } from './api.ts'
import type { ResidentDrift } from './api.ts'
import { BaselineChart } from './BaselineChart.tsx'
import { ContextTimeline } from './ContextTimeline.tsx'
import { DriftCard } from './DriftCard.tsx'
import HeatCalendar from './HeatCalendar.tsx'
import { SessionList } from './SessionList.tsx'
import { dailyScores } from './days.ts'
import type { Resident } from './types.ts'

const HEADING_ID = 'resident-detail-heading'

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
}: {
  residentId: string
  onBack: () => void
}) {
  const [loaded, setLoaded] = useState<Loaded | null>(null)
  const [attempt, setAttempt] = useState(0)
  const [monitoring, setMonitoring] = useState(true)
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
          <h1 id={HEADING_ID} ref={headingRef} tabIndex={-1}>{resident.name}</h1>
          <span className="resident-room">Room {resident.room}</span>
          <MonitoringToggle room={resident.room} on={monitoring} onChange={setMonitoring} />
          <StatusChip status={resident.status} />
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
      <button type="button" className="back-button" onClick={onBack}>
        ← Unit overview
      </button>
      {body}
    </section>
  )
}
