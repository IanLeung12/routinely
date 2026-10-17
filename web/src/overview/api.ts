import { apiUrl } from '../config.ts'
import { mockResidents } from '../mock/residents.ts'
import type { ResidentSummary } from './types.ts'

export type ResidentsSource = 'api' | 'demo'

/** Unit overview data (SPEC section 9). Falls back to the mock residents so the
 * dashboard still has something to show when the pipeline API isn't reachable;
 * `source` tells the caller whether that fallback kicked in. */
export async function fetchResidentsWithSource(): Promise<{
  residents: ResidentSummary[]
  source: ResidentsSource
}> {
  try {
    const response = await fetch(`${apiUrl}/residents`)
    if (!response.ok) {
      return { residents: mockResidents, source: 'demo' }
    }
    return { residents: (await response.json()) as ResidentSummary[], source: 'api' }
  } catch {
    return { residents: mockResidents, source: 'demo' }
  }
}

export async function fetchResidents(): Promise<ResidentSummary[]> {
  return (await fetchResidentsWithSource()).residents
}
