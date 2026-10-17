import './microBars.css'

/** What a day can say about itself (SPEC section 9), the same three words as
 * `StatusChip`. The chart kit keeps its own copy so it doesn't depend on a
 * screen's types. */
export type MicroBarStatus = 'normal' | 'watch' | 'flagged'

/** One day of the strip. `score` is that day's error score, or `null` when there
 * was nothing usable to score (no session, or the capture was unclear). */
export type MicroBarDay = {
  date: string
  score: number | null
  status: MicroBarStatus
}

/* Geometry. A fixed strip, sized to sit inside a list row: adding days makes the
   ticks thinner, never the row taller. */
const WIDTH = 84
const HEIGHT = 20
const GAP = 2
const MAX_TICK_WIDTH = 4
/** A day that was scored is never shorter than this, so a score of 0 still reads
 * as "there was a session", not as a day with no reading. */
const MIN_TICK_HEIGHT = 3
/** A day with no reading: a faint hairline that holds the day's place. */
const HAIRLINE_HEIGHT = 1
/** Heights are relative to the busiest day on screen, but never to less than one
 * error: a quiet fortnight of 0.1s stays a row of stubs instead of being
 * stretched into a mountain range. */
const MIN_DOMAIN = 1

/** Two decimals is plenty for an 84px strip, and keeps the SVG readable. */
const round = (value: number) => Math.round(value * 100) / 100

/** The score to draw for a day, or `null` if there is nothing to draw: a missing
 * score, a broken one (NaN), and a negative one all mean "no reading". */
function reading(day: MicroBarDay): number | null {
  if (day.score === null || !Number.isFinite(day.score)) {
    return null
  }
  return Math.max(0, day.score)
}

/** What a screen reader hears instead of the ticks: how many days, then only
 * what is worth saying about them ("14 days, 2 flagged"). A chart says its
 * meaning in words too, so colour is never the only signal (docs/DESIGN.md). */
export function summariseDays(days: MicroBarDay[]): string {
  if (days.length === 0) {
    return 'no days yet'
  }

  const count = (status: MicroBarStatus) => days.filter((day) => day.status === status).length
  const flagged = count('flagged')
  const watch = count('watch')
  const missing = days.filter((day) => reading(day) === null).length

  const parts = [`${days.length} ${days.length === 1 ? 'day' : 'days'}`]
  if (flagged > 0) {
    parts.push(`${flagged} flagged`)
  }
  if (watch > 0) {
    parts.push(`${watch} to watch`)
  }
  if (missing > 0) {
    parts.push(`${missing} with no reading`)
  }
  if (parts.length === 1) {
    parts.push('all within their usual range')
  }
  return parts.join(', ')
}

/** A day-by-day tick strip for a dense list row (docs/DESIGN.md; Fey's sector
 * rows): one thin vertical tick per day, its height that day's score and its
 * colour that day's status. A day with no reading keeps its slot as a faint
 * hairline, so a gap in the data never looks like a good day. Fixed 84×20, so
 * every row of a list lines up and the strip can be read without a number. */
export function MicroBars({
  days,
  ariaLabel,
  className,
}: {
  days: MicroBarDay[]
  ariaLabel: string
  className?: string
}) {
  const scores = days.map(reading)
  const tallest = Math.max(MIN_DOMAIN, ...scores.filter((score): score is number => score !== null))
  const step = WIDTH / Math.max(days.length, 1)
  const tickWidth = Math.min(MAX_TICK_WIDTH, Math.max(1, step - GAP))

  return (
    <svg
      className={['micro-bars', className].filter(Boolean).join(' ')}
      width={WIDTH}
      height={HEIGHT}
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      role="img"
      aria-label={`${ariaLabel}: ${summariseDays(days)}`}
    >
      {days.map((day, index) => {
        const score = scores[index]
        const height =
          score === null
            ? HAIRLINE_HEIGHT
            : round(MIN_TICK_HEIGHT + (score / tallest) * (HEIGHT - MIN_TICK_HEIGHT))
        return (
          <rect
            key={`${day.date}-${index}`}
            className={`micro-bars__tick micro-bars__tick--${score === null ? 'missing' : day.status}`}
            data-date={day.date}
            x={round(index * step + (step - tickWidth) / 2)}
            y={round(HEIGHT - height)}
            width={round(tickWidth)}
            height={height}
            rx={round(Math.min(tickWidth, height) / 2)}
          />
        )
      })}
    </svg>
  )
}

export default MicroBars
