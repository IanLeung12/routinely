import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { TimeOfDayStrip } from './TimeOfDayStrip.tsx'

const originalWidth = window.innerWidth

afterEach(() => {
  cleanup()
  window.innerWidth = originalWidth
})

describe('TimeOfDayStrip at phone width', () => {
  it('keeps all three bucket labels and their counts available at 375px', () => {
    window.innerWidth = 375
    render(<TimeOfDayStrip buckets={[
      { bucket: 'morning', sessions: 2, errors: 1 },
      { bucket: 'afternoon', sessions: 3, errors: 2 },
      { bucket: 'evening', sessions: 4, errors: 6 },
    ]} />)

    const list = within(screen.getByRole('list', { name: 'Errors by time of day' }))
    for (const [label, errors] of [['Morning', 1], ['Afternoon', 2], ['Evening', 6]] as const) {
      const bucket = within(list.getByRole('listitem', {
        name: `${label}: ${errors} ${errors === 1 ? 'error' : 'errors'}`,
      }))
      expect(bucket.getByText(label)).toBeTruthy()
      expect(bucket.getByText(/per session/)).toBeTruthy()
    }
  })
})
