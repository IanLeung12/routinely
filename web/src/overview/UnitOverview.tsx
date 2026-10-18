import { useEffect, useState } from 'react'
import { fetchPausedRooms } from '../about/monitoringApi.ts'
import { formatScore } from '../resident/format.ts'
import { Card } from '../ui/Card.tsx'
import { EmptyState } from '../ui/EmptyState.tsx'
import { Loading } from '../ui/Loading.tsx'
import { Pill, type PillTone } from '../ui/Pill.tsx'
import { SegmentedControl } from '../ui/SegmentedControl.tsx'
import { StatusChip } from '../ui/StatusChip.tsx'
import { fetchResidentsWithSource, type ResidentsSource } from './api.ts'
import './overview.css'
import { loadOverviewPrefs, saveOverviewPrefs, type UnitFilter } from './overviewPrefs.ts'
import { ResidentSort, sortResidents, type SortMode } from './ResidentSort.tsx'
import { Sparkline } from './Sparkline.tsx'
import type { ResidentStatus, ResidentSummary } from './types.ts'

const FILTERS: { id: UnitFilter; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'flagged', label: 'Flagged' },
  { id: 'watch', label: 'Watch' },
  { id: 'paused', label: 'Paused' },
]

const STATUS_TONE: Record<ResidentStatus, PillTone> = {
  normal: 'positive',
  watch: 'watch',
  flagged: 'negative',
}

function countForFilter(
  filterId: UnitFilter,
  residents: ResidentSummary[],
  pausedRooms: string[],
): number {
  if (filterId === 'all') return residents.length
  if (filterId === 'paused') return pausedRooms.length
  return residents.filter((resident) => resident.status === filterId).length
}

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

/** The latest score and, when there's a prior session to compare it with, which
 * way it moved — the same arrow-carries-the-direction rule as every other `Pill`. */
function latestScore(resident: ResidentSummary): { value: number; direction?: 'up' | 'down' } | null {
  const scores = resident.scores
  if (scores.length === 0) return null
  const latest = scores[scores.length - 1].score
  const previous = scores.length > 1 ? scores[scores.length - 2].score : latest
  if (latest === previous) return { value: latest }
  return { value: latest, direction: latest > previous ? 'up' : 'down' }
}

/** Screen 1 (SPEC section 9): resident list with a status chip and an error-score
 * trend, flagged residents first. Visual first; a nurse should read it in 10s.
 * The whole row opens that resident's detail. Without `onSelect` the list is read-only.
 *
 * Generalised for "People I support" (SPEC section 17): a supervisor of several people
 * who isn't a whole care-home unit still uses this screen, scoped to `personIds` so it
 * never shows someone outside their list. The care-home case passes the whole unit, so
 * its behaviour is unchanged. */
export function UnitOverview({
  onSelect,
  refreshKey,
  personIds,
}: {
  onSelect?: (residentId: string) => void
  /** Bump this (e.g. after a live session ends) to refetch residents. */
  refreshKey?: number | string
  /** Scopes the list to these people. Omit to show everyone the fetch returns (the
   * care-home unit, today). */
  personIds?: string[]
}) {
  const [fetched, setFetched] = useState<ResidentSummary[] | null>(null)
  const [source, setSource] = useState<ResidentsSource>('api')
  const [filter, setFilter] = useState<UnitFilter>(() => loadOverviewPrefs().filter)
  const [sortMode, setSortMode] = useState<SortMode>(() => loadOverviewPrefs().sort)
  const [pausedRooms, setPausedRooms] = useState<string[]>([])

  useEffect(() => {
    saveOverviewPrefs({ filter, sort: sortMode })
  }, [filter, sortMode])

  useEffect(() => {
    let cancelled = false
    fetchResidentsWithSource().then((result) => {
      if (!cancelled) {
        setFetched(result.residents)
        setSource(result.source)
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

  if (fetched === null) {
    return <Loading label="Loading residents…" />
  }

  const residents = personIds ? fetched.filter((resident) => personIds.includes(resident.id)) : fetched

  if (residents.length === 0) {
    return <EmptyState message="No residents on this unit yet." />
  }

  const filtered = applyFilter(residents, filter, pausedRooms)
  const filterOptions = FILTERS.map(({ id, label }) => ({
    value: id,
    label: `${label} (${countForFilter(id, residents, pausedRooms)})`,
  }))

  return (
    <Card flush className="unit-overview">
      <div className="unit-overview__head">
        <p role="status" className="resident-summary">
          {summarize(residents)}
        </p>
        <div className="unit-overview__controls">
          <SegmentedControl
            label="Filter residents"
            options={filterOptions}
            value={filter}
            onChange={setFilter}
          />
          <ResidentSort mode={sortMode} onChange={setSortMode} />
        </div>
      </div>
      {source === 'demo' && (
        <p role="status" className="overview__demo-notice">
          Showing demo residents: the Routinely service isn't reachable.
        </p>
      )}
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
            const score = latestScore(resident)
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
                  <span className="resident-trend">
                    <Sparkline scores={resident.scores} />
                    {score && (
                      <Pill
                        tone={STATUS_TONE[resident.status]}
                        direction={score.direction}
                        className="resident-score"
                      >
                        {formatScore(score.value)}
                      </Pill>
                    )}
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </Card>
  )
}
