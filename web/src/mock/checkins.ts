import type { CheckIn, CheckInResponse, CheckInStatus } from '../checkin/types.ts'

interface SeededCheckIn extends CheckIn {
  safetyPin: string
  duressPin: string
}

/** Nobody has an active check-in until an alert starts one (T450); the demo's people
 * (`mock/people.ts`) stay check-in-free by default so every other screen keeps
 * rendering the way it always has. `startMockCheckIn` is how a demo or a test puts
 * one on the board. */
const checkIns: SeededCheckIn[] = []

function toCheckIn(checkIn: SeededCheckIn): CheckIn {
  return { id: checkIn.id, person_id: checkIn.person_id, status: checkIn.status, deadline: checkIn.deadline }
}

export function mockActiveCheckIn(personId: string): CheckIn | null {
  const found = checkIns.find((checkIn) => checkIn.person_id === personId && checkIn.status === 'pending')
  return found ? toCheckIn(found) : null
}

/** Same response whichever PIN matched (SPEC section 12): the person never learns
 * which one it was. A PIN that matches neither leaves the check-in `pending`. */
export function mockRespond(checkInId: string, pin: string): CheckInResponse {
  const checkIn = checkIns.find((candidate) => candidate.id === checkInId)
  if (!checkIn) return { accepted: false }

  if (pin === checkIn.safetyPin) {
    checkIn.status = 'ok'
    return { accepted: true }
  }
  if (pin === checkIn.duressPin) {
    checkIn.status = 'duress'
    return { accepted: true }
  }
  return { accepted: false }
}

/** Starts a check-in the way `POST /checkins/demo` will (T450): for demos and for
 * exercising the fetch-fails-fall-back-to-mock path in `checkin/api.ts` end to end. */
export function startMockCheckIn(checkIn: {
  id: string
  person_id: string
  deadline: string
  safetyPin: string
  duressPin: string
  status?: CheckInStatus
}): CheckIn {
  const seeded: SeededCheckIn = { status: 'pending', ...checkIn }
  checkIns.push(seeded)
  return toCheckIn(seeded)
}
