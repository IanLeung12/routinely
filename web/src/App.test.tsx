import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ResidentSummary } from './overview/types.ts'
import type { Alert } from './contracts.ts'
import { mockAlerts } from './mock/alerts.ts'
import { FakeWebSocket } from './live/testWebSocket.ts'
import {
  createInvite,
  currentSupervisor,
  getRole,
  peopleISupport,
  resetPeople,
  setPeopleApi,
  setRole,
  unlink,
} from './people/api.ts'
import App from './App.tsx'

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('API unavailable in tests')))
  // Every screen below the roles block is the supervisor's, and the demo's supervisor
  // is the care-home nurse: the nurse dashboard is the supervisor-with-many case
  // (SPEC section 17). The chooser has its own tests and starts from no role at all.
  localStorage.clear()
  setPeopleApi(null)
  setRole('supervisor')
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('App', () => {
  it('shows the live routine picker with making tea selected by default', async () => {
    await act(async () => { render(<App />) })

    const picker = within(screen.getByRole('group', { name: 'Routine to watch' }))
    expect(picker.getByRole('button', { name: 'Making tea', pressed: true })).toBeTruthy()
    expect(picker.getByRole('button', { name: 'Medication with water', pressed: false })).toBeTruthy()
  })

  it('renders the dashboard shell', async () => {
    // Flush the rejected request and fallback state update before jsdom teardown.
    await act(async () => {
      render(<App />)
    })

    expect(screen.getByRole('heading', { level: 1, name: 'Routinely' })).toBeTruthy()
    expect(screen.getByRole('heading', { level: 2, name: 'Unit overview' })).toBeTruthy()
    expect(screen.getByRole('note')).toBeTruthy()
  })

  it('has a skip link before the main landmark, for keyboard users', async () => {
    await act(async () => {
      render(<App />)
    })

    const skipLink = screen.getByRole('link', { name: 'Skip to main content' })
    expect(skipLink.getAttribute('href')).toBe('#main')
    const main = screen.getByRole('main')
    expect(main.id).toBe('main')
    // The skip link is the first focusable element, ahead of the main landmark.
    expect(skipLink.compareDocumentPosition(main) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
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

  it('shows the nav dock and jumps straight back to the overview from another screen', async () => {
    await act(async () => { render(<App />) })

    const dock = within(screen.getByRole('navigation', { name: 'Main screens' }))
    expect(dock.getByRole('button', { name: 'Overview' }).getAttribute('aria-current')).toBe('page')

    await act(async () => {
      fireEvent.click(dock.getByRole('button', { name: 'Shift handoff' }))
    })
    expect(await screen.findByRole('heading', { name: 'Shift handoff' })).toBeTruthy()
    expect(dock.getByRole('button', { name: 'Shift handoff' }).getAttribute('aria-current')).toBe('page')

    await act(async () => {
      fireEvent.click(dock.getByRole('button', { name: 'Overview' }))
    })
    expect(screen.getByRole('heading', { name: 'Unit overview' })).toBeTruthy()
    expect(dock.getByRole('button', { name: 'Overview' }).getAttribute('aria-current')).toBe('page')
  })

  it('shows an offline indicator in the top bar when the residents API is unreachable', async () => {
    await act(async () => { render(<App />) })

    expect(await screen.findByText('Offline — demo data')).toBeTruthy()
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

describe('roles', () => {
  it('asks who the app is for on first open, and not again after', async () => {
    resetPeople()
    await act(async () => { render(<App />) })

    expect(screen.getByRole('heading', { name: 'Who is this for?' })).toBeTruthy()
    expect(screen.queryByRole('heading', { level: 2, name: 'Unit overview' })).toBeNull()

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /setting this up for myself/i }))
    })
    expect(screen.getByRole('heading', { name: 'My routine' })).toBeTruthy()

    // Opened again later: the choice is remembered, so nobody is asked twice.
    cleanup()
    await act(async () => { render(<App />) })
    expect(screen.queryByRole('heading', { name: 'Who is this for?' })).toBeNull()
    expect(screen.getByRole('heading', { name: 'My routine' })).toBeTruthy()
  })

  it('changes the home screen when the role is switched in the shell', async () => {
    await act(async () => { render(<App />) })
    expect(await screen.findByRole('heading', { level: 2, name: 'Unit overview' })).toBeTruthy()

    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Myself' })) })
    expect(screen.getByRole('heading', { name: 'My routine' })).toBeTruthy()
    expect(screen.queryByRole('heading', { level: 2, name: 'Unit overview' })).toBeNull()

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Someone I support' }))
    })
    expect(await screen.findByRole('heading', { level: 2, name: 'Unit overview' })).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'My routine' })).toBeNull()
  })

  it('opens straight into the one person a supervisor supports', async () => {
    // Everyone but Mrs. K taken off: a daughter watching her father has no unit to
    // read first (SPEC section 17).
    peopleISupport()
      .filter((person) => person.id !== 'mrs-k')
      .forEach((person) => unlink(person.id, currentSupervisor().id))

    await act(async () => { render(<App />) })

    expect(await screen.findByRole('heading', { level: 1, name: 'Mrs. K' })).toBeTruthy()
    expect(screen.queryByRole('heading', { level: 2, name: 'Unit overview' })).toBeNull()

    // Back goes to the people list, not to a unit overview they are not part of.
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /People I support/ }))
    })
    expect(screen.getByRole('heading', { level: 2, name: 'People I support' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Stop supporting Mrs. K' })).toBeTruthy()
  })

  it('round-trips an invite from the person to the supervisor and back', async () => {
    await act(async () => { render(<App />) })

    // As the person: hand out a code.
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Myself' })) })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Invite someone' }))
    })
    const { code } = createInvite('sam')
    expect(screen.getByText(code)).toBeTruthy()

    // As the supervisor: type it in.
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Someone I support' }))
    })
    fireEvent.change(screen.getByLabelText('Invite code'), { target: { value: code } })
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Add person' })) })

    expect(screen.getByText('Sam shared their routine with you.')).toBeTruthy()
    expect(peopleISupport().map((person) => person.id)).toContain('sam')

    // And off the list again.
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Stop supporting Sam' }))
    })
    expect(screen.queryByRole('button', { name: 'Stop supporting Sam' })).toBeNull()
    expect(peopleISupport().map((person) => person.id)).not.toContain('sam')
  })

  it('forgets the role when the demo is reset', async () => {
    await act(async () => { render(<App />) })
    expect(await screen.findByRole('heading', { level: 2, name: 'Unit overview' })).toBeTruthy()

    // The role is cleared before the pipeline is asked to reset, which offline it
    // refuses: "Reset demo" must start the demo over whether or not the API answers.
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Reset demo' })) })

    expect(screen.getByRole('heading', { name: 'Who is this for?' })).toBeTruthy()
    expect(getRole()).toBeNull()
  })
})
