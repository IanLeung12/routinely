import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MonitoringToggle } from './MonitoringToggle'

describe('MonitoringToggle', () => {
  afterEach(cleanup)

  it.each([true, false])('reflects monitoring state %s and requests the opposite state', (on) => {
    const onChange = vi.fn()
    render(<MonitoringToggle room="101" on={on} onChange={onChange} />)

    const toggle = screen.getByRole('switch', { name: 'Monitoring in room 101' })
    expect(toggle.getAttribute('aria-checked')).toBe(String(on))
    expect(toggle.textContent).toBe(on ? 'On' : 'Paused')
    expect(screen.queryByText('No camera data is processed while paused.') !== null).toBe(!on)

    fireEvent.click(toggle)
    expect(onChange).toHaveBeenCalledExactlyOnceWith(!on)
    expect(toggle.getAttribute('aria-checked')).toBe(String(on))
  })
})
