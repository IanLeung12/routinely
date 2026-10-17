import { formatScore } from '../resident/format.ts'

const WIDTH = 120
const HEIGHT = 32
const PADDING = 2

/** Plain-SVG sparkline of a resident's error score over time (SPEC section 9). No
 * chart library: this is a handful of points, not a reason to pull one in. */
export function Sparkline({ scores }: { scores: { ts: string; score: number }[] }) {
  if (scores.length === 0) {
    return <svg width={WIDTH} height={HEIGHT} role="img" aria-label="No error score history yet" />
  }

  const values = scores.map((point) => point.score)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const latest = values[values.length - 1]
  const trend = latest > values[0] ? 'rising' : latest < values[0] ? 'falling' : min === max ? 'flat' : 'varying'

  const points = values.map((value, index) => {
    const x =
      values.length === 1
        ? WIDTH / 2
        : PADDING + (index / (values.length - 1)) * (WIDTH - 2 * PADDING)
    const y = HEIGHT - PADDING - ((value - min) / range) * (HEIGHT - 2 * PADDING)
    return `${x},${y}`
  })

  return (
    <svg
      width={WIDTH}
      height={HEIGHT}
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      role="img"
      aria-label={`Error score over the last ${values.length} sessions, latest ${formatScore(latest)}, ${trend}`}
    >
      <polyline points={points.join(' ')} fill="none" stroke="currentColor" strokeWidth={2} />
    </svg>
  )
}
