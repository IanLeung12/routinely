import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { StatusChip } from '../overview/StatusChip.tsx'
import { fetchResident } from './api.ts'
import { BaselineChart } from './BaselineChart.tsx'
import { ContextTimeline } from './ContextTimeline.tsx'
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
  const [loaded, setLoaded] = useState<{ residentId: string; resident: Resident | null } | null>(
    null,
  )

  useEffect(() => {
    let cancelled = false
    fetchResident(residentId).then((fetched) => {
      if (!cancelled) {
        setLoaded({ residentId, resident: fetched })
      }
    })
    return () => {
      cancelled = true
    }
  }, [residentId])

  let body: ReactNode
  if (loaded === null || loaded.residentId !== residentId) {
    body = <p className="muted">Loading resident…</p>
  } else if (loaded.resident === null) {
    body = <p className="muted">No data for resident {residentId}.</p>
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

          <section className="panel">
            <h3>Daily scores</h3>
            {days.length === 0 ? (
              <p className="muted">No scored sessions yet.</p>
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
