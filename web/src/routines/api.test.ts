import { afterEach, describe, expect, it, vi } from 'vitest'
import { mockBuiltInRoutines } from '../mock/routines.ts'
import { draftFromText, draftFromVideo, fetchRoutines, saveRoutine } from './api.ts'
import type { TaskGraph } from './types.ts'

afterEach(() => {
  vi.unstubAllGlobals()
  localStorage.clear()
})

describe('draftFromText', () => {
  it('returns the API draft on a 200', async () => {
    const draft = { draft: { steps: [] }, task_graph: { id: 'x', title: 'X', steps: [] }, needs_training: [], warnings: [] }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => draft }))

    expect(await draftFromText('make toast')).toEqual(draft)
  })

  it('falls back to a canned draft when the API is unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))

    const result = await draftFromText('brush my teeth')
    expect(result.task_graph.id).toBe('brush_teeth')
    expect(result.needs_training).toEqual(expect.arrayContaining(['toothbrush']))
  })

  it('rejects with the detail on a non-OK response, instead of a canned draft', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: false, status: 500, json: async () => ({ detail: 'the drafting model could not be reached; try again' }) }),
    )

    await expect(draftFromText('make toast please')).rejects.toThrow(
      'the drafting model could not be reached; try again',
    )
  })
})

describe('draftFromVideo', () => {
  it('rejects without consent, before touching the network', async () => {
    const fetch = vi.fn()
    vi.stubGlobal('fetch', fetch)
    const file = new File(['clip'], 'setup.mp4', { type: 'video/mp4' })

    await expect(draftFromVideo(file, false)).rejects.toThrow(/consent/i)
    expect(fetch).not.toHaveBeenCalled()
  })

  it('falls back to the canned "brush teeth" draft offline', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    const file = new File(['clip'], 'setup.mp4', { type: 'video/mp4' })

    const result = await draftFromVideo(file, true)
    expect(result.task_graph.id).toBe('brush_teeth')
  })

  it('rejects with the detail on a 413 (clip too big), instead of a canned draft', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 413,
        json: async () => ({ detail: 'one setup clip is at most 25 MB; film a shorter one' }),
      }),
    )
    const file = new File(['clip'], 'setup.mp4', { type: 'video/mp4' })

    await expect(draftFromVideo(file, true)).rejects.toThrow(
      'one setup clip is at most 25 MB; film a shorter one',
    )
  })
})

describe('fetchRoutines', () => {
  it('returns the built-ins plus anything saved locally when offline', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))

    const routines = await fetchRoutines()
    expect(routines).toEqual(mockBuiltInRoutines)
  })
})

describe('saveRoutine', () => {
  it('keeps a saved routine in localStorage when the API is unreachable, so it shows up next time', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    const graph: TaskGraph = { id: 'wash_hands', title: 'Wash hands', steps: [] }

    const saved = await saveRoutine(graph)
    // `Routine.detail()`'s shape, so the list's step count works offline too (T443).
    expect(saved).toEqual({
      id: 'wash_hands',
      title: 'Wash hands',
      task_id: 'wash_hands',
      built_in: false,
      source: 'text',
      step_count: 0,
      needs_training: [],
      task_graph: graph,
    })

    const routines = await fetchRoutines()
    expect(routines).toContainEqual(saved)
  })

  it('rejects with the detail on a 409 (built-in id or full library), and writes nothing to localStorage', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: false, status: 409, json: async () => ({ detail: "'tea' is a built-in routine" }) }),
    )
    const graph: TaskGraph = { id: 'tea', title: 'Tea', steps: [] }

    await expect(saveRoutine(graph)).rejects.toThrow("'tea' is a built-in routine")
    expect(localStorage.getItem('rw.routines.saved')).toBeNull()
  })
})
