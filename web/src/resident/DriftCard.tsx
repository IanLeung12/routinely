import { Card } from '../ui/Card.tsx'
import './driftCard.css'

export function DriftCard({ slopePerDay, days, trending, minDays = 7 }: {
  slopePerDay: number
  days: number
  trending: boolean
  minDays?: number
}) {
  const state = days < minDays ? 'insufficient' : trending ? 'trending' : 'stable'

  return (
    <Card>
      <section className="drift-card" data-state={state} aria-label="Slow drift">
        <h3>Slow drift</h3>
        <p className="drift-card__summary">
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
