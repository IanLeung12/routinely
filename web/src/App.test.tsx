import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { LiveMessage } from './live/useLiveSession.ts'
import type { ResidentSummary } from './overview/types.ts'
import type { Alert } from './contracts.ts'
import { mockAlerts } from './mock/alerts.ts'
import App from './App.tsx'

/** Stands in for a real WebSocket (mirrors live/LiveSession.test.tsx): drives the live
 * session by calling `emit` on the latest instance instead of opening a real socket. */
class FakeWebSocket {
  static instances: FakeWebSocket[] = []
  url: string
  onmessage: ((event: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  onclose: (() => void) | null = null

  constructor(url: string) {
    this.url = url
    FakeWebSocket.instances.push(this)
  }

  close() {}

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
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('API unavailable in tests')))
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('App', () => {
  it('renders the dashboard shell', async () => {
    // Flush the rejected request and fallback state update before jsdom teardown.
    await act(async () => {
      render(<App />)
    })

    expect(screen.getByRole('heading', { level: 1, name: 'Routine Watch' })).toBeTruthy()
    expect(screen.getByRole('heading', { level: 2, name: 'Unit overview' })).toBeTruthy()
    expect(screen.getByRole('note')).toBeTruthy()
  })

  it('opens the mock alert evidence and returns to the overview', async () => {
    await act(async () => { render(<App />) })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Mrs. K: Change flagged for review' }))
    })
    expect(await screen.findByText(/^Flagged for review:/)).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Suggested checks' })).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Unit overview' })).toBeNull()
    expect(screen.getByRole('note')).toBeTruthy()

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Back/ }))
    })
    expect(screen.getByRole('heading', { name: 'Unit overview' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Mrs. K: Change flagged for review' })).toBeTruthy()
  })

  it('renders the shift handoff screen once it lazy-loads', async () => {
    await act(async () => { render(<App />) })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Shift handoff' }))
    })

    expect(await screen.findByRole('heading', { name: 'Shift handoff' })).toBeTruthy()
  })

  it('opens the shift handoff from the header and returns to the overview', async () => {
    await act(async () => { render(<App />) })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Shift handoff' }))
    })

    expect(await screen.findByRole('heading', { name: 'Shift handoff' })).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Unit overview' })).toBeNull()

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Back/ }))
    })
    expect(screen.getByRole('heading', { name: 'Unit overview' })).toBeTruthy()
  })

  it('opens the pattern library from the header and returns to the overview', async () => {
    await act(async () => { render(<App />) })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Pattern library' }))
    })

    expect(await screen.findByRole('heading', { name: 'Pattern library' })).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Unit overview' })).toBeNull()

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Back/ }))
    })
    expect(screen.getByRole('heading', { name: 'Unit overview' })).toBeTruthy()
  })

  it("opens the resident's alert from the shift handoff", async () => {
    await act(async () => { render(<App />) })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Shift handoff' }))
    })
    expect(await screen.findByRole('heading', { name: 'Shift handoff' })).toBeTruthy()

    // The evidence is one tap from the handoff row (SPEC section 9).
    await act(async () => {
      fireEvent.click(await screen.findByRole('button', { name: "Open Mrs. K's alert" }))
    })

    expect(await screen.findByText(/^Flagged for review:/)).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Suggested checks' })).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Shift handoff' })).toBeNull()

    // The alert was opened from the handoff, so Back returns there, not the overview.
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Back/ }))
    })
    expect(screen.getByRole('heading', { name: 'Shift handoff' })).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Unit overview' })).toBeNull()
  })

  it('refetches residents and alerts when the live session ends with a flag', async () => {
    const watchResident: ResidentSummary = {
      id: 'mrs-k', name: 'Mrs. K', room: '204', status: 'watch', top_pattern: null, scores: [],
    }
    const flaggedResident: ResidentSummary = { ...watchResident, status: 'flagged' }
    const flaggedAlert: Alert = { ...mockAlerts[0], alert_id: 'alert-mrs-k' }

    // Keyed off the shift, not the call count: the overview and App each fetch
    // residents, so which of the two calls lands first isn't guaranteed.
    let flagged = false
    let residentCalls = 0
    let alertCalls = 0
    vi.stubGlobal('fetch', vi.fn((url: string) => {
      // The live session's end-of-session summary also fetches its own resident
      // (`/residents/mrs-k`), separately from the list the overview and App refetch.
      if (url.includes('/residents/')) {
        return Promise.resolve({ ok: true, json: async () => watchResident })
      }
      if (url.includes('/residents')) {
        residentCalls += 1
        return Promise.resolve({ ok: true, json: async () => [flagged ? flaggedResident : watchResident] })
      }
      if (url.includes('/alerts')) {
        alertCalls += 1
        return Promise.resolve({ ok: true, json: async () => (flagged ? [flaggedAlert] : []) })
      }
      return Promise.reject(new Error(`unexpected fetch: ${url}`))
    }))
    vi.stubGlobal('WebSocket', FakeWebSocket)

    await act(async () => { render(<App />) })

    expect(await screen.findByLabelText('Open Mrs. K, room 204, watch')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Mrs. K: Change flagged for review' })).toBeNull()

    const socket = FakeWebSocket.latest()
    flagged = true
    await act(async () => {
      socket.emit({ type: 'session_end', score: 6, flag: true, alert_id: 'alert-mrs-k' })
    })

    // The overview and App each fetch residents, so one refresh doubles the count.
    await waitFor(() => expect(residentCalls).toBe(4))
    await waitFor(() => expect(alertCalls).toBe(2))

    expect(await screen.findByLabelText('Open Mrs. K, room 204, flagged')).toBeTruthy()
    expect(await screen.findByRole('button', { name: 'Mrs. K: Change flagged for review' })).toBeTruthy()
  })

  it('hides the guided tour without ?tour=1 and shows it with the param', async () => {
    await act(async () => { render(<App />) })
    expect(screen.queryByRole('dialog', { name: 'Guided demo tour' })).toBeNull()
    cleanup()

    window.history.pushState({}, '', '?tour=1')
    await act(async () => { render(<App />) })
    expect(await screen.findByRole('dialog', { name: 'Guided demo tour' })).toBeTruthy()
    window.history.pushState({}, '', '/')
  })
})
