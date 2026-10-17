import { afterEach, describe, expect, it, vi } from 'vitest'
import { fetchMonitoringHistory, fetchPausedRooms, setRoomMonitoring } from './monitoringApi.ts'

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

describe('fetchMonitoringHistory', () => {
  it('returns the room history from GET /rooms/{room}/monitoring/history', async () => {
    const history = [{ on: false, by: 'nurse-amy', at: '2026-10-17T09:10:00+00:00' }]
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ room: '101', history }) })
    vi.stubGlobal('fetch', fetchMock)

    const result = await fetchMonitoringHistory('101')

    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/rooms/101/monitoring/history'))
    expect(result).toEqual(history)
  })

  it('encodes the room in the path', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ history: [] }) })
    vi.stubGlobal('fetch', fetchMock)

    await fetchMonitoringHistory('wing a/101')

    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/rooms/wing%20a%2F101/monitoring/history'))
  })

  it('reads a body without a history as no changes', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) }))

    await expect(fetchMonitoringHistory('101')).resolves.toEqual([])
  })

  it('throws when the response is not ok', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: false, status: 404, json: async () => ({}) }),
    )

    await expect(fetchMonitoringHistory('101')).rejects.toThrow()
  })

  it('throws on network error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))

    await expect(fetchMonitoringHistory('101')).rejects.toThrow()
  })
})
