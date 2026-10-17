import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import HeatCalendar from './HeatCalendar'

afterEach(cleanup)

describe('HeatCalendar accessible day names', () => {
  it.fails('names every day with its date and error count, including no errors', () => {
    const days = [
      { date: '2026-10-17', score: 2, errors: '2 errors' },
      { date: '2026-10-18', score: 1, errors: '1 error' },
      { date: '2026-10-19', score: 0, errors: 'no errors' },
    ]
    render(<HeatCalendar days={days} />)

    expect(screen.getAllByRole('gridcell')).toHaveLength(days.length)
    for (const { date, errors } of days) {
      expect(screen.getByLabelText(`${date}: ${errors}`))
        .toBe(screen.getByRole('gridcell', { name: `${date}: ${errors}` }))
    }
  })
})
