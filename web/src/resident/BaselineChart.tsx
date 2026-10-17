import { formatDay, formatScore } from './format.ts'
import type { Baseline, ScorePoint } from './types.ts'

const WIDTH = 560
const HEIGHT = 190
const PAD = { top: 14, right: 104, bottom: 26, left: 34 }
const PLOT_W = WIDTH - PAD.left - PAD.right
const PLOT_H = HEIGHT - PAD.top - PAD.bottom

function plural(count: number): string {
  return count === 1 ? '1 session' : `${count} sessions`
}

/** Score per session against this resident's own baseline (SPEC section 9, screen 2).
 * Plain SVG: a dozen points is not a reason to pull in a chart library. The newest
 * session — today's, in the demo — is drawn large, and the dashed line is the score a
 * session has to pass to count towards a flag. */
export function BaselineChart({
  scores,
  baseline,
}: {
  scores: ScorePoint[]
  baseline: Baseline
}) {
  if (scores.length === 0) {
    return <p className="muted">No scored sessions yet.</p>
  }

  const top = Math.max(baseline.threshold, ...scores.map((point) => point.score)) * 1.15 || 1
  const x = (index: number) =>
    scores.length === 1 ? PAD.left + PLOT_W / 2 : PAD.left + (index / (scores.length - 1)) * PLOT_W
  const y = (score: number) => PAD.top + PLOT_H - (Math.max(score, 0) / top) * PLOT_H

  const latest = scores[scores.length - 1]
  const above = scores.filter((point) => point.score > baseline.threshold).length
  const label =
    `Baseline chart: ${plural(scores.length)}, latest score ${formatScore(latest.score)}, ` +
    `flag threshold ${formatScore(baseline.threshold)}, ${plural(above)} above it`

  const meanY = y(baseline.mean)
  const thresholdY = y(baseline.threshold)
  // With a big spike the two lines sit close together; drop the lower label rather
  // than print the two on top of each other.
  const showMeanLabel = meanY - thresholdY >= 14

  return (
    <div className="baseline-chart">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label={label}>
        <line
          className="chart-axis"
          x1={PAD.left}
          y1={y(0)}
          x2={PAD.left + PLOT_W}
          y2={y(0)}
        />
        <text className="chart-tick" x={PAD.left - 6} y={y(0) + 4} textAnchor="end">
          0
        </text>

        <line
          className="chart-mean"
          x1={PAD.left}
          y1={meanY}
          x2={PAD.left + PLOT_W}
          y2={meanY}
        />
        {showMeanLabel && (
          <text className="chart-tick" x={PAD.left + PLOT_W + 8} y={meanY + 4}>
            their normal {formatScore(baseline.mean)}
          </text>
        )}

        <line
          className="chart-threshold"
          x1={PAD.left}
          y1={thresholdY}
          x2={PAD.left + PLOT_W}
          y2={thresholdY}
        />
        <text
          className="chart-tick chart-tick--threshold"
          x={PAD.left + PLOT_W + 8}
          y={thresholdY + 4}
        >
          threshold {formatScore(baseline.threshold)}
        </text>

        <polyline
          className="chart-line"
          points={scores.map((point, index) => `${x(index)},${y(point.score)}`).join(' ')}
        />

        {scores.slice(0, -1).map((point, index) => (
          <circle
            key={point.ts}
            className={
              point.score > baseline.threshold ? 'chart-point chart-point--above' : 'chart-point'
            }
            cx={x(index)}
            cy={y(point.score)}
            r={3}
          >
            <title>{`${formatDay(point.ts)}: ${formatScore(point.score)}`}</title>
          </circle>
        ))}
        <circle
          className={
            latest.score > baseline.threshold
              ? 'chart-point chart-point--latest chart-point--above'
              : 'chart-point chart-point--latest'
          }
          cx={x(scores.length - 1)}
          cy={y(latest.score)}
          r={6}
        >
          <title>{`${formatDay(latest.ts)}: ${formatScore(latest.score)}`}</title>
        </circle>

        <text className="chart-tick" x={PAD.left} y={HEIGHT - 6}>
          {formatDay(scores[0].ts)}
        </text>
        <text className="chart-tick" x={PAD.left + PLOT_W} y={HEIGHT - 6} textAnchor="end">
          {formatDay(latest.ts)}
        </text>
      </svg>

      <p className="chart-legend">
        <span className="chart-legend__latest">Latest session {formatScore(latest.score)}</span>
        <span className="chart-legend__threshold">
          Two sessions above {formatScore(baseline.threshold)} within 48 h flag a change for review
        </span>
      </p>
    </div>
  )
}
