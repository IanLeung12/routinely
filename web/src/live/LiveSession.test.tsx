import { act, cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { LiveMessage } from './useLiveSession.ts'
import { LiveSession } from './LiveSession.tsx'

/** Stands in for a real WebSocket (SPEC section 9, screen 3): tests drive it by calling
 * `emit`/`fail` on the latest instance instead of opening a real socket. */
class FakeWebSocket {
  static instances: FakeWebSocket[] = []
  url: string
  closed = false
  onmessage: ((event: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  onclose: (() => void) | null = null

  constructor(url: string) {
    this.url = url
    FakeWebSocket.instances.push(this)
  }

  close() {
    this.closed = true
  }

  emit(message: LiveMessage) {
    this.onmessage?.({ data: JSON.stringify(message) })
  }

  fail() {
    this.onerror?.()
    this.onclose?.()
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
  FakeWebSocket.instances = []
  vi.stubGlobal('WebSocket', FakeWebSocket)
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

describe('LiveSession', () => {
  it('opens a WebSocket at the live session route for the scenario', () => {
    render(<LiveSession scenario="tea_skip_teabag_pour_twice" speed={2} />)

    expect(FakeWebSocket.latest().url).toBe('ws://localhost:8000/ws/live?scenario=tea_skip_teabag_pour_twice&speed=2')
  })

  it('updates the task map and error list as live messages arrive, no mock badge', () => {
    render(<LiveSession scenario="tea_skip_teabag_pour_twice" />)
    const socket = FakeWebSocket.latest()

    act(() => {
      socket.emit({ type: 'step_state', states: { fill_kettle: 'done' } })
    })
    expect(screen.getByText('Fill the kettle').closest('[role="listitem"]')?.getAttribute('data-state')).toBe(
      'done',
    )
    expect(screen.queryByText('Mock data')).toBeNull()

    act(() => {
      socket.emit({
        type: 'error',
        error: {
          error_id: 'live-error-1',
          session_id: 'live-session',
          type: 'omission',
          step_id: 'teabag_in_cup',
          t_start: 72,
          t_end: 72,
          evidence: [],
        },
      })
    })
    expect(screen.getByText('Omission · Put the teabag in the cup · 1:12')).toBeTruthy()

    act(() => {
      socket.emit({ type: 'session_end', score: 6, flag: true, alert_id: 'alert-1' })
    })
    expect(screen.getByRole('status').textContent).toBe('Flagged for review')
  })

  it('shows a clear banner when session_end is not flagged', () => {
    render(<LiveSession scenario="tea_normal" />)
    const socket = FakeWebSocket.latest()

    act(() => {
      socket.emit({ type: 'session_end', score: 0, flag: false, alert_id: null })
    })

    expect(screen.getByRole('status').textContent).toBe('Session complete, nothing flagged')
  })

  it('falls back to the mock stream on a WebSocket failure, showing the mock badge', () => {
    vi.useFakeTimers()
    render(<LiveSession scenario="tea_skip_teabag_pour_twice" />)
    const socket = FakeWebSocket.latest()

    act(() => {
      socket.fail()
    })
    expect(screen.getByText('Mock data')).toBeTruthy()

    act(() => {
      vi.advanceTimersByTime(10_000)
    })

    expect(screen.getByRole('status').textContent).toBe('Flagged for review')
    const errorItems = within(screen.getByText('Errors').closest('.card')!).getAllByRole('listitem')
    expect(errorItems).toHaveLength(2)
    expect(errorItems.map((item) => item.textContent)).toEqual([
      'Perseveration · Pour the water · 0:30',
      'Omission · Put the teabag in the cup · 0:40',
    ])

    expect(
      screen.getByText('Put the teabag in the cup').closest('[role="listitem"]')?.getAttribute('data-state'),
    ).toBe('omission')
    expect(screen.getByText('Pour the water').closest('[role="listitem"]')?.getAttribute('data-state')).toBe(
      'repeat',
    )
  })

  it('does not fall back to mock if the socket closes after already receiving data', () => {
    vi.useFakeTimers()
    render(<LiveSession scenario="tea_skip_teabag_pour_twice" />)
    const socket = FakeWebSocket.latest()

    act(() => {
      socket.emit({ type: 'step_state', states: { fill_kettle: 'done' } })
      socket.onclose?.()
    })

    act(() => {
      vi.advanceTimersByTime(10_000)
    })

    expect(screen.queryByText('Mock data')).toBeNull()
  })
})
