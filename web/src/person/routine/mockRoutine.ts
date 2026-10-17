import type { PersonRoutine, RoutineDay, RoutineSession } from './types.ts'

/** The demo's own routine (SPEC section 17). There is no per-person route yet, so
 * this is what "My routine" draws: Sam's week of making tea, their own usual, and
 * the two patterns the last two evenings are consistent with.
 *
 * It lives beside the screen rather than in `src/mock/` because it is this screen's
 * stand-in for a route, not shared demo data; `routine/api.ts` is the seam a real
 * per-person API drops into.
 *
 * Stamped on the demo's own clock (1 January 2026, the day the rest of the demo
 * data ends on), so "this evening" means the same thing every time it is opened
 * instead of drifting with the wall clock. */

/** How long making tea usually takes Sam, in minutes: their own normal, not a target. */
const USUAL_MINUTES = 3

/** Sam's clock for this payload. */
export const DEMO_NOW = '2026-01-01T20:10:00+00:00'

type Row = {
  ts: string
  duration_s: number
  errors?: RoutineSession['errors']
  self_corrected?: number
}

/** A flat week, then two evenings that run long while the mornings stay the same:
 * the evidence behind "took a little longer, mostly in the evening". Oldest first;
 * `sessions` below is the same list newest first, the way the screen reads it. */
const ROWS: Row[] = [
  { ts: '2025-12-26T08:05:00+00:00', duration_s: 176 },
  { ts: '2025-12-26T18:10:00+00:00', duration_s: 188 },
  { ts: '2025-12-27T08:20:00+00:00', duration_s: 184 },
  { ts: '2025-12-28T08:02:00+00:00', duration_s: 171, self_corrected: 1 },
  { ts: '2025-12-28T18:05:00+00:00', duration_s: 195 },
  { ts: '2025-12-29T08:12:00+00:00', duration_s: 179 },
  { ts: '2025-12-30T08:08:00+00:00', duration_s: 182 },
  { ts: '2025-12-30T18:15:00+00:00', duration_s: 214, errors: { hesitation: 1 } },
  { ts: '2025-12-31T08:06:00+00:00', duration_s: 186 },
  { ts: '2025-12-31T18:25:00+00:00', duration_s: 268, errors: { hesitation: 1 } },
  { ts: '2026-01-01T08:10:00+00:00', duration_s: 190 },
  {
    ts: '2026-01-01T18:40:00+00:00',
    duration_s: 318,
    errors: { hesitation: 2, omission: 1 },
  },
]

function sessionsFrom(rows: Row[]): RoutineSession[] {
  return rows.map((row, index) => ({
    session_id: `sam-${String(index + 1).padStart(2, '0')}`,
    started_at: row.ts,
    task: 'Making tea',
    duration_s: row.duration_s,
    errors: row.errors ?? {},
    ...(row.self_corrected === undefined ? {} : { self_corrected: row.self_corrected }),
  }))
}

/** One point per day the person had a routine, from the sessions themselves, so the
 * chart and the session list can never drift apart. A day is the average of its
 * sessions: a morning and an evening are the same routine twice, not two routines. */
function daysFrom(sessions: RoutineSession[], usualMinutes: number): RoutineDay[] {
  const byDate = new Map<string, number[]>()
  for (const session of sessions) {
    const date = session.started_at.slice(0, 10)
    byDate.set(date, [...(byDate.get(date) ?? []), session.duration_s])
  }
  return [...byDate.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, durations]) => ({
      date,
      minutes: Number(
        (durations.reduce((total, seconds) => total + seconds, 0) / durations.length / 60)
          .toFixed(1),
      ),
      usual_minutes: usualMinutes,
    }))
}

const oldestFirst = sessionsFrom(ROWS)

/** Sam's routine, as the mock API serves it. */
export const mockPersonRoutine: PersonRoutine = {
  person_id: 'sam',
  now: DEMO_NOW,
  status: 'flagged',
  usual_minutes: USUAL_MINUTES,
  days: daysFrom(oldestFirst, USUAL_MINUTES),
  sessions: [...oldestFirst].reverse(),
  patterns: [
    {
      pattern_id: 'motor_slowing',
      name: 'Motor slowing / medication effect',
      confidence: 0.61,
      urgency: 'next_round',
      evidence: [
        'step durations up to 4.2 min a session from 3.0',
        'few out-of-order steps',
      ],
      checks: ['medication_review'],
    },
    {
      pattern_id: 'evening_worsening',
      name: 'Evening-only worsening (sundowning pattern)',
      confidence: 0.48,
      urgency: 'routine',
      evidence: ['both affected sessions started after 17:00', 'mornings unchanged'],
      checks: ['sleep, lighting, routine, pain, evening medication'],
    },
  ],
}

/** The same week with nothing to mention: what a person sees when their routine
 * looks like their usual, which is most weeks. */
export const mockSteadyRoutine: PersonRoutine = {
  ...mockPersonRoutine,
  status: 'normal',
  days: mockPersonRoutine.days.map((day) => ({ ...day, minutes: USUAL_MINUTES })),
  sessions: mockPersonRoutine.sessions.map((session) => ({
    ...session,
    duration_s: Math.min(session.duration_s, USUAL_MINUTES * 60 + 10),
    errors: {},
  })),
  patterns: [],
}
