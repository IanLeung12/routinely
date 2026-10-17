import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { BaselineChart } from './BaselineChart.tsx'
import type { Baseline, ScorePoint } from './types.ts'

afterEach(cleanup)

const baseline: Baseline = { mean: 1, std: 0.5, threshold: 2 }

function expectNoNaNAttributes(container: HTMLElement) {
  for (const element of container.querySelectorAll('*')) {
    for (const attribute of element.attributes) {
      expect(attribute.value).not.toContain('NaN')
    }
  }
}

describe('BaselineChart', () => {
  it('renders scored sessions against their baseline', () => {
    const scores: ScorePoint[] = [
      { ts: '2026-10-15T08:00:00Z', score: 1 },
      { ts: '2026-10-16T08:00:00Z', score: 2.5 },
      { ts: '2026-10-17T08:00:00Z', score: 3 },
    ]
    const { container } = render(<BaselineChart scores={scores} baseline={baseline} />)

    expect(screen.getByRole('img', {
      name: 'Baseline chart: 3 sessions, latest score 3.0, flag threshold 2.0, 2 sessions above it',
    })).toBeTruthy()
    expect(screen.getByText('Latest session 3.0')).toBeTruthy()
    expect(screen.getByText('threshold 2.0')).toBeTruthy()
    expectNoNaNAttributes(container)
  })

  it('renders an empty state without invalid attributes for an empty series', () => {
    const { container } = render(<BaselineChart scores={[]} baseline={baseline} />)

    expect(screen.getByText('No scored sessions yet.')).toBeTruthy()
    expect(screen.queryByRole('img')).toBeNull()
    expectNoNaNAttributes(container)
  })
})
