import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { EmptyState } from '../ui/EmptyState.tsx'
import { Loading } from '../ui/Loading.tsx'
import { StatusChip } from '../ui/StatusChip.tsx'
import { fetchDrift, fetchResident } from './api.ts'
import type { ResidentDrift } from './api.ts'
import { BaselineChart } from './BaselineChart.tsx'
import { ContextTimeline } from './ContextTimeline.tsx'
import { DriftCard } from './DriftCard.tsx'
import HeatCalendar from './HeatCalendar.tsx'
import { SessionList } from './SessionList.tsx'
import { dailyScores } from './days.ts'
import type { Resident } from './types.ts'

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
  /** Tagged with the id it was fetched for, so switching resident shows the new one
   * loading rather than the last one's chart. */
  const [loaded, setLoaded] = useState<{
    residentId: string; resident: Resident | null; drift: ResidentDrift | null
  } | null>(
    null,
  )

  useEffect(() => {
    let cancelled = false
    Promise.all([fetchResident(residentId), fetchDrift(residentId)]).then(([resident, drift]) => {
      if (!cancelled) {
        setLoaded({ residentId, resident, drift })
      }
    })
    return () => {
      cancelled = true
    }
  }, [residentId])

  let body: ReactNode
  if (loaded === null || loaded.residentId !== residentId) {
    body = <Loading label="Loading resident…" />
  } else if (loaded.resident === null) {
    body = <EmptyState message={`No data for resident ${residentId}.`} />
  } else {
    const resident = loaded.resident
    const days = dailyScores(resident.scores)
    body = (
      <>
        <header className="resident-detail__header">
          <h2>{resident.name}</h2>
          <span className="resident-room">Room {resident.room}</span>
          <StatusChip status={resident.status} />
        </header>

        <div className="resident-panels">
          <section className="panel panel--wide">
            <h3>Baseline</h3>
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
            <h3>Daily scores</h3>
            {days.length === 0 ? (
              <EmptyState message="No scored sessions yet." />
            ) : (
              <div className="heat-calendar">
                <HeatCalendar days={days} />
              </div>
            )}
          </section>

          <section className="panel">
            <h3>Sessions</h3>
            <SessionList
              sessions={resident.sessions}
              scores={resident.scores}
              threshold={resident.baseline.threshold}
            />
          </section>

          <section className="panel">
            <h3>Care records</h3>
            <ContextTimeline records={resident.care_records} />
          </section>
        </div>
      </>
    )
  }

  return (
    <section className="resident-detail">
      <button type="button" className="back-button" onClick={onBack}>
        ← Unit overview
      </button>
      {body}
    </section>
  )
}
