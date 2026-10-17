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

  it('falls back on a non-OK response too', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }))

    const result = await draftFromText('make toast please')
    expect(result.task_graph.id).toBe('make_toast')
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
    expect(saved).toEqual({ id: 'wash_hands', title: 'Wash hands', task_graph: graph, built_in: false })

    const routines = await fetchRoutines()
    expect(routines).toContainEqual(saved)
  })
})
