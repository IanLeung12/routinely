import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { DriftCard } from './DriftCard.tsx'

afterEach(cleanup)

describe('DriftCard at phone width', () => {
  it('renders with its existing class names at 375px', () => {
    window.innerWidth = 375
    render(<DriftCard slopePerDay={0.2} days={14} trending />)
    const region = screen.getByRole('region')
    expect(region.classList.contains('drift-card')).toBe(true)
    expect(screen.getByText(/Flagged for review/).classList.contains('drift-card__summary')).toBe(true)
  })
})
