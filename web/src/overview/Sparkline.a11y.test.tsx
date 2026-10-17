import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { Sparkline } from './Sparkline.tsx'

afterEach(cleanup)

describe('Sparkline text alternatives', () => {
  it.each([
    { values: [1, 2, 3], trend: 'rising' },
    { values: [3, 2, 1], trend: 'falling' },
    { values: [2, 2, 2], trend: 'flat' },
    { values: [1, 3, 1], trend: 'varying' },
    { values: [2], trend: 'flat' },
  ])('describes a $trend trend for $values', ({ values, trend }) => {
    render(<Sparkline scores={values.map((score, index) => ({ ts: String(index), score }))} />)

    expect(screen.getByRole('img', {
      name: new RegExp(`Error score over the last ${values.length} sessions, latest .*, ${trend}$`),
    })).toBeTruthy()
  })

  it('describes the absence of history for empty data', () => {
    render(<Sparkline scores={[]} />)

    expect(screen.getByRole('img', { name: 'No error score history yet' })).toBeTruthy()
  })
})
