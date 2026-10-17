import { Button } from '../ui/Button.tsx'
import type { ResidentStatus, ResidentSummary } from './types.ts'

export type SortMode = 'default' | 'recent'

const STATUS_ORDER: Record<ResidentStatus, number> = { flagged: 0, watch: 1, normal: 2 }

const SORT_MODES: { id: SortMode; label: string }[] = [
  { id: 'default', label: 'Default order' },
  { id: 'recent', label: 'Most recent change first' },
]

/** A resident's most recent session time, the newest point in `scores` (oldest-first).
 * The resident summary has no dedicated "latest flag/alert time" field, so this is the
 * closest existing signal to "most recent change" (see T318). */
function latestChangeTs(resident: ResidentSummary): number {
  const latest = resident.scores[resident.scores.length - 1]
  if (!latest) return -Infinity
  const parsed = Date.parse(latest.ts)
  return Number.isNaN(parsed) ? -Infinity : parsed
}

/** Pure sort for the unit overview list (SPEC section 9). `default` keeps today's
 * flagged-first ordering; `recent` orders by each resident's latest session time,
 * newest first, falling back to the default status order when a resident has no
 * scores at all. Ties keep their original relative order (stable sort). */
export function sortResidents(residents: ResidentSummary[], mode: SortMode): ResidentSummary[] {
  const sorted = [...residents]
  if (mode === 'recent') {
    return sorted.sort((a, b) => latestChangeTs(b) - latestChangeTs(a))
  }
  return sorted.sort((a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status])
}

export function ResidentSort({
  mode,
  onChange,
}: {
  mode: SortMode
  onChange: (mode: SortMode) => void
}) {
  return (
    <div className="unit-sort" role="group" aria-label="Sort residents">
      {SORT_MODES.map(({ id, label }) => (
        <Button
          key={id}
          variant="secondary"
          className="unit-sort__button"
          aria-pressed={mode === id}
          onClick={() => onChange(id)}
        >
          {label}
        </Button>
      ))}
    </div>
  )
}
