import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { ConfidenceBadge } from './ConfidenceBadge.tsx'

afterEach(cleanup)

describe('ConfidenceBadge', () => {
  it.each([
    [0.87, 'High confidence', '87%', 'high'],
    [0.8, 'High confidence', '80%', 'high'],
    [0.6, 'Medium confidence', '60%', 'medium'],
    [0.5, 'Medium confidence', '50%', 'medium'],
    [0.2, 'Low confidence', '20%', 'low'],
    [1.4, 'High confidence', '100%', 'high'],
    [-0.2, 'Low confidence', '0%', 'low'],
  ] as const)('renders confidence %s', (confidence, label, percentage, level) => {
    render(<ConfidenceBadge confidence={confidence} />)

    const badge = screen.getByText(label).parentElement
    expect(screen.getByText(percentage)).toBeTruthy()
    expect(badge?.getAttribute('data-level')).toBe(level)
  })

  it.each([0.2, 0.6, 0.87, 1.4])('unclear overrides confidence %s', (confidence) => {
    render(<ConfidenceBadge confidence={confidence} unclear />)

    const badge = screen.getByTitle('Low confidence; not counted as an error')
    expect(screen.getByText('Unclear')).toBeTruthy()
    expect(badge.getAttribute('data-level')).toBe('unclear')
    expect(screen.queryByText(/^(High|Medium|Low) confidence$/)).toBeNull()
  })
})
