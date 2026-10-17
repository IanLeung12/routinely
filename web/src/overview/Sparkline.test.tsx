import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { Sparkline } from './Sparkline.tsx'

afterEach(cleanup)

describe('Sparkline', () => {
  it('draws an SVG bar for each score', () => {
    render(<Sparkline scores={[
      { ts: '2026-01-01', score: 1 },
      { ts: '2026-01-02', score: 3 },
      { ts: '2026-01-03', score: 2 },
    ]} />)

    const chart = screen.getByRole('img', { name: 'Error score over the last 3 sessions, latest 2.0, rising' })
    const bars = [...chart.querySelectorAll('rect')]
    expect(bars).toHaveLength(3)
    expect(bars.map((bar) => bar.getAttribute('data-date'))).toEqual(['2026-01-01', '2026-01-02', '2026-01-03'])
    expect(bars.map((bar) => Number(bar.getAttribute('height')))).toEqual([8.67, 20, 14.33])
  })

  it('labels the session count and formats the latest score for screen readers', () => {
    render(<Sparkline scores={[
      { ts: '2026-01-01', score: 1 },
      { ts: '2026-01-02', score: 3 },
      { ts: '2026-01-03', score: 2.4000001 },
    ]} />)

    expect(screen.getByRole('img', {
      name: 'Error score over the last 3 sessions, latest 2.4, rising',
    })).toBeTruthy()
  })

  it.each([{ values: [] }, { values: [4] }, { values: [4, 4] }])('handles sparse or flat scores $values without invalid attributes', ({ values }) => {
    const { container } = render(<Sparkline scores={values.map((score, index) => ({ ts: `${index}`, score }))} />)

    expect(container.querySelector('svg')).toBeTruthy()
    for (const element of container.querySelectorAll('*')) {
      for (const attribute of element.attributes) {
        expect(attribute.value).not.toMatch(/NaN|Infinity/)
      }
    }
    if (values.length === 0) {
      expect(container.querySelector('rect')).toBeNull()
      expect(screen.getByRole('img', { name: 'No error score history yet' })).toBeTruthy()
    } else {
      expect(container.querySelectorAll('rect')).toHaveLength(values.length)
    }
  })
})
