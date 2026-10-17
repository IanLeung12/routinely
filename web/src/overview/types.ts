import type { PatternUrgency } from '../contracts.ts'

/** Unit overview (SPEC section 9): one row per resident, same shape as T012's `GET /residents`. */
export type ResidentStatus = 'normal' | 'watch' | 'flagged'

export type TopPattern = {
  pattern_id: string
  name: string
  urgency: PatternUrgency
}

export type ResidentSummary = {
  id: string
  name: string
  room: string
  status: ResidentStatus
  top_pattern: TopPattern | null
  scores: { ts: string; score: number }[]
}
