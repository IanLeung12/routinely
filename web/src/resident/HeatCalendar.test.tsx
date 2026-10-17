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
    expect(screen.getByLabelText('2026-01-04: no session').style.backgroundColor).toBe('rgb(189, 189, 189)')
    expect(screen.getByLabelText('2026-01-05: score 0')).toBeTruthy()
  })

  it('orders dates and positions Monday first across week boundaries', () => {
    render(<HeatCalendar days={[
      { date: '2026-01-05', score: 1 },
      { date: '2026-01-04', score: 1 },
    ]} />)

    const cells = screen.getAllByRole('gridcell')
    expect(cells[0].getAttribute('aria-label')).toBe('2026-01-04: score 1')
    expect(cells[0].style.gridColumn).toBe('7')
    expect(cells[0].style.gridRow).toBe('1')
    expect(cells[1].style.gridColumn).toBe('1')
    expect(cells[1].style.gridRow).toBe('2')
  })

  it('uses a darker red for higher scores', () => {
    render(<HeatCalendar days={[
      { date: '2026-01-05', score: 0 },
      { date: '2026-01-06', score: 2 },
      { date: '2026-01-07', score: 10 },
    ]} />)

    const cells = screen.getAllByRole('gridcell')
    const red = cells.map(cell => Number(cell.style.backgroundColor.match(/\d+/)?.[0]))
    expect(red[0]).toBeGreaterThan(red[1])
    expect(red[1]).toBeGreaterThan(red[2])
  })

  it('renders nothing for an empty list', () => {
    const { container } = render(<HeatCalendar days={[]} />)
    expect(container.innerHTML).toBe('')
  })
})
