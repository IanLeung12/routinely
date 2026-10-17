import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiUrl } from '../config.ts'
import { mockResidentDetail, mockResidentDrift } from '../mock/residentDetail.ts'
import { fetchDrift, fetchResident } from './api.ts'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('fetchDrift', () => {
  it('returns the JSON body on a 200', async () => {
    const drift = { resident_id: 'mr-chen', slope_per_day: 0.9, days: 7, trending: true }
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => drift })
    vi.stubGlobal('fetch', fetch)

    expect(await fetchDrift('mr-chen')).toEqual(drift)
    expect(fetch).toHaveBeenCalledWith(`${apiUrl}/residents/mr-chen/drift`)
  })

  it('returns the mock drift on a non-OK response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }))
    expect(await fetchDrift('mr-chen')).toEqual(mockResidentDrift('mr-chen'))
  })

  it('returns the mock drift when fetch rejects', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    expect(await fetchDrift('mr-chen')).toEqual(mockResidentDrift('mr-chen'))
  })

  it('URL-encodes the resident id in the request', async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => null })
    vi.stubGlobal('fetch', fetch)

    await fetchDrift('mrs/k')
    expect(fetch).toHaveBeenCalledWith(`${apiUrl}/residents/mrs%2Fk/drift`)
  })
})

describe('fetchResident', () => {
  it('returns the JSON body on a 200', async () => {
    const resident = mockResidentDetail('mrs-k')
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => resident })
    vi.stubGlobal('fetch', fetch)

    expect(await fetchResident('mrs-k')).toEqual(resident)
    expect(fetch).toHaveBeenCalledWith(`${apiUrl}/residents/mrs-k`)
  })

  it('returns the mock resident on a non-OK response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }))
    expect(await fetchResident('mrs-k')).toEqual(mockResidentDetail('mrs-k'))
  })

  it('returns the mock resident when fetch rejects', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    expect(await fetchResident('mrs-k')).toEqual(mockResidentDetail('mrs-k'))
  })

  it('returns null for an unknown id when offline', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    expect(await fetchResident('unknown')).toBeNull()
  })

  it('URL-encodes the resident id in the request', async () => {
    const fetch = vi.fn().mockRejectedValue(new Error('offline'))
    vi.stubGlobal('fetch', fetch)

    await fetchResident('mrs/k')
    expect(fetch).toHaveBeenCalledWith(`${apiUrl}/residents/mrs%2Fk`)
  })
})
