import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { RoutineChart } from './RoutineChart.tsx'
import type { PersonRoutine } from './types.ts'

afterEach(cleanup)

function routine(days: PersonRoutine['days']): PersonRoutine {
  return {
    person_id: 'sam',
    now: '2026-01-01T20:10:00+00:00',
    status: 'flagged',
    usual_minutes: 3,
    days,
    sessions: [],
    patterns: [],
  }
}

const WEEK = [
  { date: '2025-12-31', minutes: 3.8, usual_minutes: 3 },
  { date: '2026-01-01', minutes: 4.2, usual_minutes: 3 },
]

describe('RoutineChart', () => {
  it('draws this week against their usual, one bar a day', () => {
    render(<RoutineChart routine={routine(WEEK)} />)

    const chart = screen.getByRole('img', {
      name: 'Minutes your routine took each day this week, next to your usual',
    })
    expect(chart).toBeTruthy()
    expect(within(chart).getByText('Wed')).toBeTruthy()
    expect(within(chart).getByText('Thu')).toBeTruthy()
  })

  it('offers the same numbers as a table for a screen reader', () => {
    render(<RoutineChart routine={routine(WEEK)} />)

    const rows = within(screen.getByRole('table')).getAllByRole('row')
    // Header, then one row a day with the day's minutes and their usual beside it.
    expect(rows.length).toBe(WEEK.length + 1)
    expect(within(rows[2]).getByText('4.2 (Today)')).toBeTruthy()
    expect(within(rows[2]).getAllByText('3').length).toBe(1)
  })

  it('says which bar is which, so colour is never the only signal', () => {
    render(<RoutineChart routine={routine(WEEK)} />)

    expect(screen.getByText(/The filled bar is that day/)).toBeTruthy()
    expect(screen.getByText(/your usual, about 3 min/)).toBeTruthy()
  })

  it('has an empty state before there is a week to compare', () => {
    render(<RoutineChart routine={routine([])} />)

    expect(screen.getByText('No days to compare yet.')).toBeTruthy()
    expect(screen.queryByRole('img')).toBeNull()
  })
})
