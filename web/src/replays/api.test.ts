import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiUrl } from '../config.ts'
import { mockReplays } from '../mock/replays.ts'
import { deleteReplay, fetchPersonReplays, fetchReplay } from './api.ts'

afterEach(() => vi.unstubAllGlobals())

describe('replays API', () => {
  it('fetches a person library and full replay from the API with encoded ids', async () => {
    const library = { person_id: 'person/id', replays: [], normal: null }
    const replay = { ...mockReplays[0], session_id: 'replay/id' }
    const fetch = vi.fn().mockResolvedValueOnce({ ok: true, json: async () => library })
      .mockResolvedValueOnce({ ok: true, json: async () => replay })
    vi.stubGlobal('fetch', fetch)
    expect(await fetchPersonReplays('person/id')).toEqual(library)
    expect(await fetchReplay('replay/id')).toEqual(replay)
    expect(fetch).toHaveBeenNthCalledWith(1, `${apiUrl}/people/person%2Fid/replays`)
    expect(fetch).toHaveBeenNthCalledWith(2, `${apiUrl}/replays/replay%2Fid`)
  })

  it('falls back to the skeleton library on network failure', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    const library = await fetchPersonReplays('mrs-k')
    expect(library.replays.map(replay => replay.error_types)).toEqual([['omission'], ['sequence'], ['perseveration']])
    expect(library.normal?.normal).toBe(true)
    expect(library.replays[0]).not.toHaveProperty('frames')
    expect(await fetchReplay(library.replays[0].session_id)).toEqual(mockReplays[0])
    expect((await fetchPersonReplays('mr-d')).replays).toHaveLength(1)
  })

  it.each([403, 404, 500])('rejects HTTP %s when fetching a library or replay', async status => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status }))
    await expect(fetchPersonReplays('mrs-k')).rejects.toThrow('Could not fetch replays')
    await expect(fetchReplay(mockReplays[0].session_id)).rejects.toThrow(
      status === 404 ? 'Replay not found' : 'Could not fetch replay',
    )
  })

  it('surfaces invalid API JSON instead of showing the offline library', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, json: async () => { throw new Error('Invalid JSON') },
    }))
    await expect(fetchPersonReplays('mrs-k')).rejects.toThrow('Invalid JSON')
    await expect(fetchReplay(mockReplays[0].session_id)).rejects.toThrow('Invalid JSON')
  })

  it('returns an empty library for Sam offline', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    expect(await fetchPersonReplays('sam')).toEqual({ person_id: 'sam', replays: [], normal: null })
  })

  it('sends DELETE and accepts an empty success response', async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: true })
    vi.stubGlobal('fetch', fetch)
    await deleteReplay('replay/id')
    expect(fetch).toHaveBeenCalledWith(`${apiUrl}/replays/replay%2Fid`, { method: 'DELETE' })
  })

  it('keeps offline deletions out of the library and detail', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    await deleteReplay('mr-d-omission')
    expect((await fetchPersonReplays('mr-d')).replays).toEqual([])
    await expect(fetchReplay('mr-d-omission')).rejects.toThrow('Replay not found')
    await expect(deleteReplay('mr-d-omission')).rejects.toThrow('Replay not found')
  })

  it.each([403, 404, 500])('rejects DELETE HTTP %s without hiding the offline replay', async status => {
    const replay = mockReplays[0]
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce({ ok: false, status })
      .mockRejectedValue(new Error('offline')))
    await expect(deleteReplay(replay.session_id)).rejects.toThrow(
      status === 404 ? 'Replay not found' : 'Could not delete replay',
    )
    const library = await fetchPersonReplays(replay.person_id)
    expect(library.replays.map(item => item.session_id)).toContain(replay.session_id)
    expect(await fetchReplay(replay.session_id)).toEqual(replay)
  })

  it('reports an API 404 for a replay absent from the offline library', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 404 }))
    await expect(deleteReplay('server-only')).rejects.toThrow('Replay not found')
  })
})

