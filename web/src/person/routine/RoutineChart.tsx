import { Card } from '../../ui/Card.tsx'
import { EmptyState } from '../../ui/EmptyState.tsx'
import { SectionHeader } from '../../ui/SectionHeader.tsx'
import { BarChart } from '../../ui/charts/BarChart.tsx'
import { dayLabel } from './sessionWords.ts'
import type { PersonRoutine } from './types.ts'
import './routine.css'

/** The one chart on the person's screen (SPEC section 17): their usual against each
 * day of this week. Paired bars rather than the line chart, because this is a screen
 * someone opens on a phone and `ui/charts/LineChart.tsx` asks for 40rem before it
 * scrolls sideways; `BarChart` carries its own screen-reader table either way. */
export function RoutineChart({ routine }: { routine: PersonRoutine }) {
  const data = routine.days.map((day) => ({
    label: dayLabel(day.date),
    value: day.minutes,
    compare: day.usual_minutes,
  }))

  return (
    <Card>
      <SectionHeader
        title="Your usual and this week"
        caption="Minutes your routine took each day"
      />
      {data.length === 0 ? (
        <EmptyState message="No days to compare yet." />
      ) : (
        <>
          <BarChart
            data={data}
            ariaLabel="Minutes your routine took each day this week, next to your usual"
            callout={{ index: data.length - 1, label: 'Today' }}
          />
          <p className="routine-chart__legend">
            {`The filled bar is that day. The outlined bar beside it is your usual, about ${Math.round(routine.usual_minutes)} min.`}
          </p>
        </>
      )}
    </Card>
  )
}

export default RoutineChart
