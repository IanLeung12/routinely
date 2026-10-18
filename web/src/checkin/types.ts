/** The person's half of a safety check-in (Project KAZE, SPEC section 18): asked
 * after an alert, before anything reaches a supervisor (T450 owns the backend;
 * this is the shape it will answer with). The duress PIN must look exactly like
 * the safety PIN to the person (SPEC section 12), so nothing here ever says which
 * one matched - `CheckInResponse` is the same shape either way. */
export type CheckInStatus =
  | 'pending'
  | 'ok'
  | 'duress'
  | 'alarm'
  | 'escalated'
  | 'acknowledged'
  | 'resolved'

export interface CheckIn {
  id: string
  person_id: string
  status: CheckInStatus
  /** ISO timestamp the countdown ends at. Server-owned (T450): the client only reads it. */
  deadline: string
}

/** Same shape for the safety PIN and the duress PIN - only a wrong PIN differs. */
export interface CheckInResponse {
  accepted: boolean
}
