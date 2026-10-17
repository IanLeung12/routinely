import { afterEach, describe, expect, it, vi } from 'vitest'
import { fetchPausedRooms, setRoomMonitoring } from './monitoringApi.ts'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('fetchPausedRooms', () => {
  it('returns paused_rooms from GET /monitoring', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ paused_rooms: ['101'] }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const result = await fetchPausedRooms()

    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/monitoring'))
    expect(result).toEqual(['101'])
  })

  it('throws when the response is not ok', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: false, status: 500, json: async () => ({}) }),
    )

    await expect(fetchPausedRooms()).rejects.toThrow()
  })

  it('throws on network error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))

    await expect(fetchPausedRooms()).rejects.toThrow()
  })
})

describe('setRoomMonitoring', () => {
  it('PUTs the room monitoring state', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ on: false }) })
    vi.stubGlobal('fetch', fetchMock)

    await setRoomMonitoring('101', false)

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/rooms/101/monitoring'),
      expect.objectContaining({
        method: 'PUT',
        body: JSON.stringify({ on: false }),
      }),
    )
  })

  it('throws when the response is not ok', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: false, status: 404, json: async () => ({}) }),
    )

    await expect(setRoomMonitoring('101', true)).rejects.toThrow()
  })

  it('throws on network error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))

    await expect(setRoomMonitoring('101', true)).rejects.toThrow()
  })
})
