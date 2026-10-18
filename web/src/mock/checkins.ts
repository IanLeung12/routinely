import type { CheckInStatus, PersonCheckIn } from '../checkin/types.ts'

interface SeededCheckIn extends PersonCheckIn {
  safetyPin: string
  duressPin: string
}

/** Nobody has an active check-in until an alert starts one (T450); the demo's
 * people (`mock/people.ts`) stay check-in-free by default so every other screen
 * keeps rendering the way it always has. `startMockCheckIn` is how a demo or a
 * test puts one on the board; `resetMockCheckIns` clears it between tests. */
let checkIns: SeededCheckIn[] = []

function toPersonCheckIn(checkIn: SeededCheckIn): PersonCheckIn {
  return {
    checkin_id: checkIn.checkin_id,
    person_id: checkIn.person_id,
    state: checkIn.state,
    ask: checkIn.ask,
    seconds_left: checkIn.seconds_left,
  }
}

export function mockActiveCheckIn(personId: string): PersonCheckIn | null {
  const found = checkIns.find(
    (checkIn) => checkIn.person_id === personId && checkIn.state !== 'ok' && checkIn.state !== 'resolved',
  )
  return found ? toPersonCheckIn(found) : null
}

/** Same response whichever PIN matched (SPEC section 12): the person never learns
 * which one it was. A PIN that matches neither leaves the check-in `pending`. */
export function mockRespond(checkinId: string, pin: string): { accepted: boolean } {
  const checkIn = checkIns.find((candidate) => candidate.checkin_id === checkinId)
  if (!checkIn) return { accepted: false }

  if (pin === checkIn.safetyPin || pin === checkIn.duressPin) {
    checkIn.state = 'ok'
    return { accepted: true }
  }
  return { accepted: false }
}

/** Starts a check-in the way `POST /checkins/demo` will (T450): for demos and for
 * exercising the fetch-fails-fall-back-to-mock path in `checkin/api.ts` end to end. */
export function startMockCheckIn(checkIn: {
  checkin_id: string
  person_id: string
  ask: string
  seconds_left: number | null
  safetyPin: string
  duressPin: string
  state?: CheckInStatus
}): PersonCheckIn {
  const seeded: SeededCheckIn = { state: 'pending', ...checkIn }
  checkIns.push(seeded)
  return toPersonCheckIn(seeded)
}

export function resetMockCheckIns(): void {
  checkIns = []
}
