import { apiUrl } from '../config.ts'
import type { ResidentDrift } from '../contracts.ts'
import { mockResidentDetail, mockResidentDrift } from '../mock/residentDetail.ts'
import type { Resident, ResidentFeedback } from './types.ts'

/** `GET /residents/{id}/drift`'s payload, generated from the pipeline's contracts and
 * re-exported here so the drift card still reads it from the client that fetches it. */
export type { ResidentDrift }

export async function fetchDrift(residentId: string): Promise<ResidentDrift | null> {
  try {
    const response = await fetch(`${apiUrl}/residents/${encodeURIComponent(residentId)}/drift`)
    if (response.ok) return await response.json() as ResidentDrift | null
  } catch { /* Keep the slow-drift demo available offline. */ }
  return mockResidentDrift(residentId)
}

/** Resident detail (SPEC section 9, screen 2). Falls back to the mock resident so the
 * screen still has something to show when the pipeline API isn't reachable, and
 * returns null when nobody — live or mock — has that id. */
export async function fetchResident(residentId: string): Promise<Resident | null> {
  try {
    const response = await fetch(`${apiUrl}/residents/${encodeURIComponent(residentId)}`)
    if (!response.ok) {
      return mockResidentDetail(residentId)
    }
    return (await response.json()) as Resident
  } catch {
    return mockResidentDetail(residentId)
  }
}

/** What this resident's nurses have answered and the pattern ranking it changed
 * (`GET /residents/{id}/feedback`, SPEC Nice to have 8).
 *
 * Throws when the API can't be reached: unlike the resident herself there is no mock
 * to stand in, and "nobody has answered yet" is a different thing to tell a nurse than
 * "we couldn't ask". A body missing a field is read as the empty one, so a resident the
 * API has nothing logged for still renders as an empty card. */
export async function fetchFeedbackHistory(residentId: string): Promise<ResidentFeedback> {
  const response = await fetch(`${apiUrl}/residents/${encodeURIComponent(residentId)}/feedback`)
  if (!response.ok) {
    throw new Error(`fetchFeedbackHistory failed: ${response.status}`)
  }
  const body = (await response.json()) as Partial<ResidentFeedback> | null
  return {
    answers: body?.answers ?? [],
    pattern_weights: body?.pattern_weights ?? {},
    pattern_names: body?.pattern_names ?? {},
  }
}
