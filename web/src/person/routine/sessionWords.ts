import { ERROR_TYPE_VALUES } from '../../contracts.ts'
import type { ErrorType } from '../../contracts.ts'
import type { RoutineSession } from './types.ts'

/** The person's own words for a session (SPEC section 17). The supervisor's screens
 * name error types ('skipped step ×1'); the person reads what happened to them, so
 * every line here is a plain sentence about their routine and never a judgement
 * about them.
 *
 * Times are read in UTC like the rest of the dashboard (`resident/format.ts`), so a
 * session that happened in the evening says so on every machine. */

const WEEKDAYS = [
  'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday',
]

/** SPEC section 7.5's parts of the day: morning before noon, afternoon until 17:00,
 * evening from 17:00. The same buckets the pattern scorer uses, so "mostly in the
 * evening" in a note and "This evening" on a session mean the same thing. */
function partOfDay(hour: number): string {
  if (hour < 12) return 'morning'
  if (hour < 17) return 'afternoon'
  return 'evening'
}

/** What was different, singular and plural. Nothing here names an error type or a
 * condition: a missed step is a missed step. */
const DIFFERENCE: Record<ErrorType, [one: string, few: string]> = {
  omission: ['a step was missed', 'a few steps were missed'],
  sequence: ['a step came in a different order', 'a few steps came in a different order'],
  perseveration: ['a step was done twice', 'a few steps were done twice'],
  substitution: ['something else was picked up', 'a few things were picked up instead'],
  hesitation: ['there was a longer pause', 'there were a few longer pauses'],
  abandonment: ['a step was left unfinished', 'a few steps were left unfinished'],
}

/** How much longer than usual still counts as "about the same". A quarter again on a
 * three-minute routine is most of a minute: visible, not noise. */
const LONGER_THAN_USUAL = 1.25

function parse(ts: string): Date | null {
  const date = new Date(ts)
  return Number.isNaN(date.getTime()) ? null : date
}

/** Whole days between two instants, by UTC calendar day rather than by elapsed time. */
function daysBetween(earlier: Date, later: Date): number {
  const from = Date.UTC(earlier.getUTCFullYear(), earlier.getUTCMonth(), earlier.getUTCDate())
  const to = Date.UTC(later.getUTCFullYear(), later.getUTCMonth(), later.getUTCDate())
  return Math.round((to - from) / 86_400_000)
}

/** 'This evening', 'Yesterday morning', 'Monday afternoon'. Anything older than
 * yesterday is named by its weekday, which is as far back as a week of sessions
 * goes. Falls back to the weekday when there is no usable clock to compare with. */
export function whenLabel(startedAt: string, now: string): string {
  const at = parse(startedAt)
  if (at === null) return startedAt
  const part = partOfDay(at.getUTCHours())
  const today = parse(now)
  const days = today === null ? null : daysBetween(at, today)
  if (days === 0) return `This ${part}`
  if (days === 1) return `Yesterday ${part}`
  return `${WEEKDAYS[at.getUTCDay()]} ${part}`
}

/** 'Thu': the chart's axis label for one day. */
export function dayLabel(date: string): string {
  const at = parse(date)
  return at === null ? date : WEEKDAYS[at.getUTCDay()].slice(0, 3)
}

/** '5 min'. Rounded, because nobody reads their own morning in seconds. */
export function formatMinutes(seconds: number): string {
  return `${Math.max(1, Math.round(seconds / 60))} min`
}

/** 'a, b and c'. */
export function joinWords(parts: string[]): string {
  if (parts.length <= 1) return parts[0] ?? ''
  return `${parts.slice(0, -1).join(', ')} and ${parts[parts.length - 1]}`
}

function sentence(parts: string[]): string {
  const joined = joinWords(parts)
  return joined === '' ? '' : `${joined[0].toUpperCase()}${joined.slice(1)}.`
}

export type SessionWords = {
  /** 'This evening'. */
  when: string
  /** '5 min'. */
  took: string
  /** What looked different, as one sentence. Empty when nothing did. */
  different: string
  /** What went the way it usually does. Always says something. */
  smooth: string
}

/** One session, as the person reads it: when it was, how long it took, what looked
 * different and what went the way it usually does. */
export function describeSession(
  session: RoutineSession,
  usualMinutes: number,
  now: string,
): SessionWords {
  const differences = ERROR_TYPE_VALUES.flatMap((type) => {
    const count = session.errors[type] ?? 0
    if (count <= 0) return []
    const [one, few] = DIFFERENCE[type]
    return [count === 1 ? one : few]
  })

  const usualSeconds = usualMinutes * 60
  if (usualSeconds > 0 && session.duration_s >= usualSeconds * LONGER_THAN_USUAL) {
    differences.push(
      `it took about ${formatMinutes(session.duration_s)} instead of your usual ${formatMinutes(usualSeconds)}`,
    )
  }

  const fixed = session.self_corrected ?? 0
  const smooth: string[] = []
  if (fixed > 0) {
    smooth.push(fixed === 1 ? 'you put one step right yourself' : `you put ${fixed} steps right yourself`)
  }
  smooth.push(
    differences.length > 0
      ? 'the rest went the way it usually does'
      : 'the whole routine went the way it usually does',
  )

  return {
    when: whenLabel(session.started_at, now),
    took: formatMinutes(session.duration_s),
    different: sentence(differences),
    smooth: sentence(smooth),
  }
}
