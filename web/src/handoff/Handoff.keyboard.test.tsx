import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { UserEvent } from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Alert } from '../contracts.ts'
import { mockAlerts } from '../mock/alerts.ts'
import { Handoff } from './Handoff.tsx'
import type { Handoff as HandoffData } from './types.ts'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

const alerts: Alert[] = [
  { ...mockAlerts[0], alert_id: 'mrs-k-change-1', resident_id: 'mrs-k' },
]

const served: HandoffData = {
  window_hours: 12,
  residents: [
    { resident_id: 'mrs-k', name: 'Mrs. K', room: '204', flags: 2, pending_review: 1, trending: false },
    { resident_id: 'mr-chen', name: 'Mr. Chen', room: '211', flags: 0, pending_review: 0, trending: true },
  ],
  paused: [],
  summary: 'Flagged for review: 2 errors this session vs 0.58 normally over 14 days.',
}

function serve(handoff: HandoffData, alertList: Alert[] = alerts) {
  const fetch = vi.fn().mockImplementation((url: string) => {
    if (url.includes('/alerts')) {
      return Promise.resolve({ ok: true, json: async () => alertList })
    }
    if (url.includes('/residents/')) {
      return Promise.resolve({ ok: false })
    }
    return Promise.resolve({ ok: true, json: async () => handoff })
  })
  vi.stubGlobal('fetch', fetch)
  return fetch
}

/** The accessible-name algorithm for the controls this screen renders: an explicit
 * aria-label or the element's own text. */
function accessibleName(el: Element | null): string {
  if (!el) return ''
  const ariaLabel = el.getAttribute('aria-label')
  if (ariaLabel?.trim()) return ariaLabel.trim()
  return (el.textContent ?? '').trim()
}

/** Tabs forward until `target` has focus, asserting every stop along the way has an
 * accessible name: a nurse tabbing through the handoff must always hear something. */
async function tabTo(user: UserEvent, target: Element, max = 20) {
  for (let i = 0; i < max && document.activeElement !== target; i++) {
    await user.tab()
    expect(accessibleName(document.activeElement)).not.toBe('')
  }
  expect(document.activeElement).toBe(target)
}

describe('Handoff keyboard access', () => {
  it.each(['{Enter}', ' '])('tabs from Copy summary to Print handoff and prints once with %j', async (key) => {
    serve(served)
    const printSpy = vi.fn()
    vi.stubGlobal('print', printSpy)
    const user = userEvent.setup()

    render(<Handoff onBack={() => {}} />)
    await screen.findByText(served.summary)

    await tabTo(user, screen.getByRole('button', { name: 'Copy summary' }))
    await user.tab()
    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Print handoff' }))
    expect(printSpy).not.toHaveBeenCalled()

    await user.keyboard(key)
    expect(printSpy).toHaveBeenCalledTimes(1)
  })

  it('tabs in DOM order to each open-alert button and activates it with Enter', async () => {
    serve(served)
    const onOpenAlert = vi.fn()
    const user = userEvent.setup()

    render(<Handoff onBack={() => {}} onOpenAlert={onOpenAlert} />)
    await screen.findByText(served.summary)

    const backButton = screen.getByRole('button', { name: /Back/ })
    // Every window is its own tab stop, so a nurse can pick one without a mouse.
    const windows = screen.getByRole('group', { name: 'Window' })
    const firstWindow = within(windows).getByRole('button', { name: '8h' })
    const lastWindow = within(windows).getByRole('button', { name: '48h' })
    const copyButton = screen.getByRole('button', { name: 'Copy summary' })
    const openAlertButton = await screen.findByRole('button', { name: "Open Mrs. K's alert" })

    await tabTo(user, backButton)
    await tabTo(user, firstWindow)
    await tabTo(user, lastWindow)
    await tabTo(user, copyButton)
    await tabTo(user, openAlertButton)

    await user.keyboard('{Enter}')

    expect(onOpenAlert).toHaveBeenCalledWith('mrs-k-change-1')
  })

  it('gives every focusable control an accessible name', async () => {
    serve(served)
    const user = userEvent.setup()

    render(<Handoff onBack={() => {}} onOpenAlert={vi.fn()} />)
    await screen.findByText(served.summary)
    await screen.findByRole('button', { name: "Open Mrs. K's alert" })

    for (let i = 0; i < 6; i++) {
      await user.tab()
      expect(accessibleName(document.activeElement)).not.toBe('')
    }
  })
})
