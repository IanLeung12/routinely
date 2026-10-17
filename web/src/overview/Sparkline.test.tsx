import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { Sparkline } from './Sparkline.tsx'

afterEach(cleanup)

describe('Sparkline', () => {
  it('draws an SVG trend with a point for each score', () => {
    render(<Sparkline scores={[
      { ts: '2026-01-01', score: 1 },
      { ts: '2026-01-02', score: 3 },
      { ts: '2026-01-03', score: 2 },
    ]} />)

    const svg = screen.getByRole('img', { name: 'Error score over the last 3 sessions, latest 2.0' })
    const points = svg.querySelector('polyline')?.getAttribute('points')?.split(' ')
    expect(points).toHaveLength(3)
    expect(points?.map((point) => Number(point.split(',')[0]))).toEqual([2, 60, 118])
    expect(points?.map((point) => Number(point.split(',')[1]))).toEqual([30, 2, 16])
  })

  it('labels the session count and formats the latest score for screen readers', () => {
    render(<Sparkline scores={[
      { ts: '2026-01-01', score: 1 },
      { ts: '2026-01-02', score: 3 },
      { ts: '2026-01-03', score: 2.4000001 },
    ]} />)

    expect(screen.getByRole('img', {
      name: 'Error score over the last 3 sessions, latest 2.4',
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
      expect(container.querySelector('polyline')).toBeNull()
      expect(container.querySelector('svg')?.getAttribute('aria-hidden')).toBe('true')
    } else {
      expect(container.querySelector('polyline')?.getAttribute('points')?.split(' ')).toHaveLength(values.length)
    }
  })
})
