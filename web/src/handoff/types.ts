/** Shift handoff (SPEC section 9): one row per resident, the shape of `GET /handoff`. */

/** What one resident did with the window the incoming nurse missed.
 *
 * `flags` counts the sessions in the window that scored above the resident's own
 * baseline, `pending_review` the alerts raised for them that nobody has given a
 * verdict on yet, and `trending` whether their error score is on a slow rise (which
 * takes weeks to show, so it is read over their whole history, not this window).
 * A session above baseline is evidence, not a flagged change: one bad session never
 * raises an alert on its own (SPEC section 7). `room` is where to find them, so a row
 * on screen or in the copied handoff says which door to walk to. */
export type HandoffResident = {
  resident_id: string
  name: string
  room: string
  flags: number
  pending_review: number
  trending: boolean
  monitoring_paused?: boolean
}

/** A room the monitoring store currently has paused (SPEC section 12): nobody was
 * watching, so the resident's quiet row means "not looked at", not "all quiet". */
export type PausedRoom = {
  room: string
  resident_id: string
  name: string
}

export type Handoff = {
  window_hours: number
  residents: HandoffResident[]
  /** Missing on an older API that predates pause tracking: treat as `[]`. */
  paused?: PausedRoom[]
  summary: string
}
