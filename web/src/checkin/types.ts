/** Mock-facing safety check-in shapes; PINs are write-only. */
export type CheckInStatus = 'pending' | 'ok' | 'alarm' | 'escalated' | 'acknowledged' | 'resolved'
export type ResolutionReason = 'false_alarm' | 'helped' | 'other'
export interface CheckInEvent {
  event: string
  at: string
  actor?: string
  next?: string
  reason?: ResolutionReason
}
export interface CheckIn {
  id: string
  person_id: string
  status: CheckInStatus
  created_at: string
  deadline: string
  duress?: boolean
  location?: string
  events: CheckInEvent[]
}
export interface SafetySupporter {
  id: string
  name: string
  location: boolean
  alert_details: boolean
  replay: boolean
}
export interface SafetySettingsData {
  checkin_window: number
  ack_window: number
  supporters: SafetySupporter[]
  safety_pin_set?: boolean
  duress_pin_set?: boolean
}
export type SafetySettingsInput = SafetySettingsData & { safety_pin?: string; duress_pin?: string }

/** What a person's own device sees for one of their check-ins (`person_view` in
 * `pipeline/.../checkin.py`): the question and their own countdown, nothing else -
 * a duress response already reads as `ok` here, which is the whole point of it
 * (SPEC section 12). `/checkins/active?person=` answers with these, wrapped as
 * `{ checkins: [...] }`; `seconds_left` is `null` once nothing is counting. */
export interface PersonCheckIn {
  checkin_id: string
  person_id: string
  state: CheckInStatus
  ask: string
  seconds_left: number | null
}
