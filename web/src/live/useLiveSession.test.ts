import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { LiveMessage } from './useLiveSession.ts'
import { useLiveSession } from './useLiveSession.ts'

class FakeWebSocket {
  static instances: FakeWebSocket[] = []
  closed = false
  onmessage: ((event: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  onclose: (() => void) | null = null

  constructor() {
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

    expect(result.current.ended).toEqual({ score: 6, flag: true, alert_id: 'alert-1' })
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

  it('closes the socket on unmount', () => {
    const { unmount } = renderHook(() => useLiveSession('tea_normal'))
    const socket = FakeWebSocket.latest()

    unmount()

    expect(socket.closed).toBe(true)
  })
})
