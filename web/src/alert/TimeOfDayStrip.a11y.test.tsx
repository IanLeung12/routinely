import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { TimeOfDayStrip } from './TimeOfDayStrip.tsx'

afterEach(cleanup)

describe('TimeOfDayStrip accessible names', () => {
  it('names each cell with its part of day and error count, including zero errors', () => {
    render(<TimeOfDayStrip buckets={[
      { bucket: 'morning', sessions: 2, errors: 0 },
      { bucket: 'afternoon', sessions: 2, errors: 1 },
      { bucket: 'evening', sessions: 2, errors: 3 },
    ]} />)

    for (const name of [
      'Morning: 0 errors, 2 sessions',
      'Afternoon: 1 error, 2 sessions',
      'Evening: 3 errors, 2 sessions',
    ]) {
      expect(screen.getByRole('listitem', { name })).toBeTruthy()
    }
    expect(screen.getAllByRole('listitem')).toHaveLength(3)
  })

  it('names zero-count cells when their buckets are omitted', () => {
    render(<TimeOfDayStrip buckets={[{ bucket: 'evening', sessions: 1, errors: 3 }]} />)

    expect(screen.getByRole('listitem', { name: 'Morning: 0 errors, 0 sessions' })).toBeTruthy()
    expect(screen.getByRole('listitem', { name: 'Afternoon: 0 errors, 0 sessions' })).toBeTruthy()
    expect(screen.getByRole('listitem', { name: 'Evening: 3 errors, 1 session' })).toBeTruthy()
  })
})
