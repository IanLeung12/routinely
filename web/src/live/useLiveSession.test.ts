import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { CaptureFrame } from '../contracts.ts'
import type { LiveCamera, LiveMessage } from './useLiveSession.ts'
import { useLiveSession } from './useLiveSession.ts'

class FakeWebSocket {
  static instances: FakeWebSocket[] = []
  url: string
  closed = false
  onmessage: ((event: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  onclose: ((event?: { code?: number }) => void) | null = null

  constructor(url = '') {
    this.url = url
    FakeWebSocket.instances.push(this)
  }

  close() {
    this.closed = true
  }

  emit(message: LiveMessage) {
    this.onmessage?.({ data: JSON.stringify(message) })
  }

  static latest(): FakeWebSocket {
    const instance = FakeWebSocket.instances[FakeWebSocket.instances.length - 1]
    if (!instance) {
      throw new Error('no FakeWebSocket instance was created')
    }
    return instance
  }
}

beforeEach(() => {
  vi.useFakeTimers()
  FakeWebSocket.instances = []
  vi.stubGlobal('WebSocket', FakeWebSocket)
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

describe('useLiveSession', () => {
  it('updates step states as step_state messages arrive', () => {
    const { result } = renderHook(() => useLiveSession('tea_normal'))
    const socket = FakeWebSocket.latest()

    act(() => {
      socket.emit({ type: 'step_state', states: { fill_kettle: 'done' } })
    })

    expect(result.current.states.fill_kettle).toBe('done')
  })

  it('sets the ended state from a session_end message', () => {
    const { result } = renderHook(() => useLiveSession('tea_normal'))
    const socket = FakeWebSocket.latest()

    act(() => {
      socket.emit({ type: 'session_end', score: 6, flag: true, alert_id: 'alert-1' })
    })

    // `quality` defaults to 'ok' for a session_end that carries none, so the screen
    // shows the score rather than the "capture unclear" notice (T343).
    expect(result.current.ended).toEqual({ score: 6, flag: true, alert_id: 'alert-1', quality: 'ok' })
  })

  it('replaces streamed errors with session_end errors when present', () => {
    const { result } = renderHook(() => useLiveSession('tea_normal'))
    const socket = FakeWebSocket.latest()

    const streamedOmission = {
      error_id: 'err-1',
      session_id: 's1',
      type: 'omission' as const,
      step_id: 'teabag_in_cup',
      t_start: 1,
      t_end: 1,
      evidence: [],
    }
    const finalError = {
      error_id: 'err-2',
      session_id: 's1',
      type: 'sequence' as const,
      step_id: 'pour',
      t_start: 2,
      t_end: 2,
      evidence: [],
    }

    act(() => {
      socket.emit({ type: 'error', error: streamedOmission })
    })
    expect(result.current.errors).toEqual([streamedOmission])

    act(() => {
      socket.emit({ type: 'session_end', score: 6, flag: true, alert_id: 'alert-1', errors: [finalError] })
    })

    expect(result.current.errors).toEqual([finalError])
  })

  it('keeps the streamed error list when session_end has no errors', () => {
    const { result } = renderHook(() => useLiveSession('tea_normal'))
    const socket = FakeWebSocket.latest()

    const streamedOmission = {
      error_id: 'err-1',
      session_id: 's1',
      type: 'omission' as const,
      step_id: 'teabag_in_cup',
      t_start: 1,
      t_end: 1,
      evidence: [],
    }

    act(() => {
      socket.emit({ type: 'error', error: streamedOmission })
    })

    act(() => {
      socket.emit({ type: 'session_end', score: 6, flag: true, alert_id: 'alert-1' })
    })

    expect(result.current.errors).toEqual([streamedOmission])
  })

  it('reports the paused room from a paused message and never falls back to mock data', () => {
    const { result } = renderHook(() => useLiveSession('tea_normal'))
    const socket = FakeWebSocket.latest()

    // What `GET /ws/live` does when the demo resident's room is paused (SPEC section
    // 12): one `paused` message, then the socket closes with no session played.
    act(() => {
      socket.emit({ type: 'paused', room: '204' })
      socket.onclose?.()
    })
    act(() => {
      vi.advanceTimersByTime(10_000)
    })

    expect(result.current.paused).toEqual({ room: '204' })
    expect(result.current.source).toBe('live')
    expect(result.current.steps).toEqual([])
    expect(result.current.ended).toBeNull()
  })

  it('leaves paused null for a session that plays normally', () => {
    const { result } = renderHook(() => useLiveSession('tea_normal'))
    const socket = FakeWebSocket.latest()

    act(() => {
      socket.emit({ type: 'session_end', score: 0, flag: false, alert_id: null })
    })

    expect(result.current.paused).toBeNull()
  })

  it('retry clears the paused state and opens a new socket that can stream normally', () => {
    const { result } = renderHook(() => useLiveSession('tea_normal'))
    const firstSocket = FakeWebSocket.latest()

    act(() => {
      firstSocket.emit({ type: 'paused', room: '204' })
      firstSocket.onclose?.()
    })
    expect(result.current.paused).toEqual({ room: '204' })

    act(() => {
      result.current.retry()
    })
    expect(result.current.paused).toBeNull()
    expect(FakeWebSocket.instances.length).toBe(2)
    expect(firstSocket.closed).toBe(true)

    const secondSocket = FakeWebSocket.latest()
    expect(secondSocket).not.toBe(firstSocket)

    act(() => {
      secondSocket.emit({ type: 'step_state', states: { fill_kettle: 'done' } })
    })
    expect(result.current.paused).toBeNull()
    expect(result.current.states.fill_kettle).toBe('done')
  })

  it('leaves paused set when a retry reconnects to a still-paused room', () => {
    const { result } = renderHook(() => useLiveSession('tea_normal'))
    const firstSocket = FakeWebSocket.latest()

    act(() => {
      firstSocket.emit({ type: 'paused', room: '204' })
      firstSocket.onclose?.()
    })

    act(() => {
      result.current.retry()
    })
    const secondSocket = FakeWebSocket.latest()

    act(() => {
      secondSocket.emit({ type: 'paused', room: '204' })
      secondSocket.onclose?.()
    })
    act(() => {
      vi.advanceTimersByTime(10_000)
    })

    expect(result.current.paused).toEqual({ room: '204' })
    expect(result.current.source).toBe('live')
  })

  it('closes the socket on unmount', () => {
    const { unmount } = renderHook(() => useLiveSession('tea_normal'))
    const socket = FakeWebSocket.latest()

    unmount()

    expect(socket.closed).toBe(true)
  })

  // ------------------------------------------------- the camera that won't open (T394)

  it('reports cameraUnavailable, without falling back to mock data, when the socket closes 4503', () => {
    const { result } = renderHook(() => useLiveSession('tea_normal', 1, { index: 0, task: 'tea' }))
    const socket = FakeWebSocket.latest()

    act(() => {
      socket.onclose?.({ code: 4503 })
    })
    act(() => {
      vi.advanceTimersByTime(10_000)
    })

    expect(result.current.cameraUnavailable).toBe(true)
    expect(result.current.source).toBe('live')
    expect(result.current.steps).toEqual([])
  })

  it('leaves cameraUnavailable false and falls back to mock data on an unrelated close code', () => {
    const { result } = renderHook(() => useLiveSession('tea_normal'))
    const socket = FakeWebSocket.latest()

    act(() => {
      socket.onclose?.({ code: 4404 })
    })
    act(() => {
      vi.advanceTimersByTime(10_000)
    })

    expect(result.current.cameraUnavailable).toBe(false)
    expect(result.current.source).toBe('mock')
  })

  // ------------------------------------------------------- the camera (T356)

  function frame(objects: CaptureFrame['objects'] = []): LiveMessage {
    return {
      type: 'frame',
      frame: { session_id: 's', seq: 0, t: 0, source: 'camera', poses: [], hands: [], objects },
    }
  }

  it('plays the recorded scenario by default', () => {
    renderHook(() => useLiveSession('tea_normal', 2))

    expect(FakeWebSocket.latest().url).toContain('/ws/live?scenario=tea_normal&speed=2')
  })

  it('asks for the camera and the task graph when pointed at one', () => {
    renderHook(() => useLiveSession('tea_normal', 1, { index: 2, task: 'meds' }))

    expect(FakeWebSocket.latest().url).toContain('/ws/live?source=camera&camera=2&task=meds')
  })

  it('opens a fresh socket when the screen switches from a recording to the camera', () => {
    const { rerender } = renderHook(
      ({ camera }: { camera: LiveCamera | null }) => useLiveSession('tea_normal', 1, camera),
      { initialProps: { camera: null as LiveCamera | null } },
    )

    rerender({ camera: { index: 0, task: 'tea' } })

    expect(FakeWebSocket.instances).toHaveLength(2)
    expect(FakeWebSocket.latest().url).toContain('source=camera')
  })

  it('keeps one socket while the camera it was given stays the same', () => {
    const { rerender } = renderHook(() => useLiveSession('tea_normal', 1, { index: 0, task: 'tea' }))

    rerender()

    expect(FakeWebSocket.instances).toHaveLength(1)
  })

  it('remembers whether any frame has carried an object box', () => {
    const { result } = renderHook(() => useLiveSession('tea_normal', 1, { index: 0, task: 'tea' }))
    const socket = FakeWebSocket.latest()

    act(() => {
      socket.emit(frame())
    })
    expect(result.current.objectsSeen).toBe(false)

    act(() => {
      socket.emit(frame([{ label: 'cup', confidence: 0.9, box: { x1: 0, y1: 0, x2: 0.1, y2: 0.1 } }]))
    })
    expect(result.current.objectsSeen).toBe(true)

    // The detector losing sight of the cup is not the detector being missing.
    act(() => {
      socket.emit(frame())
    })
    expect(result.current.objectsSeen).toBe(true)
  })
})

