import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { mockAlerts } from '../mock/alerts.ts'
import { AlertView } from './AlertView.tsx'

const MRS_K = mockAlerts[0]

function offline() {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')))
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  mockAlerts[0].feedback = null
})

/** The accessible-name algorithm for the handful of attributes this screen's controls
 * use: an explicit aria-label, an aria-labelledby reference, or the element's own text. */
function accessibleName(el: Element | null): string {
  if (!el) return ''
  const ariaLabel = el.getAttribute('aria-label')
  if (ariaLabel?.trim()) return ariaLabel.trim()
  const labelledBy = el.getAttribute('aria-labelledby')
  if (labelledBy) {
    const text = labelledBy
      .split(/\s+/)
      .map((id) => document.getElementById(id)?.textContent ?? '')
      .join(' ')
      .trim()
    if (text) return text
  }
  return (el.textContent ?? '').trim()
}

/** Tabs forward until `target` has focus, asserting every stop along the way has an
 * accessible name: a nurse tabbing through the alert must always hear something. */
async function tabTo(user: ReturnType<typeof userEvent.setup>, target: Element, max = 40) {
  for (let i = 0; i < max && document.activeElement !== target; i++) {
    await user.tab()
    expect(accessibleName(document.activeElement)).not.toBe('')
  }
  expect(document.activeElement).toBe(target)
}

describe('AlertView keyboard access', () => {
  it('tabs from the top of the alert to Confirmed and confirms it with Enter', async () => {
    offline()
    const user = userEvent.setup()

    render(<AlertView alertId={MRS_K.alert_id} onBack={() => {}} />)
    await screen.findByText(MRS_K.summary)
    await screen.findByRole('button', { name: /play/i })

    const confirmedButton = screen.getByRole('button', { name: 'Confirmed' })
    await tabTo(user, confirmedButton)

    await user.keyboard('{Enter}')

    expect(await screen.findByText('Marked as confirmed')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Confirmed' }).getAttribute('aria-pressed')).toBe('true')

    const causeGroup = await screen.findByRole('group', { name: 'What was it? (optional)' })
    const suddenChange = within(causeGroup).getByRole('button', { name: 'Sudden change' })
    await tabTo(user, suddenChange)

    await user.keyboard(' ')

    expect(screen.getByRole('button', { name: 'Sudden change' }).getAttribute('aria-pressed')).toBe('true')
  })

  it('tabs to False alarm and confirms it with Space', async () => {
    offline()
    const user = userEvent.setup()

    render(<AlertView alertId={MRS_K.alert_id} onBack={() => {}} />)
    await screen.findByText(MRS_K.summary)
    await screen.findByRole('button', { name: /play/i })

    const falseAlarmButton = screen.getByRole('button', { name: 'False alarm' })
    await tabTo(user, falseAlarmButton)

    await user.keyboard(' ')

    expect(await screen.findByText('Marked as false alarm')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'False alarm' }).getAttribute('aria-pressed')).toBe('true')
  })
})
