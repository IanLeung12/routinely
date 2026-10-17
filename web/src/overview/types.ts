import type { ResidentSummary as GeneratedResidentSummary } from '../contracts.ts'

/** Unit overview (SPEC section 9): one row per resident, same shape as T012's `GET /residents`. */
export type { ResidentStatus, TopPattern } from '../contracts.ts'

export type ResidentSummary = GeneratedResidentSummary & {
  /** Who consented to monitoring and when (SPEC §12). Absent on an older API or mock. */
  consent?: { given_by: string; on: string }
}
