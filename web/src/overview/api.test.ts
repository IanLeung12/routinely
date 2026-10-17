import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiUrl } from '../config.ts'
import { mockResidents } from '../mock/residents.ts'
import { fetchResidents } from './api.ts'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('fetchResidents', () => {
  it('returns the JSON body on a 200', async () => {
    const residents = [mockResidents[0]]
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => residents })
    vi.stubGlobal('fetch', fetch)

    expect(await fetchResidents()).toEqual(residents)
    expect(fetch).toHaveBeenCalledWith(`${apiUrl}/residents`)
  })

  it('returns the mock residents on a non-OK response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }))
    expect(await fetchResidents()).toBe(mockResidents)
  })

  it('returns the mock residents when fetch rejects', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    expect(await fetchResidents()).toBe(mockResidents)
  })
})
