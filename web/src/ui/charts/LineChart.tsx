import { useId, useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'
import { Pill } from '../Pill'
import { linearScale, niceTicks, timeScale, timeTicks } from './scale'
import './charts.css'

export type LineChartPoint = { time: number | Date; value: number }
export type LineChartProps = {
  label: string
  /** Human-readable interpretation, displayed even when there are no readings. */
  summary: string
  data: readonly LineChartPoint[]
  comparison?: readonly LineChartPoint[]
  comparisonLabel?: string
  baseline?: { mean: number; threshold: number }
  flagThreshold?: number
  formatValue?: (value: number) => string
  formatTime?: (time: number) => string
}

const WIDTH = 640
const HEIGHT = 240
const LEFT = 52
const RIGHT = 530
const TOP = 20
const BOTTOM = 204
const defaultTime = (time: number) => new Date(time).toISOString().slice(0, 10)
const defaultValue = (value: number) => String(Number(value.toFixed(2)))
const validPoints = (data: readonly LineChartPoint[]) => data
  .filter((point) => Number.isFinite(new Date(+point.time).getTime()) && Number.isFinite(point.value))
  .slice().sort((a, b) => +a.time - +b.time)

/** Two-series time chart. Input is sorted without mutation; invalid readings are omitted.
 * Arrow keys move through readings; Home/End jump to the first/latest reading. */
export function LineChart({ label, summary, data, comparison = [], comparisonLabel = 'Their usual',
  baseline, flagThreshold, formatValue = defaultValue, formatTime = defaultTime }: LineChartProps) {
  const id = useId()
  const [active, setActive] = useState<number | null>(null)
  const [focused, setFocused] = useState<number | null>(null)
  const pointRefs = useRef<(SVGCircleElement | null)[]>([])
  const points = validPoints(data)
  const usual = validPoints(comparison)
  const band = baseline && Number.isFinite(baseline.mean) && Number.isFinite(baseline.threshold)
    && baseline.threshold >= 0 ? baseline : undefined
  const latest = points.at(-1)
  const all = [...points, ...usual]
  const times = all.map((point) => +point.time)
  const values = all.map((point) => point.value)
  if (band) values.push(band.mean - band.threshold, band.mean + band.threshold)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const padding = (max - min) * 0.1 || Math.max(Math.abs(min) * 0.1, 1)
  const domain: [number, number] = [min - padding, max + padding]
  const timeDomain: [number, number] = [Math.min(...times), Math.max(...times)]
  const x = timeScale(timeDomain, [LEFT, RIGHT])
  const y = linearScale(domain, [BOTTOM, TOP])
  const path = (series: readonly LineChartPoint[]) => series.map((point, i) =>
    `${i ? 'L' : 'M'}${x(point.time)},${y(point.value)}`).join(' ')
  const focusIndex = focused === null ? null : Math.min(focused, points.length - 1)
  const selectedIndex = focusIndex ?? active
  const selected = selectedIndex === null ? undefined : points[selectedIndex]
  const flagged = (point: LineChartPoint) => flagThreshold !== undefined && point.value > flagThreshold
  const pointLabel = (point: LineChartPoint) => `${formatTime(+point.time)}: ${formatValue(point.value)}${flagged(point) ? ', change flagged for review' : ''}`
  function navigate(event: KeyboardEvent<SVGCircleElement>, index: number) {
    const next = event.key === 'ArrowRight' ? Math.min(index + 1, points.length - 1)
      : event.key === 'ArrowLeft' ? Math.max(index - 1, 0)
        : event.key === 'Home' ? 0 : event.key === 'End' ? points.length - 1 : null
    if (next === null) return
    event.preventDefault()
    pointRefs.current[next]?.focus()
  }

  return (
    <figure className="line-chart" aria-label={label} aria-describedby={`${id}-summary`}>
      <figcaption id={`${id}-summary`} className="line-chart__summary">{summary}</figcaption>
      {!latest ? <p className="line-chart__summary">No readings available.</p> : <>
        <p id={`${id}-instructions`} className="line-chart__summary">
          Use Left and Right arrow keys to explore readings; Home and End jump to the first and latest.
        </p>
        <div className="line-chart__viewport">
          <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="group" aria-label={`${label} readings`}>
            <g aria-hidden="true">
              {niceTicks(domain).map((tick) => <g key={tick}>
                <line className="line-chart__grid" x1={LEFT} x2={RIGHT} y1={y(tick)} y2={y(tick)} />
                <text className="line-chart__axis" x={LEFT - 8} y={y(tick)} textAnchor="end" dominantBaseline="middle">{formatValue(tick)}</text>
              </g>)}
              {timeTicks(timeDomain).map((tick) => <text className="line-chart__axis" key={tick} x={x(tick)} y={BOTTOM + 24} textAnchor="middle">{formatTime(tick)}</text>)}
              {band && <g>
                <rect className="line-chart__band" x={LEFT} width={RIGHT - LEFT} y={y(band.mean + band.threshold)} height={y(band.mean - band.threshold) - y(band.mean + band.threshold)} />
                <line className="line-chart__mean" x1={LEFT} x2={RIGHT} y1={y(band.mean)} y2={y(band.mean)} />
              </g>}
              {usual.length > 0 && <path className="line-chart__comparison" d={path(usual)} />}
              <path className="line-chart__line" d={path(points)} />
              {selected && <line className="line-chart__crosshair" x1={x(selected.time)} x2={x(selected.time)} y1={TOP} y2={BOTTOM} />}
              {points.filter((point) => point === latest || flagged(point)).map((point, index) =>
                <circle key={index} className={`line-chart__marker${flagged(point) ? ' line-chart__marker--flagged' : ''}`} cx={x(point.time)} cy={y(point.value)} r={3} />)}
              <foreignObject x={x(latest.time) + 8} y={y(latest.value) - 14} width={100} height={32}>
                <Pill tone={flagged(latest) ? 'negative' : 'neutral'}>{formatValue(latest.value)}</Pill>
              </foreignObject>
            </g>
            {points.map((point, index) => <circle
              key={`${+point.time}-${index}`} ref={(node) => { pointRefs.current[index] = node }}
              className="line-chart__target" cx={x(point.time)} cy={y(point.value)} r={10}
              role="button" aria-label={pointLabel(point)} aria-describedby={`${id}-instructions`}
              tabIndex={index === (focusIndex ?? 0) ? 0 : -1}
              onFocus={() => setFocused(index)} onBlur={() => setFocused(null)}
              onClick={(event) => event.currentTarget.focus()}
              onMouseEnter={() => setActive(index)} onMouseLeave={() => setActive(null)}
              onKeyDown={(event) => navigate(event, index)}
            />)}
          </svg>
        </div>
        <p className="line-chart__summary">Latest: {pointLabel(latest)}</p>
        {band && <p className="line-chart__summary">Usual range: {formatValue(band.mean - band.threshold)}–{formatValue(band.mean + band.threshold)} (mean {formatValue(band.mean)}).</p>}
        {usual.length > 0 && <p className="line-chart__summary">Dotted comparison: {comparisonLabel}.</p>}
        {points.some(flagged) && <p className="line-chart__summary">{points.filter(flagged).length} {points.filter(flagged).length === 1 ? 'reading' : 'readings'} above the flag threshold: change flagged for review.</p>}
        {selected && <div role="tooltip" className="line-chart__tooltip">{pointLabel(selected)}</div>}
      </>}
    </figure>
  )
}
