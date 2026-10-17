import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { DemoBanner } from './DemoBanner.tsx'

afterEach(cleanup)

describe('DemoBanner', () => {
  it('labels the synthetic data and review-only flags in a note', () => {
    render(<DemoBanner />)
    expect(screen.getByRole('note').textContent).toBe('Demo mode: synthetic residents, no real patient data. Changes are flagged for review only.')
    expect(screen.queryByRole('button')).toBeNull()
  })

  it('offers dismissal only when a callback is supplied', () => {
    const onDismiss = vi.fn()
    render(<DemoBanner onDismiss={onDismiss} />)
    fireEvent.click(screen.getByRole('button', { name: 'Dismiss' }))
    expect(onDismiss).toHaveBeenCalledOnce()
  })
})
