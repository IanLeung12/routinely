import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { DemoBanner } from './DemoBanner.tsx'

afterEach(cleanup)

describe('DemoBanner', () => {
  it('labels the synthetic data and review-only flags in a note', () => {
    render(<DemoBanner onReset={vi.fn()} />)
    expect(screen.getByRole('note').textContent).toContain('Demo mode: synthetic residents, no real patient data. Changes are flagged for review only.')
    expect(screen.queryByRole('button', { name: 'Dismiss' })).toBeNull()
  })

  it('offers dismissal only when a callback is supplied', () => {
    const onDismiss = vi.fn()
    render(<DemoBanner onDismiss={onDismiss} onReset={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Dismiss' }))
    expect(onDismiss).toHaveBeenCalledOnce()
  })

  it('resets the demo and reloads on success', async () => {
    const onReset = vi.fn().mockResolvedValue(undefined)
    render(<DemoBanner onReset={onReset} />)
    const button = screen.getByRole('button', { name: 'Reset demo' }) as HTMLButtonElement
    fireEvent.click(button)
    expect(onReset).toHaveBeenCalledOnce()
    await waitFor(() => expect(button.disabled).toBe(false))
    expect(screen.queryByText("Couldn't reset the demo")).toBeNull()
  })

  it('disables the button while the reset is in flight', async () => {
    let resolveReset: () => void = () => {}
    const onReset = vi.fn(() => new Promise<void>((resolve) => { resolveReset = resolve }))
    render(<DemoBanner onReset={onReset} />)
    const button = screen.getByRole('button', { name: 'Reset demo' }) as HTMLButtonElement
    fireEvent.click(button)
    await waitFor(() => expect(button.disabled).toBe(true))
    await act(async () => { resolveReset() })
  })

  it('shows inline error text and does not throw when the reset fails', async () => {
    const onReset = vi.fn().mockRejectedValue(new Error('demo reset failed: 404'))
    render(<DemoBanner onReset={onReset} />)
    const button = screen.getByRole('button', { name: 'Reset demo' }) as HTMLButtonElement
    fireEvent.click(button)
    await screen.findByText("Couldn't reset the demo")
    await waitFor(() => expect(button.disabled).toBe(false))
  })

  it('announces the reset error to screen readers', async () => {
    const onReset = vi.fn().mockRejectedValue(new Error('demo reset failed: 404'))
    render(<DemoBanner onReset={onReset} />)
    fireEvent.click(screen.getByRole('button', { name: 'Reset demo' }))
    const alert = await screen.findByRole('alert')
    expect(alert.textContent).toContain("Couldn't reset the demo")
  })

  it('disables the button while resetting and re-enables once resolved', async () => {
    let resolveReset: () => void = () => {}
    const onReset = vi.fn(() => new Promise<void>((resolve) => { resolveReset = resolve }))
    render(<DemoBanner onReset={onReset} />)
    const button = screen.getByRole('button', { name: 'Reset demo' }) as HTMLButtonElement
    fireEvent.click(button)
    await waitFor(() => expect(button.disabled).toBe(true))
    await act(async () => { resolveReset() })
    await waitFor(() => expect(button.disabled).toBe(false))
  })

  it('clears a previous reset error once a later reset succeeds', async () => {
    const onReset = vi.fn()
      .mockRejectedValueOnce(new Error('demo reset failed: 404'))
      .mockResolvedValueOnce(undefined)
    render(<DemoBanner onReset={onReset} />)
    fireEvent.click(screen.getByRole('button', { name: 'Reset demo' }))
    await screen.findByRole('alert')

    fireEvent.click(screen.getByRole('button', { name: 'Reset demo' }))
    await vi.waitFor(() => expect(screen.queryByRole('alert')).toBeNull())
  })
})

describe('default onReset', () => {
  it('POSTs /demo/reset and reloads on success, or shows the error text on failure', async () => {
    const reload = vi.fn()
    vi.stubGlobal('location', { ...window.location, reload })
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce({ ok: false, status: 404 })
    vi.stubGlobal('fetch', fetchMock)

    render(<DemoBanner />)
    fireEvent.click(screen.getByRole('button', { name: 'Reset demo' }))
    await waitFor(() => expect(reload).toHaveBeenCalledOnce())
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/demo/reset'), { method: 'POST' })

    cleanup()
    render(<DemoBanner />)
    fireEvent.click(screen.getByRole('button', { name: 'Reset demo' }))
    await screen.findByText("Couldn't reset the demo")
    expect(reload).toHaveBeenCalledOnce()

    vi.unstubAllGlobals()
  })
})
