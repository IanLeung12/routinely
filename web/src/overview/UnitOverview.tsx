import { useEffect, useState } from 'react'
import { fetchResidents } from './api.ts'
import { Sparkline } from './Sparkline.tsx'
import { StatusChip } from './StatusChip.tsx'
import type { ResidentSummary, ResidentStatus } from './types.ts'

const STATUS_ORDER: Record<ResidentStatus, number> = { flagged: 0, watch: 1, normal: 2 }

function sortResidents(residents: ResidentSummary[]): ResidentSummary[] {
  return [...residents].sort((a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status])
}

/** Screen 1 (SPEC section 9): resident list with a status chip and an error-score
 * sparkline, flagged residents first. Visual first; a nurse should read it in 10s. */
export function UnitOverview() {
  const [residents, setResidents] = useState<ResidentSummary[] | null>(null)

  useEffect(() => {
    let cancelled = false
    fetchResidents().then((fetched) => {
      if (!cancelled) {
        setResidents(fetched)
      }
    })
    return () => {
      cancelled = true
    }
  }, [])

  if (residents === null) {
    return <p className="muted">Loading residents…</p>
  }

  return (
    <ul className="resident-list">
      {sortResidents(residents).map((resident) => (
        <li key={resident.id} className="resident-row">
          <div className="resident-identity">
            <span className="resident-name">{resident.name}</span>
            <span className="resident-room">Room {resident.room}</span>
          </div>
          <StatusChip status={resident.status} />
          <Sparkline scores={resident.scores} />
        </li>
      ))}
    </ul>
  )
}
