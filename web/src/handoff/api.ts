import { apiUrl } from '../config.ts'
import { mockHandoff } from './mockHandoff.ts'
import type { Handoff } from './types.ts'

/** The handoff, and whether it is the local mock rather than the pipeline's answer.
 * The screen says so when it is: a nurse reading "no change flagged" has to know
 * whether that is the unit or a dead connection. */
export type HandoffResult = { handoff: Handoff; offline: boolean }

/** Shift handoff data (`GET /handoff?hours=`). Falls back to the mock handoff so the
 * screen still works offline, with `offline: true` so it can be labelled. */
export async function fetchHandoff(hours: number): Promise<HandoffResult> {
  try {
    const response = await fetch(`${apiUrl}/handoff?hours=${encodeURIComponent(hours)}`)
    if (response.ok) {
      return { handoff: (await response.json()) as Handoff, offline: false }
    }
  } catch { /* Keep the screen usable while offline. */ }
  return { handoff: mockHandoff, offline: true }
}
