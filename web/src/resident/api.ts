import { apiUrl } from '../config.ts'
import { mockResidentDetail } from '../mock/residentDetail.ts'
import type { Resident } from './types.ts'

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
