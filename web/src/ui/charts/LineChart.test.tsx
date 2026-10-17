import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it } from 'vitest'
import { LineChart } from './LineChart'

afterEach(cleanup)
const data = [
  { time: Date.UTC(2026, 9, 1), value: 5 },
  { time: Date.UTC(2026, 9, 2), value: 9 },
  { time: Date.UTC(2026, 9, 3), value: 3 },
]
const props = { label: 'Daily score', summary: 'Scores are within their usual range.', data }

it('names the chart, displays its summary and tags the chronologically latest value', () => {
  const { container } = render(<LineChart {...props} data={[data[2], data[0], data[1]]} formatValue={(value) => `${value} pts`} />)
  expect(screen.getByRole('figure', { name: 'Daily score' }).getAttribute('aria-describedby')).toBe(screen.getByText(props.summary).id)
  expect(container.querySelector('foreignObject .pill')?.textContent).toBe('3 pts')
  expect(screen.getByText('Latest: 2026-10-03: 3 pts')).toBeTruthy()
  expect(data[0].value).toBe(5)
})

it('draws the band and dotted comparison only when supplied', () => {
  const { container, rerender } = render(<LineChart {...props} />)
  expect(container.querySelector('.line-chart__band')).toBeNull()
  expect(container.querySelector('.line-chart__comparison')).toBeNull()
  rerender(<LineChart {...props} baseline={{ mean: 5, threshold: 2 }} comparison={data} />)
  expect(Number(container.querySelector('.line-chart__band')?.getAttribute('height'))).toBeGreaterThan(0)
  expect(container.querySelector('.line-chart__mean')).toBeTruthy()
  expect(container.querySelector('.line-chart__comparison')?.getAttribute('d')).toContain('L')
  expect(screen.getByText('Usual range: 3–7 (mean 5).')).toBeTruthy()
})

it('moves keyboard focus across points and shows the same tooltip and crosshair as hover', async () => {
  const user = userEvent.setup()
  const { container } = render(<LineChart {...props} />)
  const points = screen.getAllByRole('button')
  await user.tab()
  expect(document.activeElement).toBe(points[0])
  expect(screen.getByRole('tooltip').textContent).toBe('2026-10-01: 5')
  await user.keyboard('{ArrowRight}')
  expect(document.activeElement).toBe(points[1])
  expect(screen.getByRole('tooltip').textContent).toBe('2026-10-02: 9')
  expect(container.querySelector('.line-chart__crosshair')?.getAttribute('x1')).toBe(points[1].getAttribute('cx'))
  await user.keyboard('{End}{ArrowRight}')
  expect(document.activeElement).toBe(points[2])
  await user.keyboard('{ArrowLeft}{Home}{ArrowLeft}')
  expect(document.activeElement).toBe(points[0])
  await user.tab()
  expect(screen.queryByRole('tooltip')).toBeNull()
  fireEvent.mouseEnter(points[2])
  expect(screen.getByRole('tooltip').textContent).toBe('2026-10-03: 3')
  fireEvent.mouseLeave(points[2])
  expect(screen.queryByRole('tooltip')).toBeNull()
})

it('reports flagged readings in text as well as coloured marks', () => {
  const { container } = render(<LineChart {...props} flagThreshold={7} />)
  expect(screen.getByRole('button', { name: /2026-10-02: 9, change flagged for review/ })).toBeTruthy()
  expect(screen.getByText('1 reading above the flag threshold: change flagged for review.')).toBeTruthy()
  expect(container.querySelectorAll('.line-chart__marker--flagged')).toHaveLength(1)
})

it('handles empty, invalid, single and constant readings without invalid SVG coordinates', () => {
  const { container, rerender } = render(<LineChart {...props} data={[]} />)
  expect(screen.getByText('No readings available.')).toBeTruthy()
  expect(container.querySelector('svg')).toBeNull()
  rerender(<LineChart {...props} data={[data[0], { time: NaN, value: 0 }, { time: 0, value: Infinity }]} />)
  expect(screen.getAllByRole('button')).toHaveLength(1)
  expect(container.querySelector('.line-chart__line')?.getAttribute('d')).not.toMatch(/NaN|Infinity/)
  rerender(<LineChart {...props} data={data.map((point) => ({ ...point, value: 0 }))} />)
  expect(container.querySelector('.line-chart__line')?.getAttribute('d')).not.toMatch(/NaN|Infinity/)
})
