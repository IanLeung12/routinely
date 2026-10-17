/** The one chart on the landing page: the demo resident's fortnight of tea sessions.
 *
 * Mrs. K is the flagged resident the rest of the demo uses (`web/src/mock/`): a flat
 * two weeks, then two sessions above her own usual range on the same day, which is
 * what a flag takes (SPEC section 7: two or more sessions above the baseline threshold
 * within 24-48 h). Scores are on the same 0-1 scale as the unit overview's sparkline,
 * and end on the 0.78 her mock row ends on.
 *
 * The band is built here the way the pipeline builds a baseline - the mean of her own
 * earlier sessions, plus or minus two standard deviations - so the "usual range" on the
 * page can never drift away from the readings drawn against it. */

export type HeroReading = { time: number; value: number }

/** One morning session a day, then the morning and evening of the day she was flagged. */
export const HERO_READINGS: HeroReading[] = [
  { time: Date.UTC(2025, 11, 19, 8, 10), value: 0.11 },
  { time: Date.UTC(2025, 11, 20, 8, 5), value: 0.09 },
  { time: Date.UTC(2025, 11, 21, 8, 22), value: 0.13 },
  { time: Date.UTC(2025, 11, 22, 8, 2), value: 0.1 },
  { time: Date.UTC(2025, 11, 23, 8, 18), value: 0.16 },
  { time: Date.UTC(2025, 11, 24, 8, 6), value: 0.08 },
  { time: Date.UTC(2025, 11, 25, 8, 10), value: 0.12 },
  { time: Date.UTC(2025, 11, 26, 8, 22), value: 0.15 },
  { time: Date.UTC(2025, 11, 27, 8, 5), value: 0.1 },
  { time: Date.UTC(2025, 11, 28, 8, 18), value: 0.13 },
  { time: Date.UTC(2025, 11, 29, 8, 2), value: 0.12 },
  { time: Date.UTC(2025, 11, 30, 8, 12), value: 0.15 },
  { time: Date.UTC(2025, 11, 31, 8, 25), value: 0.14 },
  { time: Date.UTC(2026, 0, 1, 8, 12), value: 0.62 },
  { time: Date.UTC(2026, 0, 1, 18, 2), value: 0.78 },
]

/** The day the change was flagged; everything before it is her own normal. */
const FLAGGED_DAY = Date.UTC(2026, 0, 1)
const QUIET = HERO_READINGS.filter((reading) => reading.time < FLAGGED_DAY)
const MEAN = QUIET.reduce((total, reading) => total + reading.value, 0) / QUIET.length
const STD = Math.sqrt(
  QUIET.reduce((total, reading) => total + (reading.value - MEAN) ** 2, 0) / QUIET.length,
)

/** `routine_watch.change_detection.build_baseline`: her mean, plus or minus two
 * standard deviations of her own quiet fortnight. */
export const HERO_BASELINE = { mean: MEAN, threshold: 2 * STD }

/** A session over this is one of the two the flag is built from. */
export const HERO_FLAG_THRESHOLD = MEAN + 2 * STD

/** How many readings sit above it, said in words next to the chart. */
export const HERO_FLAGGED_COUNT = HERO_READINGS.filter(
  (reading) => reading.value > HERO_FLAG_THRESHOLD,
).length

/** How many days of her own the band is built from. */
export const HERO_BASELINE_DAYS = new Set(
  HERO_READINGS.map((reading) => new Date(reading.time).toISOString().slice(0, 10)),
).size

const DAY = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' })

/** Axis and tooltip dates, in UTC so the page reads the same in every time zone. */
export function formatDay(time: number): string {
  return DAY.format(new Date(time))
}

/** Scores are two decimals everywhere they are shown (axis, tag, usual range). */
export function formatScore(value: number): string {
  return value.toFixed(2)
}
