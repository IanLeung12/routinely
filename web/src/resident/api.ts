import { apiUrl } from '../config.ts'
import { mockResidentDetail, mockResidentDrift } from '../mock/residentDetail.ts'
import type { Resident } from './types.ts'

export type ResidentDrift = {
  resident_id: string
  slope_per_day: number
  days: number
  trending: boolean
}

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
