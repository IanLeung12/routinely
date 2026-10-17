import { useEffect, useState } from 'react'
import { fetchPausedRooms } from '../about/monitoringApi.ts'
import { Button } from '../ui/Button.tsx'
import { EmptyState } from '../ui/EmptyState.tsx'
import { Loading } from '../ui/Loading.tsx'
import { StatusChip } from '../ui/StatusChip.tsx'
import { fetchResidents } from './api.ts'
import './overview.css'
import { loadOverviewPrefs, saveOverviewPrefs, type UnitFilter } from './overviewPrefs.ts'
import { ResidentSort, sortResidents, type SortMode } from './ResidentSort.tsx'
import { Sparkline } from './Sparkline.tsx'
import type { ResidentSummary } from './types.ts'

const FILTERS: { id: UnitFilter; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'flagged', label: 'Flagged' },
  { id: 'watch', label: 'Watch' },
]

function applyFilter(
  residents: ResidentSummary[],
  filter: UnitFilter,
  pausedRooms: string[],
): ResidentSummary[] {
  if (filter === 'all') return residents
  if (filter === 'paused') return residents.filter((resident) => pausedRooms.includes(resident.room))
  return residents.filter((resident) => resident.status === filter)
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
export function UnitOverview({
  onSelect,
  refreshKey,
}: {
  onSelect?: (residentId: string) => void
  /** Bump this (e.g. after a live session ends) to refetch residents. */
  refreshKey?: number | string
}) {
  const [residents, setResidents] = useState<ResidentSummary[] | null>(null)
  const [filter, setFilter] = useState<UnitFilter>(() => loadOverviewPrefs().filter)
  const [sortMode, setSortMode] = useState<SortMode>(() => loadOverviewPrefs().sort)
  const [pausedRooms, setPausedRooms] = useState<string[]>([])

  useEffect(() => {
    saveOverviewPrefs({ filter, sort: sortMode })
  }, [filter, sortMode])

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
  }, [refreshKey])

  useEffect(() => {
    let cancelled = false
    fetchPausedRooms()
      .then((rooms) => {
        if (!cancelled) {
          setPausedRooms(rooms ?? [])
        }
      })
      .catch(() => {
        if (!cancelled) {
          setPausedRooms([])
        }
      })
    return () => {
      cancelled = true
    }
  }, [refreshKey])

  if (residents === null) {
    return <Loading label="Loading residents…" />
  }

  if (residents.length === 0) {
    return <EmptyState message="No residents on this unit yet." />
  }

  const filtered = applyFilter(residents, filter, pausedRooms)

  return (
    <>
      <p role="status" className="resident-summary">
        {summarize(residents)}
      </p>
      <div className="unit-filter" role="group" aria-label="Filter residents">
        {FILTERS.map(({ id, label }) => (
          <Button
            key={id}
            variant="secondary"
            className="unit-filter__button"
            aria-pressed={filter === id}
            onClick={() => setFilter(id)}
          >
            {label}
          </Button>
        ))}
        <Button
          variant="secondary"
          className="unit-filter__button"
          aria-pressed={filter === 'paused'}
          onClick={() => setFilter('paused')}
        >
          {`Paused (${pausedRooms.length})`}
        </Button>
      </div>
      <ResidentSort mode={sortMode} onChange={setSortMode} />
      {filtered.length === 0 ? (
        <EmptyState
          message={
            filter === 'flagged'
              ? 'No residents flagged for review.'
              : filter === 'paused'
                ? 'No rooms paused.'
                : 'No residents to watch.'
          }
        />
      ) : (
        <ul className="resident-list">
          {sortResidents(filtered, sortMode).map((resident) => {
            const paused = pausedRooms.includes(resident.room)
            return (
            <li key={resident.id} className="resident-row">
              <button
                type="button"
                className="resident-open"
                onClick={() => onSelect?.(resident.id)}
                aria-label={`Open ${resident.name}, room ${resident.room}, ${resident.status}${paused ? ', Monitoring paused' : ''}`}
              >
                <span className="resident-identity">
                  <span className="resident-name">{resident.name}</span>
                  <span className="resident-room">Room {resident.room}</span>
                  {paused && <span className="resident-paused-chip">Monitoring paused</span>}
                </span>
                <span className="resident-status">
                  <StatusChip status={resident.status} />
                  {resident.top_pattern && (
                    <span className="resident-pattern">{resident.top_pattern.name}</span>
                  )}
                </span>
                <Sparkline scores={resident.scores} />
              </button>
            </li>
            )
          })}
        </ul>
      )}
    </>
  )
}
