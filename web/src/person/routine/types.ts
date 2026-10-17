import type { ErrorType, PatternMatch } from '../../contracts.ts'

/** What someone watching their own routine sees (SPEC section 17): their own
 * sessions, their own usual, and the patterns behind a change - nothing about
 * anybody else, and no unit-wide data.
 *
 * Field names are snake_case like the rest of the payloads in `contracts.ts`:
 * this stands in for a per-person route that doesn't exist yet, so the shape is
 * the one a real one would serve (`routine/api.ts`). */

/** How a session went, in the counts the pipeline already produces (SPEC section 7).
 * The person never reads these names; `sessionWords.ts` turns them into sentences. */
export type RoutineErrors = Partial<Record<ErrorType, number>>

/** One attempt at one everyday task. */
export type RoutineSession = {
  session_id: string
  /** When it started (wall clock, UTC like the rest of the dashboard). */
  started_at: string
  /** The task in the person's own words, e.g. 'Making tea'. */
  task: string
  duration_s: number
  /** What usually happened in this session, as error counts. Empty means it all
   * went the way it usually does. */
  errors: RoutineErrors
  /** Slips they put right themselves: worth seeing, never counted as a mistake. */
  self_corrected?: number
}

/** One day of the week behind the chart: what their routine took that day against
 * what it usually takes them. Days with no session are simply absent. */
export type RoutineDay = {
  /** 'YYYY-MM-DD' in UTC. */
  date: string
  /** Minutes the day's sessions took on average. */
  minutes: number
  /** Minutes the same routine usually takes them. */
  usual_minutes: number
}

/** Everything the person's home screen draws. */
export type PersonRoutine = {
  person_id: string
  /** The clock the rest of this payload is read against, so "this evening" means
   * the same thing every time the demo is opened (`mockRoutine.ts`). */
  now: string
  /** Their own week against their own usual. Never a judgement about them. */
  status: 'normal' | 'watch' | 'flagged'
  /** How long this routine usually takes them, in minutes. */
  usual_minutes: number
  /** Oldest day first, so the chart reads left to right. */
  days: RoutineDay[]
  /** Newest session first. */
  sessions: RoutineSession[]
  /** The patterns a flagged change is consistent with, best first (SPEC section
   * 7.5), rephrased for the person by `person/personNotes.ts`. Empty when there
   * is nothing to mention - an empty list is a real answer. */
  patterns: PatternMatch[]
}
