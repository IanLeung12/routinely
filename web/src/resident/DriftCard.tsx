import { Card } from '../ui/Card.tsx'

export function DriftCard({ slopePerDay, days, trending, minDays = 7 }: {
  slopePerDay: number
  days: number
  trending: boolean
  minDays?: number
}) {
  const state = days < minDays ? 'insufficient' : trending ? 'trending' : 'stable'

  return (
    <Card>
      <section data-state={state} aria-label="Slow drift" style={{ color: 'var(--text)' }}>
        <h3>Slow drift</h3>
        <p style={{ color: state === 'trending' ? 'var(--error-amber-text)' : 'var(--muted)' }}>
          {state === 'insufficient'
            ? `Not enough history yet (${days} of ${minDays} days)`
            : state === 'trending'
              ? `Error score rising about +${slopePerDay.toFixed(2)} per day over ${days} days. Flagged for review.`
              : `No slow drift over ${days} days`}
        </p>
      </section>
    </Card>
  )
}
