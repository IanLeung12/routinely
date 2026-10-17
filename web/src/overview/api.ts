import { apiUrl } from '../config.ts'
import { mockResidents } from '../mock/residents.ts'
import type { ResidentSummary } from './types.ts'

/** Unit overview data (SPEC section 9). Falls back to the mock residents so the
 * dashboard still has something to show when the pipeline API isn't reachable. */
export async function fetchResidents(): Promise<ResidentSummary[]> {
  try {
    const response = await fetch(`${apiUrl}/residents`)
    if (!response.ok) {
      return mockResidents
    }
    return (await response.json()) as ResidentSummary[]
  } catch {
    return mockResidents
  }
}
