import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiUrl } from '../config.ts'
import { mockAlerts } from '../mock/alerts.ts'
import { mockReplays } from '../mock/replay.ts'
import { fetchReplay } from './api.ts'

const MRS_K = mockAlerts[0]

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('fetchReplay', () => {
  it('fetches the session and normal replay windows for the first error, from the API', async () => {
    const today = [{ ...mockReplays['mrs-k-change-1'].today[0], seq: 99 }]
    const normal = [{ ...mockReplays['mrs-k-change-1'].normal[0], seq: 98 }]
    const fetch = vi.fn((url: string) => {
      if (url.includes('/sessions/')) return Promise.resolve({ ok: true, json: async () => ({ frames: today }) })
      return Promise.resolve({ ok: true, json: async () => ({ frames: normal }) })
    })
    vi.stubGlobal('fetch', fetch)

    const error = MRS_K.errors[0]
    expect(await fetchReplay(MRS_K)).toEqual({ today, normal, t_start: error.t_start })
    expect(fetch).toHaveBeenCalledTimes(2)
    expect(fetch).toHaveBeenCalledWith(
      `${apiUrl}/sessions/${encodeURIComponent(error.session_id)}/replay?t_start=${error.t_start}&t_end=${error.t_end}`,
    )
    expect(fetch).toHaveBeenCalledWith(
      `${apiUrl}/residents/${encodeURIComponent(MRS_K.resident_id)}/normal_replay?t_start=${error.t_start}&t_end=${error.t_end}`,
    )
  })

  it.each(['rejection', 'non-ok'])('falls back to the mock replay on %s', async failure => {
    const fetch = vi.fn(() => {
      return failure === 'rejection'
        ? Promise.reject(new Error('offline'))
        : Promise.resolve({ ok: false, status: 500 })
    })
    vi.stubGlobal('fetch', fetch)

    expect(await fetchReplay(MRS_K)).toEqual({
      ...mockReplays['mrs-k-change-1'],
      t_start: MRS_K.errors[0].t_start,
    })
  })

  it('returns null without fetching when the alert has no errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    expect(await fetchReplay({ ...MRS_K, errors: [] })).toBeNull()
    expect(fetch).not.toHaveBeenCalled()
  })

  it('returns null when a known alert has no mock replay and the API is unreachable', async () => {
    const alert = { ...MRS_K, alert_id: 'no-replay-alert' }
    const fetch = vi.fn().mockRejectedValue(new Error('offline'))
    vi.stubGlobal('fetch', fetch)

    expect(await fetchReplay(alert)).toBeNull()
  })
})
