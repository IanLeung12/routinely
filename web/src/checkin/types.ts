/** Mock-facing safety check-in shapes; PINs are write-only. */
export type CheckInStatus = 'pending' | 'ok' | 'alarm' | 'escalated' | 'acknowledged' | 'resolved'
export type ResolutionReason = 'false_alarm' | 'helped' | 'other'

/** One transition in a check-in's log, as `checkin.py`'s `CheckinEvent` spells it:
 * `actor` is always present (`person`, `server`, or a supporter's id) and `detail`
 * carries whatever that event needs - a supporter's id, a resolution reason, nothing. */
export interface CheckInEvent {
  at: string
  event: string
  actor: string
  state: CheckInStatus
  detail?: string | null
}

/** One check-in as a supervisor may see it (`supporter_view` in
 * `pipeline/.../checkin.py`): only what the person shared with *this* supporter.
 * `location`, `alert_id`/`events` and `replays_url` are absent entirely - not
 * blanked - when that supporter wasn't given them. */
export interface CheckIn {
  checkin_id: string
  person_id: string
  person_name: string
  state: CheckInStatus
  ask: string
  duress: boolean
  silent: boolean
  started_at: string
  deadline: string | null
  seconds_left: number | null
  for_supporter: string
  supporter: string | null
  notified: string[]
  acknowledged_by: string | null
  resolved_by: string | null
  resolved_reason: ResolutionReason | null
  device_online: boolean
  location?: string
  location_simulated?: boolean
  alert_id?: string | null
  events?: CheckInEvent[]
  replays_url?: string
}

export interface SafetySupporter {
  id: string
  name: string
  relationship: string
  share: { location: boolean; alert_details: boolean; replay: boolean }
}

export interface SafetySettingsData {
  person_id: string
  name: string
  checkin_window_s: number
  ack_window_s: number
  location: string
  location_simulated: boolean
  supporters: SafetySupporter[]
  safety_pin_set: boolean
  duress_pin_set: boolean
}

/** What `PUT /people/{id}/safety` (`SafetyIn`, `extra="forbid"`) accepts: every field
 * optional, and nothing the GET answers with that isn't also a valid thing to set -
 * `person_id`, `location_simulated`, `safety_pin_set`, `duress_pin_set` would 422. */
export type SafetySettingsInput = Partial<
  Pick<SafetySettingsData, 'checkin_window_s' | 'ack_window_s' | 'location' | 'supporters'>
> & { safety_pin?: string; duress_pin?: string }

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
