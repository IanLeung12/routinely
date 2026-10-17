import { afterEach, describe, expect, it, vi } from 'vitest'
import { fetchHandoff } from './api.ts'
import { mockHandoff } from './mockHandoff.ts'

afterEach(() => {
  vi.unstubAllGlobals()
})

const served = {
  window_hours: 24,
  residents: [{ resident_id: 'mrs-k', name: 'Mrs. K', flags: 2, pending_review: 1, trending: false }],
  summary: 'Flagged for review: two sessions in the last day.',
}

describe('fetchHandoff', () => {
  it('returns what the pipeline served', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => served }))

    expect(await fetchHandoff(24)).toEqual({ handoff: served, offline: false })
  })

  it('asks for the window it was given', async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => served })
    vi.stubGlobal('fetch', fetch)

    await fetchHandoff(8)

    expect(fetch.mock.calls[0][0]).toContain('/handoff?hours=8')
  })

  it('falls back to the mock handoff, flagged offline, when the API is unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network down')))

    expect(await fetchHandoff(12)).toEqual({ handoff: mockHandoff, offline: true })
  })

  it('falls back when the API answers with an error status', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }))

    expect(await fetchHandoff(12)).toEqual({ handoff: mockHandoff, offline: true })
  })
})
