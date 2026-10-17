import { describe, expect, it } from 'vitest'
import type { SessionErrors } from '../resident/types.ts'
import { mockResidentDetail } from './residentDetail.ts'

/** The offline stand-in for `GET /residents/{id}` has to carry the same baseline
 * fields the pipeline serves, or the live screen silently drops its "usually ~"
 * comparison when the API is unreachable (T230). */
describe('mockResidentDetail', () => {
  it("serves the resident's usual duration and error count inside the baseline", () => {
    const resident = mockResidentDetail('mrs-k')

    expect(resident?.baseline.usual_duration_s).toBeGreaterThan(0)
    expect(resident?.baseline.usual_errors).toBeGreaterThanOrEqual(0)
  })

  it('averages the usual values over the early days only, not the bad recent ones', () => {
    const resident = mockResidentDetail('mrs-k')
    const sessions = resident?.sessions ?? []
    const totalErrors = (errors: SessionErrors): number =>
      Object.values(errors).reduce<number>((total, count) => total + (count ?? 0), 0)
    const wholeHistory =
      sessions.reduce<number>((total, session) => total + totalErrors(session.errors), 0) /
      sessions.length

    expect(resident?.baseline.usual_errors).toBeLessThan(wholeHistory)
  })

  it('has no mock detail for a resident nobody knows', () => {
    expect(mockResidentDetail('nobody')).toBeNull()
  })
})
