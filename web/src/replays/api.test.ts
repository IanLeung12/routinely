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

  it.each(['network', 'non-ok'])('falls back to the skeleton library on %s failure', async failure => {
    vi.stubGlobal('fetch', failure === 'network'
      ? vi.fn().mockRejectedValue(new Error('offline'))
      : vi.fn().mockResolvedValue({ ok: false }))
    const library = await fetchPersonReplays('mrs-k')
    expect(library.replays.map(replay => replay.error_types)).toEqual([['omission'], ['sequence'], ['perseveration']])
    expect(library.normal?.normal).toBe(true)
    expect(library.replays[0]).not.toHaveProperty('frames')
    expect(await fetchReplay(library.replays[0].session_id)).toEqual(mockReplays[0])
    expect((await fetchPersonReplays('mr-d')).replays).toHaveLength(1)
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
  })
})

