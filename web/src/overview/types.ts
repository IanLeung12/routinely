/** Unit overview (SPEC section 9): one row per resident, same shape as T012's `GET /residents`. */
export type ResidentStatus = 'normal' | 'watch' | 'flagged'

export type ResidentSummary = {
  id: string
  name: string
  room: string
  status: ResidentStatus
  scores: { ts: string; score: number }[]
}
