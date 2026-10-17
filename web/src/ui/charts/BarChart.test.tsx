import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { BarChart } from './BarChart.tsx'

afterEach(cleanup)

describe('BarChart', () => {
  it('renders one primary bar per item and only supplied comparisons, including zero', () => {
    const { container } = render(<BarChart ariaLabel="Weekly counts" data={[{ label: 'Mon', value: 4 }, { label: 'Tue', value: 8, compare: 0 }]} />)
    expect(screen.getByRole('img', { name: 'Weekly counts' })).toBeTruthy()
    expect(container.querySelectorAll('.bar-chart__bar')).toHaveLength(2)
    expect(container.querySelectorAll('.bar-chart__compare')).toHaveLength(1)
    const table = screen.getByRole('table', { name: 'Weekly counts' })
    expect(within(table).getByRole('cell', { name: '0' })).toBeTruthy()
    expect(table.style.clipPath).toBe('inset(50%)')
  })

  it('omits the comparison series and column when absent', () => {
    const { container } = render(<BarChart ariaLabel="Counts" data={[{ label: 'Mon', value: 3 }]} />)
    expect(container.querySelector('.bar-chart__compare')).toBeNull()
    expect(screen.queryByRole('columnheader', { name: 'Usual' })).toBeNull()
  })

  it('shows a callout above its highlighted bar and includes it in the data table', () => {
    const { container } = render(<BarChart ariaLabel="Counts" data={[{ label: 'Mon', value: 24, compare: 10 }]} highlight={0} callout={{ index: 0, label: '2.4× usual' }} />)
    expect(screen.getByText('2.4× usual')).toBeTruthy()
    expect(container.querySelector('.bar-chart__bar')?.getAttribute('fill')).toBe('var(--chart-comparison)')
    expect(within(screen.getByRole('table')).getByRole('cell', { name: '24 (highlighted) (2.4× usual)' })).toBeTruthy()
  })

  it('keeps zero, negative and constant values within the plotting area', () => {
    for (const values of [[0, 0], [5, 5], [-5, 10]]) {
      const { container } = render(<BarChart ariaLabel="Counts" data={values.map(value => ({ label: String(value), value }))} />)
      for (const bar of container.querySelectorAll('.bar-chart__bar')) {
        const top = Number(bar.getAttribute('y'))
        const height = Number(bar.getAttribute('height'))
        expect(top).toBeGreaterThanOrEqual(60)
        expect(height).toBeGreaterThanOrEqual(0)
        expect(top + height).toBeLessThanOrEqual(200)
      }
      cleanup()
    }
  })

  it('renders an accessible empty chart', () => {
    render(<BarChart ariaLabel="Counts" data={[]} />)
    expect(screen.getByRole('img', { name: 'Counts' })).toBeTruthy()
    expect(screen.getByText('No data yet')).toBeTruthy()
  })
})
