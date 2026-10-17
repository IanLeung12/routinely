import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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
  it('renders scored sessions against their baseline on the shared LineChart', () => {
    const scores: ScorePoint[] = [
      { ts: '2026-10-15T08:00:00Z', score: 1 },
      { ts: '2026-10-16T08:00:00Z', score: 2.5 },
      { ts: '2026-10-17T08:00:00Z', score: 3 },
    ]
    const { container } = render(<BaselineChart scores={scores} baseline={baseline} />)

    expect(screen.getByRole('figure', { name: 'Baseline' })).toBeTruthy()
    expect(screen.getByText(/3 sessions against their baseline\. Latest score 3\.0, flag threshold 2\.0\. 2 sessions above it/)).toBeTruthy()
    expect(container.querySelector('foreignObject .pill')?.textContent).toBe('3.0')
    expect(screen.getByText('Usual range: -1.0–3.0 (mean 1.0).')).toBeTruthy()
    expect(container.querySelectorAll('.line-chart__marker--flagged')).toHaveLength(2)
    expectNoNaNAttributes(container)
  })

  it('renders an empty state without invalid attributes for an empty series', () => {
    const { container } = render(<BaselineChart scores={[]} baseline={baseline} />)

    expect(screen.getByText('No scored sessions yet.')).toBeTruthy()
    expect(screen.queryByRole('figure')).toBeNull()
    expectNoNaNAttributes(container)
  })

  it('offers 7D/14D/30D ranges and windows the chart from the newest session', async () => {
    const user = userEvent.setup()
    const scores: ScorePoint[] = [
      { ts: '2026-09-27T08:00:00Z', score: 1 },
      { ts: '2026-10-17T08:00:00Z', score: 3 },
    ]
    render(<BaselineChart scores={scores} baseline={baseline} />)

    expect(screen.getByRole('group', { name: 'Baseline chart time range' })).toBeTruthy()
    expect(screen.getByText(/^1 session against their baseline/)).toBeTruthy()

    await user.click(screen.getByRole('button', { name: '30D' }))
    expect(screen.getByText(/^2 sessions against their baseline/)).toBeTruthy()
  })
})
