import { Card } from '../ui/Card.tsx'
import { LineChart } from '../ui/charts/LineChart.tsx'
import './driftCard.css'

/** Slow drift against this resident's own history (SPEC section 9): a fitted line, not
 * a measurement, so it is always drawn dotted on the shared `LineChart` (never a solid
 * line, per `docs/DESIGN.md`) scaled to the fitted daily slope over the window. There is
 * no fitted line to draw yet with less than `minDays` of history. */
export function DriftCard({ slopePerDay, days, trending, minDays = 7 }: {
  slopePerDay: number
  days: number
  trending: boolean
  minDays?: number
}) {
  const state = days < minDays ? 'insufficient' : trending ? 'trending' : 'stable'
  const trend = state === 'insufficient' ? [] : [{ time: 0, value: 0 }, { time: days, value: slopePerDay * days }]

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
        {trend.length > 0 && (
          <div className="drift-card__trend">
            <LineChart
              label="Slow drift trend"
              summary={`Fitted trend line over ${days} days, dotted because it is a fitted line, not a measurement.`}
              data={trend}
              formatValue={(value) => `${value >= 0 ? '+' : ''}${value.toFixed(2)}`}
              formatTime={(time) => (time === 0 ? 'First day' : `Day ${time}`)}
            />
          </div>
        )}
      </section>
    </Card>
  )
}
