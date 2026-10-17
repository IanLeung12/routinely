import { useState } from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { PrivacyPanel } from './PrivacyPanel.tsx'
import { MonitoringToggle } from './MonitoringToggle.tsx'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

/** A minimal host that opens/closes the privacy panel and wires up the room
 * monitoring toggle, the way a real screen would place them together. */
function Host() {
  const [open, setOpen] = useState(false)
  const [on, setOn] = useState(true)

  return (
    <div>
      <button onClick={() => setOpen((v) => !v)}>{open ? 'Close privacy info' : 'Privacy info'}</button>
      {open && <PrivacyPanel />}
      <MonitoringToggle room="101" on={on} onChange={setOn} />
    </div>
  )
}

describe('Privacy panel and monitoring toggle keyboard access', () => {
  it('opens the panel, reaches the toggle, and pauses then resumes without losing focus', async () => {
    const user = userEvent.setup()
    render(<Host />)

    const openButton = screen.getByRole('button', { name: 'Privacy info' })
    openButton.focus()
    expect(document.activeElement).toBe(openButton)

    await user.keyboard('{Enter}')
    expect(document.activeElement).toBe(openButton)
    expect(screen.getByRole('heading', { level: 3, name: 'Privacy and limits' })).toBeTruthy()

    await user.keyboard('{Enter}')
    expect(screen.queryByRole('heading', { level: 3, name: 'Privacy and limits' })).toBeNull()
    expect(document.activeElement).toBe(openButton)

    const toggle = screen.getByRole('switch', { name: 'Monitoring in room 101' })
    await user.tab()
    expect(document.activeElement).toBe(toggle)
    expect(toggle.getAttribute('aria-checked')).toBe('true')

    await user.keyboard(' ')
    expect(document.activeElement).toBe(toggle)
    expect(toggle.getAttribute('aria-checked')).toBe('false')
    expect(screen.getByText('No camera data is processed while paused.')).toBeTruthy()

    await user.keyboard(' ')
    expect(document.activeElement).toBe(toggle)
    expect(toggle.getAttribute('aria-checked')).toBe('true')
    expect(screen.queryByText('No camera data is processed while paused.')).toBeNull()
  })
})
