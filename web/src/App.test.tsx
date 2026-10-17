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
      fireEvent.click(screen.getByRole('button', { name: 'mrs-k: Change flagged for review' }))
    })
    expect(await screen.findByText(/^Flagged for review:/)).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Suggested checks' })).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Unit overview' })).toBeNull()
    expect(screen.getByRole('note')).toBeTruthy()

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Back/ }))
    })
    expect(screen.getByRole('heading', { name: 'Unit overview' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'mrs-k: Change flagged for review' })).toBeTruthy()
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

  it('refetches residents and alerts when the live session ends with a flag', async () => {
    const watchResident: ResidentSummary = {
      id: 'mrs-k', name: 'Mrs. K', room: '204', status: 'watch', top_pattern: null, scores: [],
    }
    const flaggedResident: ResidentSummary = { ...watchResident, status: 'flagged' }
    const flaggedAlert: Alert = { ...mockAlerts[0], alert_id: 'alert-mrs-k' }

    let residentCalls = 0
    let alertCalls = 0
    vi.stubGlobal('fetch', vi.fn((url: string) => {
      if (url.includes('/residents')) {
        residentCalls += 1
        return Promise.resolve({ ok: true, json: async () => [residentCalls === 1 ? watchResident : flaggedResident] })
      }
      if (url.includes('/alerts')) {
        alertCalls += 1
        return Promise.resolve({ ok: true, json: async () => (alertCalls === 1 ? [] : [flaggedAlert]) })
      }
      return Promise.reject(new Error(`unexpected fetch: ${url}`))
    }))
    vi.stubGlobal('WebSocket', FakeWebSocket)

    await act(async () => { render(<App />) })

    expect(await screen.findByLabelText('Open Mrs. K, room 204, watch')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'mrs-k: Change flagged for review' })).toBeNull()

    const socket = FakeWebSocket.latest()
    await act(async () => {
      socket.emit({ type: 'session_end', score: 6, flag: true, alert_id: 'alert-mrs-k' })
    })

    await waitFor(() => expect(residentCalls).toBe(2))
    await waitFor(() => expect(alertCalls).toBe(2))

    expect(await screen.findByLabelText('Open Mrs. K, room 204, flagged')).toBeTruthy()
    expect(await screen.findByRole('button', { name: 'mrs-k: Change flagged for review' })).toBeTruthy()
  })
})
