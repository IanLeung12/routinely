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
