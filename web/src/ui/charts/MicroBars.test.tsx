import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import indexCss from '../../index.css?raw'
import { MicroBars, type MicroBarDay, summariseDays } from './MicroBars.tsx'
import microBarsCss from './microBars.css?raw'

afterEach(cleanup)

/** Fourteen quiet days, oldest first, with `overrides` applied by index. */
function fortnight(overrides: Record<number, Partial<MicroBarDay>> = {}): MicroBarDay[] {
  return Array.from({ length: 14 }, (_, index) => ({
    date: `2026-01-${String(index + 1).padStart(2, '0')}`,
    score: 0.2,
    status: 'normal' as const,
    ...overrides[index],
  }))
}

const ticks = (container: HTMLElement) => [...container.querySelectorAll('rect')]
const attr = (tick: Element, name: string) => Number(tick.getAttribute(name))

describe('MicroBars', () => {
  it('draws one tick per day, sitting on the baseline of a row-sized strip', () => {
    const { container } = render(<MicroBars days={fortnight()} ariaLabel="Error score for Ada" />)

    const strip = screen.getByRole('img', { name: /14 days/ })
    expect(strip.getAttribute('width')).toBe('84')
    expect(strip.getAttribute('height')).toBe('20')

    const drawn = ticks(container)
    expect(drawn).toHaveLength(14)
    // Every tick grows up from the bottom edge, and stays inside the strip.
    for (const tick of drawn) {
      expect(attr(tick, 'y') + attr(tick, 'height')).toBe(20)
      expect(attr(tick, 'x')).toBeGreaterThanOrEqual(0)
      expect(attr(tick, 'x') + attr(tick, 'width')).toBeLessThanOrEqual(84)
    }
    // Thin, evenly spaced, oldest day on the left.
    expect(drawn.map((tick) => attr(tick, 'width'))).toEqual(Array(14).fill(4))
    expect(drawn.map((tick) => attr(tick, 'x'))).toEqual([1, 7, 13, 19, 25, 31, 37, 43, 49, 55, 61, 67, 73, 79])
  })

  it('makes each tick as tall as its score next to the busiest day', () => {
    const { container } = render(
      <MicroBars
        days={[
          { date: '2026-01-01', score: 5, status: 'flagged' },
          { date: '2026-01-02', score: 2.5, status: 'watch' },
          { date: '2026-01-03', score: 0, status: 'normal' },
        ]}
        ariaLabel="Error score for Ada"
      />,
    )

    // 5 fills the strip, 2.5 is half of it, and a scored 0 still shows a stub.
    expect(ticks(container).map((tick) => attr(tick, 'height'))).toEqual([20, 11.5, 3])
  })

  it('keeps a quiet fortnight quiet instead of stretching it to full height', () => {
    const { container } = render(<MicroBars days={fortnight()} ariaLabel="Error score for Ada" />)

    // Scores are weighted sums, so 0.2 of an error is a stub: heights are
    // relative to the busiest day but never to less than one error.
    for (const tick of ticks(container)) {
      expect(attr(tick, 'height')).toBeLessThan(10)
      expect(attr(tick, 'height')).toBeGreaterThan(1)
    }
  })

  it('holds a day with no reading open as a faint hairline', () => {
    const { container } = render(
      <MicroBars
        days={fortnight({ 3: { score: null }, 4: { score: 0 } })}
        ariaLabel="Error score for Ada"
      />,
    )

    expect(ticks(container)).toHaveLength(14)
    const missing = container.querySelector('[data-date="2026-01-04"]')
    expect(missing?.getAttribute('class')).toContain('micro-bars__tick--missing')
    expect(attr(missing as Element, 'height')).toBe(1)

    // A day that was scored 0 is taller than the hairline, so "no session" and
    // "a session with nothing wrong" never look the same.
    const scoredZero = container.querySelector('[data-date="2026-01-05"]') as Element
    expect(scoredZero.getAttribute('class')).toContain('micro-bars__tick--normal')
    expect(attr(scoredZero, 'height')).toBeGreaterThan(attr(missing as Element, 'height'))
  })

  it('colours a tick by its status, and only ever with a token', () => {
    const { container } = render(
      <MicroBars
        days={fortnight({ 11: { status: 'watch' }, 12: { status: 'flagged', score: 5 }, 13: { status: 'flagged', score: 4 } })}
        ariaLabel="Error score for Ada"
      />,
    )

    const classOf = (date: string) => container.querySelector(`[data-date="${date}"]`)?.getAttribute('class')
    expect(classOf('2026-01-01')).toContain('micro-bars__tick--normal')
    expect(classOf('2026-01-12')).toContain('micro-bars__tick--watch')
    expect(classOf('2026-01-13')).toContain('micro-bars__tick--flagged')

    expect(microBarsCss).toMatch(/\.micro-bars__tick--normal\s*\{\s*fill:\s*var\(--status-normal\)/)
    expect(microBarsCss).toMatch(/\.micro-bars__tick--watch\s*\{\s*fill:\s*var\(--status-watch\)/)
    expect(microBarsCss).toMatch(/\.micro-bars__tick--flagged\s*\{\s*fill:\s*var\(--status-flagged\)/)
    expect(microBarsCss).toMatch(/\.micro-bars__tick--missing\s*\{\s*fill:\s*var\(--hairline-strong\)/)

    // No hex in a component's stylesheet, and no token index.css doesn't define.
    expect(microBarsCss).not.toMatch(/#[0-9a-f]{3}/i)
    const tokens = [...microBarsCss.matchAll(/var\((--[a-z-]+)\)/g)].map((match) => match[1])
    expect(tokens.length).toBeGreaterThan(3)
    for (const token of tokens) {
      expect(indexCss).toContain(`${token}:`)
    }
  })

  it('gives a screen reader the caller’s label and a summary of the fortnight', () => {
    render(<MicroBars days={fortnight({ 12: { status: 'flagged' }, 13: { status: 'flagged' } })} ariaLabel="Error score for Ada" />)

    expect(screen.getByRole('img', { name: 'Error score for Ada: 14 days, 2 flagged' })).toBeTruthy()
  })

  it.each([
    { what: 'a flagged day, a watch day and a missing one', days: fortnight({ 11: { status: 'watch' }, 12: { score: null }, 13: { status: 'flagged' } }), summary: '14 days, 1 flagged, 1 to watch, 1 with no reading' },
    { what: 'nothing worth saying', days: fortnight(), summary: '14 days, all within their usual range' },
    { what: 'a single day', days: fortnight().slice(0, 1), summary: '1 day, all within their usual range' },
    { what: 'no days at all', days: [], summary: 'no days yet' },
  ])('summarises $what as "$summary"', ({ days, summary }) => {
    expect(summariseDays(days)).toBe(summary)

    render(<MicroBars days={days} ariaLabel="Error score for Ada" />)
    expect(screen.getByRole('img', { name: `Error score for Ada: ${summary}` })).toBeTruthy()
  })

  it('draws nothing but keeps its place when there are no days', () => {
    const { container } = render(<MicroBars days={[]} ariaLabel="Error score for Ada" />)

    expect(ticks(container)).toHaveLength(0)
    expect(container.querySelector('svg')?.getAttribute('class')).toBe('micro-bars')
  })

  it('takes an extra class so a row can place it', () => {
    const { container } = render(<MicroBars days={fortnight()} ariaLabel="Error score for Ada" className="overview-row__strip" />)

    expect(container.querySelector('svg')?.getAttribute('class')).toBe('micro-bars overview-row__strip')
  })

  it.each([
    { what: '30 days', days: Array.from({ length: 30 }, (_, index) => ({ date: `2026-01-${index}`, score: index / 3, status: 'normal' as const })) },
    { what: 'every day missing', days: fortnight({}).map((day) => ({ ...day, score: null })) },
    { what: 'a broken or negative score', days: fortnight({ 0: { score: Number.NaN }, 1: { score: Number.POSITIVE_INFINITY }, 2: { score: -3 } }) },
  ])('never writes an invalid attribute for $what', ({ days }) => {
    const { container } = render(<MicroBars days={days} ariaLabel="Error score for Ada" />)

    expect(ticks(container)).toHaveLength(days.length)
    for (const element of container.querySelectorAll('*')) {
      for (const attribute of element.attributes) {
        expect(attribute.value).not.toMatch(/NaN|Infinity/)
      }
      // No negative geometry either: a broken score must not flip a tick.
      for (const name of ['x', 'y', 'width', 'height', 'rx']) {
        const value = element.getAttribute(name)
        if (value !== null) {
          expect(Number(value)).toBeGreaterThanOrEqual(0)
        }
      }
    }
  })
})
