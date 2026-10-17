import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { UserEvent } from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Alert } from '../contracts.ts'
import { mockAlerts } from '../mock/alerts.ts'
import { Handoff, handoffText } from './Handoff.tsx'
import { mockHandoff } from './mockHandoff.ts'
import type { Handoff as HandoffData } from './types.ts'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

/** Two of Mrs. K's alerts, and one for Mr. Chen, whose row has nothing pending yet:
 * `/alerts` lists every flagged resident's alert whatever the handoff's window, so the
 * row's own count is what decides whether there is an alert waiting to be opened. */
const alerts: Alert[] = [
  { ...mockAlerts[0], alert_id: 'mrs-k-change-1', resident_id: 'mrs-k' },
  { ...mockAlerts[0], alert_id: 'mrs-k-change-2', resident_id: 'mrs-k' },
  { ...mockAlerts[0], alert_id: 'mr-chen-trend-1', resident_id: 'mr-chen' },
]

/** The screen reads three routes: `/handoff` for the rows, `/alerts` for the alert
 * each row opens, and `/residents/{id}` for the baseline line on each row. A resident
 * not in `residents` gets a 404, same as the real API for an id it doesn't know, so
 * `resident/api.ts` falls back to its own offline mock rather than this test needing
 * to fake every row's detail. */
function serve(
  handoff: HandoffData,
  alertList: Alert[] = alerts,
  residents: Record<string, unknown> = {},
  history: Record<string, unknown> = {},
) {
  const fetch = vi.fn().mockImplementation((url: string) => {
    if (url.includes('/alerts')) {
      return Promise.resolve({ ok: true, json: async () => alertList })
    }
    const historyMatch = /\/rooms\/([^/]+)\/monitoring\/history$/.exec(url)
    if (historyMatch) {
      const room = decodeURIComponent(historyMatch[1])
      if (room in history) {
        const entry = history[room]
        if (entry === false) return Promise.resolve({ ok: false })
        return Promise.resolve({ ok: true, json: async () => ({ history: entry }) })
      }
      return Promise.resolve({ ok: true, json: async () => ({ history: [] }) })
    }
    const residentMatch = /\/residents\/([^/]+)$/.exec(url)
    if (residentMatch) {
      const resident = residents[residentMatch[1]]
      return Promise.resolve(
        resident === undefined ? { ok: false } : { ok: true, json: async () => resident },
      )
    }
    return Promise.resolve({ ok: true, json: async () => handoff })
  })
  vi.stubGlobal('fetch', fetch)
  return fetch
}

function offline() {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network down')))
}

/** Press Tab (or Shift+Tab) until `target` has focus. Bounded by more presses than
 * the screen has stops: a control a keyboard-only nurse can never reach is the bug
 * this exists to catch, and an unbounded loop would hang the suite instead of
 * naming it. */
async function tabTo(user: UserEvent, target: HTMLElement, { shift = false } = {}) {
  for (let presses = 0; presses < 12; presses += 1) {
    await user.tab({ shift })
    if (document.activeElement === target) return
  }
  throw new Error(`"${target.textContent}" is not reachable with ${shift ? 'Shift+Tab' : 'Tab'}`)
}

const served: HandoffData = {
  window_hours: 12,
  residents: [
    { resident_id: 'mrs-k', name: 'Mrs. K', room: '204', flags: 2, pending_review: 1, trending: false },
    { resident_id: 'mr-chen', name: 'Mr. Chen', room: '211', flags: 0, pending_review: 0, trending: true },
    { resident_id: 'mrs-ahmed', name: 'Mrs. Ahmed', room: '108', flags: 0, pending_review: 0, trending: false },
  ],
  paused: [],
  summary: 'Flagged for review: 2 errors this session vs 0.58 normally over 14 days.',
}

describe('Handoff', () => {
  it('formats the summary and one complete line per resident', () => {
    const text = handoffText(mockHandoff)
    expect(text.split('\n')[0]).toBe(mockHandoff.summary)
    expect(text.split('\n')).toHaveLength(mockHandoff.residents.length + 1)
    for (const resident of mockHandoff.residents) {
      // Name and room: a pasted handoff has to say who and where, with no gaps.
      expect(text).toContain(`${resident.name}, Room ${resident.room}:`)
    }
    expect(text).toContain('Mrs. K, Room 204: 2 flagged sessions, 1 unreviewed alert, No upward trend')
    expect(text).toContain('Error score trending up')
    expect(text).not.toMatch(/diagnos/i)
    expect(text).not.toMatch(/unavailable/i)
  })

  it('copies the handoff and announces success for two seconds', async () => {
    serve(served)
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    render(<Handoff onBack={() => {}} />)
    await screen.findByText(served.summary)
    vi.useFakeTimers()

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Copy summary' }))
    })

    expect(writeText).toHaveBeenCalledWith(handoffText(served))
    expect(screen.getByText('Copied').getAttribute('role')).toBe('status')
    act(() => { vi.advanceTimersByTime(2000) })
    expect(screen.queryByText('Copied')).toBeNull()
  })

  it.each([undefined, { writeText: vi.fn().mockRejectedValue(new Error('denied')) }])(
    'shows a fallback when copying is unavailable or rejected', async (clipboard) => {
      serve(served)
      vi.stubGlobal('navigator', { clipboard })
      render(<Handoff onBack={() => {}} />)
      await screen.findByText(served.summary)

      fireEvent.click(screen.getByRole('button', { name: 'Copy summary' }))

      expect((await screen.findByText('Copy not available')).getAttribute('role')).toBe('status')
    },
  )

  it('renders the list and the summary from the mock data when the API is unreachable', async () => {
    offline()

    render(<Handoff onBack={() => {}} />)

    expect(await screen.findByText(mockHandoff.summary)).toBeTruthy()
    for (const resident of mockHandoff.residents) {
      expect(screen.getByText(resident.name)).toBeTruthy()
    }
    expect(screen.getAllByRole('listitem')).toHaveLength(mockHandoff.residents.length)
    expect(screen.getByRole('alert').textContent).toContain('Offline')
  })

  it("shows each resident's room on their row", async () => {
    serve(served)

    render(<Handoff onBack={() => {}} />)

    const kRow = (await screen.findByText('Mrs. K')).closest('li')
    expect(kRow?.textContent).toContain('Room 204')
    expect(screen.getByText('Mr. Chen').closest('li')?.textContent).toContain('Room 211')
    expect(screen.queryByText(/unavailable/i)).toBeNull()
  })

  it('shows what each resident did in words, not colour alone', async () => {
    serve(served)

    render(<Handoff onBack={() => {}} />)

    expect(await screen.findByText('2 sessions above baseline')).toBeTruthy()
    expect(screen.getByText('1 alert not reviewed yet')).toBeTruthy()
    expect(screen.getByText('Error score trending up')).toBeTruthy()
    expect(screen.getByText('No change flagged')).toBeTruthy()
  })

  it("reads each row against that resident's own normal, not a shared one", async () => {
    serve(served, alerts, {
      'mrs-k': { sessions: [{}], baseline: { mean: 1.46 } },
      'mrs-ahmed': { sessions: [], baseline: { mean: 0 } },
    })

    render(<Handoff onBack={() => {}} />)

    expect(await screen.findByText('Usually 1.5 errors a session')).toBeTruthy()
    // Mrs. Ahmed has no session history yet: no baseline line at all, never a false
    // "0" or a "NaN" from averaging nothing.
    const ahmedRow = screen.getByText('Mrs. Ahmed').closest('li')
    expect(ahmedRow?.textContent).not.toMatch(/Usually/)
    expect(screen.queryByText(/Usually 0(\.0)? errors a session/)).toBeNull()
    expect(screen.queryByText(/NaN/)).toBeNull()
  })

  it('leads with how many residents need a look', async () => {
    serve(served)

    render(<Handoff onBack={() => {}} />)

    const headline = await screen.findByText('2 of 3 residents to review in the last 12 hours')
    expect(headline.getAttribute('role')).toBe('status')
  })

  it('says so when nothing was flagged for review', async () => {
    serve({
      window_hours: 12,
      residents: [{ resident_id: 'mrs-k', name: 'Mrs. K', room: '204', flags: 0, pending_review: 0, trending: false }],
      paused: [],
      summary: 'No errors this session vs 0.58 normally over 14 days.',
    })

    render(<Handoff onBack={() => {}} />)

    const headline = await screen.findByText('No change flagged for review in the last 12 hours')
    expect(headline.getAttribute('role')).toBe('status')
  })

  it('shows an empty state for a unit with no residents', async () => {
    serve({ window_hours: 12, residents: [], paused: [], summary: 'Nothing to report.' })

    render(<Handoff onBack={() => {}} />)

    expect(await screen.findByText('No residents on this unit yet.')).toBeTruthy()
    expect(screen.queryAllByRole('listitem')).toHaveLength(0)
  })

  it('loads before it has anything to show', async () => {
    serve(served)

    render(<Handoff onBack={() => {}} />)

    expect(screen.getByRole('status').textContent).toBe('Loading handoff…')
    await screen.findByText(served.summary)
  })

  it('refetches when the nurse picks another window', async () => {
    const twelve: HandoffData = { ...served, window_hours: 12 }
    const day: HandoffData = {
      ...served,
      window_hours: 24,
      summary: 'Flagged for review: a longer window.',
    }
    const fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/residents/')) return Promise.resolve({ ok: false })
      return Promise.resolve({
        ok: true,
        json: async () => {
          if (url.includes('/alerts')) return alerts
          return url.includes('hours=24') ? day : twelve
        },
      })
    })
    vi.stubGlobal('fetch', fetch)

    render(<Handoff onBack={() => {}} />)
    await screen.findByText(twelve.summary)

    fireEvent.change(screen.getByLabelText('Window'), { target: { value: '24' } })

    expect(await screen.findByText(day.summary)).toBeTruthy()
    expect(await screen.findByRole('heading', { name: 'Last 24 hours' })).toBeTruthy()
    expect(fetch.mock.calls.map(([url]) => url as string).some(url => url.includes('hours=24'))).toBe(true)
  })

  it("opens the resident's own alert from their row", async () => {
    serve(served)
    const onOpenAlert = vi.fn()

    render(<Handoff onBack={() => {}} onOpenAlert={onOpenAlert} />)

    const open = await screen.findByRole('button', { name: "Open Mrs. K's alert" })
    expect(open.textContent).toBe('Open alert')

    fireEvent.click(open)

    expect(onOpenAlert).toHaveBeenCalledWith('mrs-k-change-1')
  })

  it('offers the alert only on rows with one still to review', async () => {
    serve(served)

    render(<Handoff onBack={() => {}} onOpenAlert={vi.fn()} />)

    await screen.findByRole('button', { name: "Open Mrs. K's alert" })
    // Mr. Chen has an alert of his own but nothing left to review this window, and
    // Mrs. Ahmed has nothing at all: neither row sends a nurse to an alert screen.
    expect(screen.queryByRole('button', { name: "Open Mr. Chen's alert" })).toBeNull()
    expect(screen.queryByRole('button', { name: "Open Mrs. Ahmed's alert" })).toBeNull()
    expect(screen.getAllByRole('button', { name: /^Open .*alert$/ })).toHaveLength(1)
  })

  it('offers nothing to tap when the list has no alert for that resident', async () => {
    serve({
      ...served,
      residents: [
        { resident_id: 'mrs-k', name: 'Mrs. K', room: '204', flags: 2, pending_review: 1, trending: false },
        { resident_id: 'mr-nguyen', name: 'Mr. Nguyen', room: '126', flags: 0, pending_review: 1, trending: false },
      ],
    })

    render(<Handoff onBack={() => {}} onOpenAlert={vi.fn()} />)

    // Mrs. K's button proves the alerts have arrived; the list holds none of
    // Mr. Nguyen's, so his row offers a nurse no button rather than a dead one.
    await screen.findByRole('button', { name: "Open Mrs. K's alert" })
    expect(screen.getByText('Mr. Nguyen')).toBeTruthy()
    expect(screen.queryByRole('button', { name: "Open Mr. Nguyen's alert" })).toBeNull()
  })

  it('offers no alert when the screen has nowhere to send a nurse', async () => {
    serve(served)

    const { rerender } = render(<Handoff onBack={() => {}} onOpenAlert={vi.fn()} />)
    await screen.findByRole('button', { name: "Open Mrs. K's alert" })

    rerender(<Handoff onBack={() => {}} />)

    expect(screen.queryByRole('button', { name: "Open Mrs. K's alert" })).toBeNull()
  })

  it('copies and goes back with no mouse, on Tab and Enter alone', async () => {
    serve(served)
    const writeText = vi.fn().mockResolvedValue(undefined)
    const onBack = vi.fn()
    // Before the navigator stub: `setup` plants its own clipboard on the real one.
    const user = userEvent.setup()
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    render(<Handoff onBack={onBack} />)
    await screen.findByText(served.summary)

    await tabTo(user, screen.getByRole('button', { name: 'Copy summary' }))
    await user.keyboard('{Enter}')

    expect(writeText).toHaveBeenCalledWith(handoffText(served))
    expect((await screen.findByText('Copied')).getAttribute('role')).toBe('status')

    // Back sits above the summary, so Shift+Tab is the way a nurse returns to it.
    await tabTo(user, screen.getByRole('button', { name: /Back/ }), { shift: true })
    await user.keyboard('{Enter}')

    expect(onBack).toHaveBeenCalledOnce()
  })

  it('goes back when asked', async () => {
    serve(served)
    const onBack = vi.fn()

    render(<Handoff onBack={onBack} />)
    await screen.findByText(served.summary)

    fireEvent.click(screen.getByRole('button', { name: /Back/ }))

    expect(onBack).toHaveBeenCalledOnce()
  })

  it('shows no paused line or chip when nothing is paused', async () => {
    serve(served)

    render(<Handoff onBack={() => {}} />)
    await screen.findByText(served.summary)

    expect(screen.queryByText(/Monitoring paused/)).toBeNull()
  })

  it('shows the paused room above the rows and a chip on its resident', async () => {
    serve({
      ...served,
      residents: [
        { resident_id: 'mrs-k', name: 'Mrs. K', room: '204', flags: 2, pending_review: 1, trending: false },
        {
          resident_id: 'mr-chen',
          name: 'Mr. Chen',
          room: '4',
          flags: 0,
          pending_review: 0,
          trending: false,
          monitoring_paused: true,
        },
      ],
      paused: [{ room: '4', resident_id: 'mr-chen', name: 'Mr. Chen' }],
    })

    render(<Handoff onBack={() => {}} />)

    expect(await screen.findByText('Monitoring paused: Mr. Chen (room 4)')).toBeTruthy()
    const chenRow = (await screen.findByText('Mr. Chen')).closest('li')
    expect(chenRow?.textContent).toContain('Monitoring paused')
    // Mrs. K's row is unaffected: the chip is per resident, not unit-wide.
    const kRow = screen.getByText('Mrs. K').closest('li')
    expect(kRow?.textContent).not.toContain('Monitoring paused')
  })

  it('shows who paused a room and when, from its audit trail', async () => {
    serve(
      {
        ...served,
        residents: [
          { resident_id: 'mrs-k', name: 'Mrs. K', room: '204', flags: 0, pending_review: 0, trending: false, monitoring_paused: true },
        ],
        paused: [{ room: '204', resident_id: 'mrs-k', name: 'Mrs. K' }],
      },
      alerts,
      {},
      {
        '204': [
          { on: false, by: 'nurse', at: '2026-10-17T13:40:00Z' },
          { on: true, by: 'nurse', at: '2026-10-17T09:00:00Z' },
        ],
      },
    )

    render(<Handoff onBack={() => {}} />)

    expect(
      await screen.findByText('Monitoring paused: Mrs. K (room 204), paused by nurse at 13:40'),
    ).toBeTruthy()
  })

  it('keeps the plain paused line when the history fetch fails', async () => {
    serve(
      {
        ...served,
        residents: [
          { resident_id: 'mrs-k', name: 'Mrs. K', room: '204', flags: 0, pending_review: 0, trending: false, monitoring_paused: true },
        ],
        paused: [{ room: '204', resident_id: 'mrs-k', name: 'Mrs. K' }],
      },
      alerts,
      {},
      { '204': false },
    )

    render(<Handoff onBack={() => {}} />)

    expect(await screen.findByText('Monitoring paused: Mrs. K (room 204)')).toBeTruthy()
  })

  it('makes no history calls when no room is paused', async () => {
    const fetch = serve(served)

    render(<Handoff onBack={() => {}} />)
    await screen.findByText(served.summary)

    expect(fetch.mock.calls.some(([url]) => (url as string).includes('/monitoring/history'))).toBe(false)
  })

  it('includes the paused room in the copied handoff text', () => {
    const data: HandoffData = {
      ...mockHandoff,
      paused: [{ room: '211', resident_id: 'mr-chen', name: 'Mr. Chen' }],
    }

    const text = handoffText(data)

    expect(text).toContain('Monitoring paused: Mr. Chen (room 211)')
    expect(text).toContain('Mr. Chen, Room 211:')
  })

  it('keeps review wording and theme tokens, offline and online', async () => {
    offline()

    const { container } = render(<Handoff onBack={() => {}} />)
    await screen.findByText(mockHandoff.summary)

    expect(container.textContent).not.toMatch(/diagnos/i)
    expect(container.textContent).toMatch(/flagged for review/i)
    for (const element of container.querySelectorAll('[style]')) {
      expect(element.getAttribute('style')).not.toMatch(/#[\da-f]{3,8}\b|hsl\(/i)
    }
  })
})
