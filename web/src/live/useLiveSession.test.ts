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

  it('closes the socket on unmount', () => {
    const { unmount } = renderHook(() => useLiveSession('tea_normal'))
    const socket = FakeWebSocket.latest()

    unmount()

    expect(socket.closed).toBe(true)
  })
})
