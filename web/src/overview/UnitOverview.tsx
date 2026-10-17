import { useEffect, useState } from 'react'
import { Loading } from '../ui/Loading.tsx'
import { StatusChip } from '../ui/StatusChip.tsx'
import { fetchResidents } from './api.ts'
import { Sparkline } from './Sparkline.tsx'
import type { ResidentSummary, ResidentStatus } from './types.ts'

const STATUS_ORDER: Record<ResidentStatus, number> = { flagged: 0, watch: 1, normal: 2 }

function sortResidents(residents: ResidentSummary[]): ResidentSummary[] {
  return [...residents].sort((a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status])
}

function summarize(residents: ResidentSummary[]): string {
  const flagged = residents.filter((r) => r.status === 'flagged').length
  const watch = residents.filter((r) => r.status === 'watch').length
  const normal = residents.filter((r) => r.status === 'normal').length

  if (flagged === 0 && watch === 0) {
    return 'All residents normal'
  }

  const parts: string[] = []
  if (flagged > 0) parts.push(`${flagged} flagged for review`)
  if (watch > 0) parts.push(`${watch} on watch`)
  if (normal > 0) parts.push(`${normal} normal`)
  return parts.join(' · ')
}

/** Screen 1 (SPEC section 9): resident list with a status chip and an error-score
 * sparkline, flagged residents first. Visual first; a nurse should read it in 10s.
 * The whole row opens that resident's detail. Without `onSelect` the list is read-only. */
export function UnitOverview({ onSelect }: { onSelect?: (residentId: string) => void }) {
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
    return <Loading label="Loading residents…" />
  }

  return (
    <>
      <p role="status" className="resident-summary">
        {summarize(residents)}
      </p>
      <ul className="resident-list">
        {sortResidents(residents).map((resident) => (
          <li key={resident.id} className="resident-row">
            <button
              type="button"
              className="resident-open"
              onClick={() => onSelect?.(resident.id)}
              aria-label={`Open ${resident.name}, room ${resident.room}, ${resident.status}`}
            >
              <span className="resident-identity">
                <span className="resident-name">{resident.name}</span>
                <span className="resident-room">Room {resident.room}</span>
              </span>
              <StatusChip status={resident.status} />
              <Sparkline scores={resident.scores} />
            </button>
          </li>
        ))}
      </ul>
    </>
  )
}
