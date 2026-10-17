import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { DriftCard } from './DriftCard.tsx'

afterEach(cleanup)

describe('DriftCard', () => {
  it('shows insufficient history before considering a rising trend', () => {
    render(<DriftCard slopePerDay={0.2} days={5} trending />)
    expect(screen.getByText('Not enough history yet (5 of 7 days)')).toBeTruthy()
    expect(screen.getByRole('region').getAttribute('data-state')).toBe('insufficient')
  })

  it('uses a custom minimum history', () => {
    render(<DriftCard slopePerDay={0.2} days={7} trending minDays={14} />)
    expect(screen.getByText('Not enough history yet (7 of 14 days)')).toBeTruthy()
  })

  it('shows a review flag and rounds the daily slope to two decimal places', () => {
    render(<DriftCard slopePerDay={0.146} days={14} trending />)
    expect(screen.getByRole('heading', { name: 'Slow drift' })).toBeTruthy()
    const summary = screen.getByText('Error score rising about +0.15 per day over 14 days. Flagged for review.')
    expect(summary.classList.contains('drift-card__summary')).toBe(true)
    expect(screen.getByRole('region').getAttribute('data-state')).toBe('trending')
  })

  it('shows stable history at the minimum-day boundary', () => {
    render(<DriftCard slopePerDay={0} days={7} trending={false} />)
    expect(screen.getByText('No slow drift over 7 days')).toBeTruthy()
    expect(screen.getByRole('region').getAttribute('data-state')).toBe('stable')
  })

  it.each([
    { slopePerDay: 0.2, days: 3, trending: true },
    { slopePerDay: 0.2, days: 14, trending: true },
    { slopePerDay: 0, days: 14, trending: false },
  ])('uses review wording and theme tokens in every state: %j', props => {
    const { container } = render(<DriftCard {...props} />)
    expect(container.textContent).not.toMatch(/diagnos/i)
    expect(container.firstElementChild?.classList.contains('card')).toBe(true)
    for (const element of container.querySelectorAll('[style]')) {
      expect(element.getAttribute('style')).not.toMatch(/#[\da-f]{3,8}\b|hsl\(/i)
    }
  })
})
