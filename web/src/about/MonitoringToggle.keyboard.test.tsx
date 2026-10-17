import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MonitoringToggle } from './MonitoringToggle'

afterEach(cleanup)

describe('MonitoringToggle keyboard access', () => {
  it.each([' ', '{Enter}'])('pauses and resumes with %s', async (key) => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    const { rerender } = render(<MonitoringToggle room="101" on={true} onChange={onChange} />)
    const toggle = screen.getByRole('switch', { name: 'Monitoring in room 101' })

    await user.tab()
    expect(document.activeElement).toBe(toggle)
    expect(toggle.getAttribute('aria-checked')).toBe('true')
    expect(screen.queryByText('No camera data is processed while paused.')).toBeNull()

    await user.keyboard(key)
    expect(onChange).toHaveBeenCalledExactlyOnceWith(false)
    rerender(<MonitoringToggle room="101" on={false} onChange={onChange} />)
    expect(toggle.getAttribute('aria-checked')).toBe('false')
    expect(screen.getByText('No camera data is processed while paused.')).toBeTruthy()
    expect(document.activeElement).toBe(toggle)

    onChange.mockClear()
    await user.keyboard(key)
    expect(onChange).toHaveBeenCalledExactlyOnceWith(true)
    rerender(<MonitoringToggle room="101" on={true} onChange={onChange} />)
    expect(toggle.getAttribute('aria-checked')).toBe('true')
    expect(screen.queryByText('No camera data is processed while paused.')).toBeNull()
    expect(document.activeElement).toBe(toggle)
  })
})
