/** Shift handoff (SPEC section 9): one row per resident, the shape of `GET /handoff`. */

/** What one resident did with the window the incoming nurse missed.
 *
 * `flags` counts the sessions in the window that scored above the resident's own
 * baseline, `pending_review` the alerts raised for them that nobody has given a
 * verdict on yet, and `trending` whether their error score is on a slow rise (which
 * takes weeks to show, so it is read over their whole history, not this window).
 * A session above baseline is evidence, not a flagged change: one bad session never
 * raises an alert on its own (SPEC section 7). */
export type HandoffResident = {
  resident_id: string
  name: string
  flags: number
  pending_review: number
  trending: boolean
}

export type Handoff = {
  window_hours: number
  residents: HandoffResident[]
  summary: string
}
