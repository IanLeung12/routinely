type Day = { date: string; score: number | null }

export default function HeatCalendar({ days }: { days: Day[] }) {
  if (days.length === 0) return null

  const orderedDays = [...days].sort((a, b) => a.date.localeCompare(b.date))
  const maximum = Math.max(1, ...days.map(({ score }) => score ?? 0))
  const firstDate = new Date(`${orderedDays[0].date}T00:00:00Z`)
  const firstMonday = firstDate.getTime() - ((firstDate.getUTCDay() + 6) % 7) * 86400000

  return (
    <div
      role="grid"
      aria-label="Daily error scores (Monday first)"
      style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 4 }}
    >
      {orderedDays.map(({ date, score }) => {
        const weekday = (new Date(`${date}T00:00:00Z`).getUTCDay() + 6) % 7
        const label = `${date}: ${score === null ? 'no session' : `score ${score}`}`
        const intensity = Math.round((Math.max(0, score ?? 0) / maximum) * 100)

        return (
          <div
            key={date}
            role="gridcell"
            title={label}
            aria-label={label}
            style={{
              gridColumn: weekday + 1,
              gridRow: Math.floor((Date.parse(`${date}T00:00:00Z`) - firstMonday) / 604800000) + 1,
              backgroundColor: score === null
                ? 'var(--error-grey-bg)'
                : `color-mix(in srgb, var(--error-red-bg) ${intensity}%, var(--panel))`,
              color: score !== null && score >= 4 ? 'var(--text)' : 'var(--error-grey-text)',
              padding: 8,
            }}
          >
            {Number(date.slice(-2))}
          </div>
        )
      })}
    </div>
  )
}
