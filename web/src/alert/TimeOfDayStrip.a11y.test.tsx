import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import type { TimeOfDayErrors } from '../contracts.ts'
import { TimeOfDayStrip } from './TimeOfDayStrip.tsx'

afterEach(cleanup)

const EVENING_ONLY: TimeOfDayErrors[] = [
  { bucket: 'morning', sessions: 14, errors: 1 },
  { bucket: 'afternoon', sessions: 0, errors: 0 },
  { bucket: 'evening', sessions: 14, errors: 15 },
]

describe('TimeOfDayStrip accessibility', () => {
  it('gives every cell an accessible name with its part of day and count, including zero-count cells', () => {
    render(<TimeOfDayStrip buckets={EVENING_ONLY} />)

    expect(screen.getByRole('listitem', { name: 'Morning: 1 error' })).toBeTruthy()
    expect(screen.getByRole('listitem', { name: 'Afternoon: no sessions' })).toBeTruthy()
    expect(screen.getByRole('listitem', { name: 'Evening: 15 errors' })).toBeTruthy()
  })
})
