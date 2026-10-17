import type { CSSProperties } from 'react'
import { EmptyState } from '../ui/EmptyState.tsx'
import { formatScore } from './format.ts'
import './heatCalendar.css'

type Day = { date: string; score: number | null }

const WEEKDAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

export default function HeatCalendar({ days }: { days: Day[] }) {
  if (days.length === 0) {
    return <EmptyState message="No sessions yet, so nothing to show on the calendar." />
  }

  const orderedDays = [...days].sort((a, b) => a.date.localeCompare(b.date))
  const maximum = Math.max(1, ...days.map(({ score }) => score ?? 0))
  const firstDate = new Date(`${orderedDays[0].date}T00:00:00Z`)
  const firstMonday = firstDate.getTime() - ((firstDate.getUTCDay() + 6) % 7) * 86400000

  return (
    <div>
      <div className="heat-grid-scroll">
      <div role="grid" aria-label="Daily error scores (Monday first)" className="heat-grid">
        {WEEKDAY_LABELS.map((label, index) => (
          <div
            key={label}
            role="columnheader"
            className="heat-grid__header"
            style={{ '--col': index + 1 } as CSSProperties}
          >
            {label}
          </div>
        ))}
        {orderedDays.map(({ date, score }) => {
          const weekday = (new Date(`${date}T00:00:00Z`).getUTCDay() + 6) % 7
          const label = `${date}: ${score === null ? 'no session' : `score ${formatScore(score)}`}`
          const intensity = Math.round((Math.max(0, score ?? 0) / maximum) * 100)
          const col = weekday + 1
          const row = Math.floor((Date.parse(`${date}T00:00:00Z`) - firstMonday) / 604800000) + 2
          const className = [
            'heat-cell',
            score === null ? 'heat-cell--none' : 'heat-cell--scored',
            score !== null && score >= 4 ? 'heat-cell--light-text' : '',
          ].filter(Boolean).join(' ')

          return (
            <div
              key={date}
              role="gridcell"
              title={label}
              aria-label={label}
              className={className}
              style={{ '--col': col, '--row': row, '--heat': `${intensity}%` } as CSSProperties}
            >
              {Number(date.slice(-2))}
            </div>
          )
        })}
      </div>
      </div>
      <p className="heat-legend">
        <span aria-hidden="true" className="heat-swatch heat-swatch--low" />{' '}
        Lighter = fewer errors ·{' '}
        <span aria-hidden="true" className="heat-swatch heat-swatch--high" />{' '}
        Darker = more errors ·{' '}
        <span aria-hidden="true" className="heat-swatch heat-swatch--none" />{' '}
        Grey = no session
      </p>
    </div>
  )
}
