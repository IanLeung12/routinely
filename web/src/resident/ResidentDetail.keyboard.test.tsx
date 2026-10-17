import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ResidentDetail } from './ResidentDetail.tsx'

function offline() {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')))
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
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

/** Tabs forward through every interactive stop, asserting each has an accessible name
 * (a nurse tabbing through the page must always hear something), and returns how many
 * stops it visited before cycling back to the first one (or hitting `max`). */
async function tabThroughAll(user: ReturnType<typeof userEvent.setup>, max = 60) {
  // The page autofocuses the h1 on load (T228); blur it so Tab starts from the top
  // of the document instead of skipping stops that come before it in DOM order.
  ;(document.activeElement as HTMLElement | null)?.blur()
  const first = document.activeElement
  await user.tab()
  const seen: Element[] = []
  for (let i = 0; i < max; i++) {
    const active = document.activeElement
    if (!active || active === document.body) break
    if (seen.includes(active)) break
    expect(accessibleName(active)).not.toBe('')
    seen.push(active)
    if (active === first) break
    await user.tab()
  }
  return seen
}

describe('ResidentDetail keyboard access', () => {
  it('reaches every interactive element by Tab, each with an accessible name', async () => {
    offline()
    const user = userEvent.setup()

    render(<ResidentDetail residentId="mrs-k" onBack={() => {}} />)
    await screen.findByRole('heading', { level: 1, name: 'Mrs. K' })

    const backButton = screen.getByRole('button', { name: /unit overview/i })
    const monitoringSwitch = await screen.findByRole('switch', { name: 'Monitoring in room 204' })

    const stops = await tabThroughAll(user)
    expect(stops).toContain(backButton)
    expect(stops).toContain(monitoringSwitch)
  })

  it('calls onBack when the back control is focused and Enter is pressed', async () => {
    offline()
    const user = userEvent.setup()
    const onBack = vi.fn()

    render(<ResidentDetail residentId="mrs-k" onBack={onBack} />)
    const backButton = await screen.findByRole('button', { name: /unit overview/i })

    ;(document.activeElement as HTMLElement | null)?.blur()
    while (document.activeElement !== backButton) {
      await user.tab()
    }

    await user.keyboard('{Enter}')

    expect(onBack).toHaveBeenCalledTimes(1)
  })
})
