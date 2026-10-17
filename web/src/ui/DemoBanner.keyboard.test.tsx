import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { DemoBanner } from './DemoBanner.tsx'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('DemoBanner keyboard access', () => {
  it.each(['{Enter}', ' '])('resets once with %j and keeps keyboard focus on the button', async (key) => {
    const reload = vi.fn()
    const fetchMock = vi.fn().mockResolvedValue({ ok: true })
    vi.stubGlobal('location', { ...window.location, reload })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<DemoBanner />)

    const button = screen.getByRole('button', { name: 'Reset demo' }) as HTMLButtonElement
    await user.tab()
    expect(document.activeElement).toBe(button)
    expect(fetchMock).not.toHaveBeenCalled()

    await user.keyboard(key)
    await waitFor(() => {
      expect(reload).toHaveBeenCalledOnce()
      expect(button.disabled).toBe(false)
    })
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/demo/reset'), { method: 'POST' })
    expect(screen.getByRole('button', { name: 'Reset demo' })).toBe(button)
    expect(document.activeElement).toBe(button)
  })
})
