import { useState } from 'react'
import { EmptyState } from '../ui/EmptyState.tsx'
import { LineChart } from '../ui/charts/LineChart.tsx'
import { RangeSelector } from '../ui/charts/RangeSelector.tsx'
import type { ChartRange } from '../ui/charts/RangeSelector.tsx'
import { formatDay, formatScore } from './format.ts'
import type { Baseline, ScorePoint } from './types.ts'

const RANGE_DAYS: Record<ChartRange, number> = { '7D': 7, '14D': 14, '30D': 30 }
const DAY_MS = 86_400_000

function plural(count: number): string {
  return count === 1 ? '1 session' : `${count} sessions`
}

/** Score per session against this resident's own baseline (SPEC section 9, screen 2), on
 * the shared `LineChart`: the band is their usual range, the end-of-line tag is the
 * latest score, and sessions above the flag threshold are called out on the line and in
 * the summary text. `RangeSelector` windows the series from the newest session, not
 * wall clock, so a resident whose demo data sits in the past still has something to show. */
export function BaselineChart({ scores, baseline }: { scores: ScorePoint[]; baseline: Baseline }) {
  const [range, setRange] = useState<ChartRange>('14D')

  if (scores.length === 0) {
    return <EmptyState message="No scored sessions yet." />
  }

  const latestTs = Math.max(...scores.map((point) => Date.parse(point.ts)))
  const cutoff = latestTs - RANGE_DAYS[range] * DAY_MS
  const windowed = scores.filter((point) => Date.parse(point.ts) >= cutoff)
  const points = windowed.map((point) => ({ time: Date.parse(point.ts), value: point.score }))
  const latest = windowed[windowed.length - 1]
  const above = windowed.filter((point) => point.score > baseline.threshold).length
  const summary =
    `${plural(windowed.length)} against their baseline. Latest score ${formatScore(latest.score)}, ` +
    `flag threshold ${formatScore(baseline.threshold)}. ${plural(above)} above it: two within 48 h ` +
    'flag a change for review.'

  return (
    <div className="baseline-chart">
      <RangeSelector value={range} onChange={setRange} label="Baseline chart time range" />
      <LineChart
        label="Baseline"
        summary={summary}
        data={points}
        baseline={{ mean: baseline.mean, threshold: baseline.threshold }}
        flagThreshold={baseline.threshold}
        formatValue={formatScore}
        formatTime={(time) => formatDay(new Date(time).toISOString())}
      />
    </div>
  )
}
