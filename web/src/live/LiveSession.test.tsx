import { act, cleanup, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fetchResident } from '../resident/api.ts'
import type { Resident } from '../resident/types.ts'
import type { LiveMessage } from './useLiveSession.ts'
import { LiveSession } from './LiveSession.tsx'

vi.mock('../resident/api.ts', () => ({
  fetchResident: vi.fn(),
}))

/** Mrs. K as `GET /residents/{id}` serves her: her baseline carries the usual
 * duration and error count the pipeline averaged over her early days, and her
 * recorded sessions are the bad ones that put her on watch. The two disagree on
 * purpose - the screen must read the baseline, not average the sessions. */
const MRS_K: Resident = {
  id: 'mrs-k',
  name: 'Mrs. K',
  room: '204',
  status: 'watch',
  top_pattern: null,
  scores: [],
  sessions: [
    {
      resident_id: 'mrs-k',
      ts: '2026-01-01T08:00:00+00:00',
      task: 'tea',
      errors: { omission: 2, perseveration: 2 },
      self_corrected: 0,
      duration_s: 600,
      assisted: false,
    },
  ],
  care_records: [],
  baseline: { mean: 1, std: 0.5, threshold: 2, usual_duration_s: 170, usual_errors: 1 },
}

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
  vi.mocked(fetchResident).mockResolvedValue(null)
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

describe('LiveSession', () => {
  it('shows the five-state legend directly below the task map', () => {
    render(<LiveSession scenario="tea_normal" />)

    const map = screen.getByRole('list', { name: 'Task steps' })
    const legend = screen.getByRole('list', { name: 'Task map legend' })
    expect(map.nextElementSibling).toBe(legend)
    expect(within(legend).getAllByRole('listitem').map((item) => item.textContent)).toEqual([
      'not yet', '✓ done', '✕ missed step', '↻ repeated step', '⇄ out of order',
    ])
  })

  it('renders the task map from the session_start message, not a hard-coded task', () => {
    render(<LiveSession scenario="medication" />)
    const socket = FakeWebSocket.latest()

    act(() => {
      socket.emit({
        type: 'session_start',
        session_id: 'live-session',
        task_id: 'medication',
        steps: [
          { id: 'open_box', label: 'Open the pill box', optional: false },
          { id: 'take_pill', label: 'Take the pill', optional: false },
        ],
      })
    })

    const map = screen.getByRole('list', { name: 'Task steps' })
    expect(within(map).getAllByRole('listitem').map((item) => item.textContent)).toEqual([
      'Open the pill box',
      'Take the pill',
    ])
    expect(screen.queryByText('Fill the kettle')).toBeNull()
  })

  it('opens a WebSocket at the live session route for the scenario', () => {
    render(<LiveSession scenario="tea_skip_teabag_pour_twice" speed={2} />)

    expect(FakeWebSocket.latest().url).toBe('ws://localhost:8000/ws/live?scenario=tea_skip_teabag_pour_twice&speed=2')
  })

  it('updates the task map and error list as live messages arrive, no mock badge', () => {
    render(<LiveSession scenario="tea_skip_teabag_pour_twice" />)
    const socket = FakeWebSocket.latest()

    act(() => {
      socket.emit({
        type: 'session_start',
        session_id: 'live-session',
        task_id: 'tea',
        steps: [
          { id: 'fill_kettle', label: 'Fill the kettle', optional: false },
          { id: 'teabag_in_cup', label: 'Put the teabag in the cup', optional: false },
        ],
      })
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
    expect(screen.getByText('skipped Put the teabag in the cup · 1:12')).toBeTruthy()

    act(() => {
      socket.emit({ type: 'session_end', score: 6, flag: true, alert_id: 'alert-1' })
    })
    expect(screen.getByRole('status').textContent).toBe('Flagged for review')
  })

  it('shows an end-of-session summary above the flag banner, timed from the first and last step', () => {
    render(<LiveSession scenario="tea_skip_teabag_pour_twice" />)
    const socket = FakeWebSocket.latest()

    act(() => {
      socket.emit({
        type: 'step',
        event: {
          event_id: 'e1',
          session_id: 'live-session',
          step_id: 'fill_kettle',
          objects: [],
          t_start: 0,
          t_end: 1,
          confidence: 0.9,
          source: 'rule',
        },
      })
      socket.emit({
        type: 'step',
        event: {
          event_id: 'e2',
          session_id: 'live-session',
          step_id: 'pour',
          objects: [],
          t_start: 219,
          t_end: 220,
          confidence: 0.9,
          source: 'rule',
        },
      })
      socket.emit({ type: 'session_end', score: 0, flag: false, alert_id: null })
    })

    const summary = screen.getByText('Session summary').closest('.card') as HTMLElement
    expect(within(summary).getByText('Finished in 3m 40s · 0 errors')).toBeTruthy()
    expect(summary.nextElementSibling?.getAttribute('role')).toBe('status')
  })

  it("shows the resident's usual duration and errors from the baseline, not their recent sessions", async () => {
    vi.mocked(fetchResident).mockResolvedValue(MRS_K)
    render(<LiveSession scenario="tea_skip_teabag_pour_twice" />)
    const socket = FakeWebSocket.latest()

    act(() => {
      socket.emit({ type: 'session_end', score: 0, flag: false, alert_id: null })
    })

    // The baseline's 170 s and 1 error, not the 600 s and 4 errors of the bad
    // session she is being flagged for (T230).
    await waitFor(() => {
      expect(document.querySelector('.session-summary__line')?.textContent).toBe(
        'Finished in 0s (usually ~2m 50s) · 0 errors (usually ~1)',
      )
    })
  })

  it('leaves the "usually" comparison out when the baseline carries no usual values', async () => {
    vi.mocked(fetchResident).mockResolvedValue({
      ...MRS_K,
      baseline: { mean: 1, std: 0.5, threshold: 2 },
    })
    render(<LiveSession scenario="tea_skip_teabag_pour_twice" />)
    const socket = FakeWebSocket.latest()

    act(() => {
      socket.emit({ type: 'session_end', score: 0, flag: false, alert_id: null })
    })

    // Flush the resident fetch, so this asserts the loaded baseline rather than
    // the blank one the screen renders before it arrives.
    await act(async () => {})
    expect(document.querySelector('.session-summary__line')?.textContent).toBe(
      'Finished in 0s · 0 errors',
    )
  })

  it('shows an Open alert button when flagged and calls onOpenAlert with the id', () => {
    const onOpenAlert = vi.fn()
    render(<LiveSession scenario="tea_skip_teabag_pour_twice" onOpenAlert={onOpenAlert} />)
    const socket = FakeWebSocket.latest()

    act(() => {
      socket.emit({ type: 'session_end', score: 6, flag: true, alert_id: 'alert-1' })
    })

    screen.getByRole('button', { name: 'Open alert' }).click()
    expect(onOpenAlert).toHaveBeenCalledWith('alert-1')
  })

  it('shows no Open alert button when the session is clear', () => {
    render(<LiveSession scenario="tea_normal" onOpenAlert={vi.fn()} />)
    const socket = FakeWebSocket.latest()

    act(() => {
      socket.emit({ type: 'session_end', score: 0, flag: false, alert_id: null })
    })

    expect(screen.queryByRole('button', { name: 'Open alert' })).toBeNull()
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
      'repeated Pour the water · 0:30',
      'skipped Put the teabag in the cup · 0:40',
    ])

    expect(
      screen.getByText('Put the teabag in the cup').closest('[role="listitem"]')?.getAttribute('data-state'),
    ).toBe('omission')
    expect(screen.getByText('Pour the water').closest('[role="listitem"]')?.getAttribute('data-state')).toBe(
      'repeat',
    )
  })

  it('says monitoring is paused instead of showing a session, with no mock fallback', async () => {
    vi.useFakeTimers()
    render(<LiveSession scenario="tea_skip_teabag_pour_twice" />)
    const socket = FakeWebSocket.latest()

    // The API's answer for a paused room (SPEC section 12): one `paused` message, then
    // the socket closes without a session.
    act(() => {
      socket.emit({ type: 'paused', room: '204' })
      socket.onclose?.()
    })
    act(() => {
      vi.advanceTimersByTime(10_000)
    })

    expect(screen.getByRole('status').textContent).toContain('Monitoring is paused for room 204')
    expect(
      screen.getByText("Turn it back on from the resident's page to watch their routines again."),
    ).toBeTruthy()

    // Nothing was watched, so there is no skeleton view, task map or error ticker to
    // show - and a pause is not a lost connection, so no mock session either.
    expect(screen.queryByRole('list', { name: 'Task steps' })).toBeNull()
    expect(screen.queryByText('Skeleton view')).toBeNull()
    expect(screen.queryByText('Errors')).toBeNull()
    expect(screen.queryByText('Mock data')).toBeNull()

    // Let the resident fetch settle before the test ends, so no state update lands
    // after jsdom is torn down.
    await act(async () => {})
  })

  it('announces step completions and raised flags through a polite live region', () => {
    render(<LiveSession scenario="tea_skip_teabag_pour_twice" />)
    const socket = FakeWebSocket.latest()
    const announcer = document.querySelector('.live-session__announcer') as HTMLElement
    expect(announcer.getAttribute('aria-live')).toBe('polite')

    act(() => {
      socket.emit({
        type: 'session_start',
        session_id: 'live-session',
        task_id: 'tea',
        steps: [
          { id: 'fill_kettle', label: 'Fill the kettle', optional: false },
          { id: 'teabag_in_cup', label: 'Put the teabag in the cup', optional: false },
        ],
      })
      socket.emit({ type: 'step_state', states: { fill_kettle: 'done' } })
    })
    expect(announcer.textContent).toBe('Step done: Fill the kettle')

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
    expect(announcer.textContent).toBe('Flag raised: skipped Put the teabag in the cup · 1:12')
  })

  it('announces a connection status change when the socket falls back to mock data', () => {
    vi.useFakeTimers()
    render(<LiveSession scenario="tea_skip_teabag_pour_twice" />)
    const socket = FakeWebSocket.latest()
    const announcer = document.querySelector('.live-session__announcer') as HTMLElement

    act(() => {
      socket.fail()
    })

    expect(announcer.textContent).toBe('Connection lost. Showing offline demo data.')
  })

  it('calls onSessionEnd once with the ended payload when flagged, not again on re-render', () => {
    const onSessionEnd = vi.fn()
    const { rerender } = render(<LiveSession scenario="tea_skip_teabag_pour_twice" onSessionEnd={onSessionEnd} />)
    const socket = FakeWebSocket.latest()

    act(() => {
      socket.emit({ type: 'session_end', score: 6, flag: true, alert_id: 'alert-1' })
    })

    expect(onSessionEnd).toHaveBeenCalledTimes(1)
    expect(onSessionEnd).toHaveBeenCalledWith({ score: 6, flag: true, alert_id: 'alert-1' })

    rerender(<LiveSession scenario="tea_skip_teabag_pour_twice" onSessionEnd={onSessionEnd} />)
    expect(onSessionEnd).toHaveBeenCalledTimes(1)
  })

  it('calls onSessionEnd once when the session is clear', () => {
    const onSessionEnd = vi.fn()
    render(<LiveSession scenario="tea_normal" onSessionEnd={onSessionEnd} />)
    const socket = FakeWebSocket.latest()

    act(() => {
      socket.emit({ type: 'session_end', score: 0, flag: false, alert_id: null })
    })

    expect(onSessionEnd).toHaveBeenCalledTimes(1)
    expect(onSessionEnd).toHaveBeenCalledWith({ score: 0, flag: false, alert_id: null })
  })

  it('does not throw when onSessionEnd is omitted', () => {
    render(<LiveSession scenario="tea_normal" />)
    const socket = FakeWebSocket.latest()

    expect(() => {
      act(() => {
        socket.emit({ type: 'session_end', score: 0, flag: false, alert_id: null })
      })
    }).not.toThrow()
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
