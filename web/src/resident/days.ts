import { utcDate } from './format.ts'
import type { ScorePoint } from './types.ts'

const DAY_MS = 86_400_000

/** One cell per day from the first scored session to the last, carrying that day's
 * worst session score (what a nurse cares about) and `null` for days with no session,
 * which is the shape `HeatCalendar` takes. */
export function dailyScores(scores: ScorePoint[]): { date: string; score: number | null }[] {
  const worstPerDay = new Map<string, number>()
  for (const point of scores) {
    const date = utcDate(point.ts)
    if (date !== null) {
      worstPerDay.set(date, Math.max(worstPerDay.get(date) ?? 0, point.score))
    }
  }

  const dates = [...worstPerDay.keys()].sort()
  if (dates.length === 0) {
    return []
  }

  const days: { date: string; score: number | null }[] = []
  const last = Date.parse(`${dates[dates.length - 1]}T00:00:00Z`)
  for (let day = Date.parse(`${dates[0]}T00:00:00Z`); day <= last; day += DAY_MS) {
    const date = new Date(day).toISOString().slice(0, 10)
    days.push({ date, score: worstPerDay.get(date) ?? null })
  }
  return days
}
