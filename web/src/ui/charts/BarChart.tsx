import { Pill } from '../Pill.tsx'
import { EmptyState } from '../EmptyState.tsx'

export type BarChartProps = {
  data: { label: string; value: number; compare?: number }[]
  ariaLabel: string
  highlight?: number
  callout?: { index: number; label: string }
}

/** Paired measurements share a zero-inclusive scale, including negative values. */
export function BarChart({ data, ariaLabel, highlight, callout }: BarChartProps) {
  const values = data.flatMap(({ value, compare }) => compare === undefined ? [value] : [value, compare])
  const finite = values.filter(Number.isFinite)
  const min = Math.min(0, ...finite)
  const max = Math.max(0, ...finite)
  const span = max - min || 1
  const y = (value: number) => 60 + (max - (Number.isFinite(value) ? value : 0)) / span * 140
  const baseline = y(0)
  const slot = 480 / Math.max(1, data.length)
  const width = Math.min(14, slot / 4)
  const hasCompare = data.some(item => item.compare !== undefined)

  return (
    <div className="bar-chart" style={{ position: 'relative' }}>
      <svg role="img" aria-label={ariaLabel} viewBox="0 0 520 240" style={{ width: '100%', height: 'auto', overflow: 'visible' }}>
        <line x1={20} x2={500} y1={baseline} y2={baseline} stroke="var(--chart-grid)" />
        {data.map((item, index) => {
          const center = 20 + slot * (index + 0.5)
          const x = item.compare === undefined ? center - width / 2 : center - width - 2
          const selected = index === (highlight ?? callout?.index)
          return (
            <g key={index}>
              <rect className="bar-chart__bar" x={x} y={Math.min(y(item.value), baseline)} width={width} height={Math.abs(y(item.value) - baseline)} rx={width / 2} fill={selected ? 'var(--chart-comparison)' : 'var(--chart-line)'}>
                <title>{`${item.label}: ${item.value}${selected ? ' (highlighted)' : ''}`}</title>
              </rect>
              {item.compare !== undefined && (
                <rect className="bar-chart__compare" x={center + 2} y={Math.min(y(item.compare), baseline)} width={width} height={Math.abs(y(item.compare) - baseline)} rx={width / 2} fill="var(--chart-baseline)" stroke="var(--chart-comparison)">
                  <title>{`${item.label} usual: ${item.compare}`}</title>
                </rect>
              )}
              <text x={center} y={224} textAnchor="middle" fill="var(--text-muted)" style={{ fontSize: 'var(--text-xs)', fontFamily: 'var(--font-sans)' }}>{item.label}</text>
              {callout?.index === index && (
                <foreignObject x={Math.max(0, Math.min(360, center - 80))} y={Math.min(y(item.value), baseline) - 42} width={160} height={36}>
                  <div style={{ textAlign: 'center' }}><Pill>{callout.label}</Pill></div>
                </foreignObject>
              )}
            </g>
          )
        })}
      </svg>
      {data.length === 0 && <EmptyState message="No data yet" />}
      <table style={{ position: 'absolute', width: 1, height: 1, padding: 0, border: 0, overflow: 'hidden', clipPath: 'inset(50%)', whiteSpace: 'nowrap' }}>
        <caption>{ariaLabel}</caption>
        <thead><tr><th scope="col">Label</th><th scope="col">Value</th>{hasCompare && <th scope="col">Usual</th>}</tr></thead>
        <tbody>{data.map((item, index) => <tr key={index}><th scope="row">{item.label}</th><td>{item.value}{index === highlight ? ' (highlighted)' : ''}{callout?.index === index ? ` (${callout.label})` : ''}</td>{hasCompare && <td>{item.compare ?? '—'}</td>}</tr>)}</tbody>
      </table>
    </div>
  )
}

export default BarChart
