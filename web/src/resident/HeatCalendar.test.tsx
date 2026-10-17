import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import HeatCalendar from './HeatCalendar'

afterEach(cleanup)

describe('HeatCalendar', () => {
  it('renders accessible daily cells with score and no-session labels', () => {
    render(<HeatCalendar days={[
      { date: '2026-01-03', score: 4.5 },
      { date: '2026-01-04', score: null },
      { date: '2026-01-05', score: 0 },
    ]} />)

    expect(screen.getAllByRole('gridcell')).toHaveLength(3)
    expect(screen.getByLabelText('2026-01-03: score 4.5').title).toBe('2026-01-03: score 4.5')
    expect(screen.getByLabelText('2026-01-04: no session').style.backgroundColor).toBe('var(--error-grey-bg)')
    expect(screen.getByLabelText('2026-01-05: score 0')).toBeTruthy()
  })

  it('renders Monday-first weekday headers and the legend', () => {
    render(<HeatCalendar days={[{ date: '2026-01-03', score: 1 }]} />)

    const headers = screen.getAllByRole('columnheader')
    expect(headers.map(header => header.textContent)).toEqual(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])
    expect(screen.getByText('Darker = more errors that day. Grey = no session.')).toBeTruthy()
  })

  it('orders dates and positions Monday first across week boundaries', () => {
    render(<HeatCalendar days={[
      { date: '2026-01-05', score: 1 },
      { date: '2026-01-04', score: 1 },
    ]} />)

    const cells = screen.getAllByRole('gridcell')
    expect(cells[0].getAttribute('aria-label')).toBe('2026-01-04: score 1')
    expect(cells[0].style.gridColumn).toBe('7')
    expect(cells[0].style.gridRow).toBe('2')
    expect(cells[1].style.gridColumn).toBe('1')
    expect(cells[1].style.gridRow).toBe('3')
  })

  it('mixes more of the theme red into higher scores', () => {
    render(<HeatCalendar days={[
      { date: '2026-01-05', score: 0 },
      { date: '2026-01-06', score: 2 },
      { date: '2026-01-07', score: 10 },
    ]} />)

    const cells = screen.getAllByRole('gridcell')
    const red = cells.map(cell => Number(cell.style.backgroundColor.match(/(\d+)%/)?.[1]))
    expect(red[0]).toBeLessThan(red[1])
    expect(red[1]).toBeLessThan(red[2])
  })

  it('uses theme colours throughout and light text at the high-score boundary', () => {
    const { container } = render(<HeatCalendar days={[
      { date: '2026-01-05', score: null },
      { date: '2026-01-06', score: 0 },
      { date: '2026-01-07', score: 3.9 },
      { date: '2026-01-08', score: 4 },
      { date: '2026-01-09', score: 5 },
    ]} />)

    for (const element of container.querySelectorAll('[style]')) {
      expect(element.getAttribute('style')).not.toMatch(/#[\da-f]{3,8}\b|hsl\(/i)
    }
    expect(screen.getByLabelText('2026-01-08: score 4').style.color).toBe('var(--text)')
    expect(screen.getByLabelText('2026-01-09: score 5').style.color).toBe('var(--text)')
    expect(screen.getByLabelText('2026-01-07: score 3.9').style.color).toBe('var(--error-grey-text)')
    expect(screen.getByRole('grid').style.backgroundColor).toBe('')
  })

  it('shows the empty state for an empty list', () => {
    render(<HeatCalendar days={[]} />)
    expect(screen.getByText('No sessions yet, so nothing to show on the calendar.')).toBeTruthy()
  })
})
