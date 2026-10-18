import { apiUrl } from '../config.ts'
import { mockActiveCheckIn, mockRespond } from '../mock/checkins.ts'
import type { CheckIn, CheckInResponse } from './types.ts'

/** Where the person's check-in card reads and answers an active check-in from
 * (T450, SPEC section 18). There is no real backend yet, so this falls back to
 * the in-memory mock exactly like `alert/api.ts` and `replays/api.ts` do; the
 * screen only calls the functions at the bottom, so T450's API swaps in by
 * implementing `CheckInApi` and calling `setCheckInApi` - no screen changes. */
export interface CheckInApi {
  activeCheckIn(personId: string): Promise<CheckIn | null>
  respond(checkInId: string, pin: string): Promise<CheckInResponse>
}

const browserCheckInApi: CheckInApi = {
  async activeCheckIn(personId) {
    try {
      const response = await fetch(`${apiUrl}/checkins/active?person=${encodeURIComponent(personId)}`)
      if (response.ok) return await response.json() as CheckIn | null
    } catch { /* Fall back to the offline mock while the API is unreachable. */ }
    return mockActiveCheckIn(personId)
  },

  async respond(checkInId, pin) {
    try {
      const response = await fetch(`${apiUrl}/checkins/${encodeURIComponent(checkInId)}/respond`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pin }),
      })
      if (response.ok) return await response.json() as CheckInResponse
      // A wrong PIN is a normal 401 (T450), not a failed connection: the
      // countdown keeps running, so this never falls through to the mock.
      if (response.status === 401) return { accepted: false }
    } catch { /* Fall back to the offline mock while the API is unreachable. */ }
    return mockRespond(checkInId, pin)
  },
}

let api: CheckInApi = browserCheckInApi

/** Replaces the mock-backed implementation with T450's real one (pass null to go
 * back); also how tests make the PIN flow deterministic. */
export function setCheckInApi(next: CheckInApi | null): void {
  api = next ?? browserCheckInApi
}

export function activeCheckIn(personId: string): Promise<CheckIn | null> {
  return api.activeCheckIn(personId)
}

export function respondToCheckIn(checkInId: string, pin: string): Promise<CheckInResponse> {
  return api.respond(checkInId, pin)
}
