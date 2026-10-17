import { formatScore } from '../resident/format.ts'
import { MicroBars } from '../ui/charts/MicroBars.tsx'

/** Compact error-score history, retaining the overview's existing input shape. */
export function Sparkline({ scores }: { scores: { ts: string; score: number }[] }) {
  const values = scores.map((point) => point.score)
  const latest = values[values.length - 1]
  const min = Math.min(...values)
  const max = Math.max(...values)
  const trend = latest > values[0] ? 'rising' : latest < values[0] ? 'falling' : min === max ? 'flat' : 'varying'

  const label = scores.length === 0
    ? 'No error score history yet'
    : `Error score over the last ${values.length} sessions, latest ${formatScore(latest)}, ${trend}`

  return (
    <span role="img" aria-label={label}>
      {/* Scores have no status metadata; retain the existing text alternative. */}
      <span aria-hidden="true">
        <MicroBars
          days={scores.map(({ ts, score }) => ({ date: ts, score, status: 'normal' }))}
          ariaLabel={label}
        />
      </span>
    </span>
  )
}
