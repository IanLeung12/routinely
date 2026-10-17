import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import Landing from './Landing.tsx'
import { HERO_BASELINE, HERO_FLAG_THRESHOLD, HERO_READINGS } from './heroChart.ts'

afterEach(() => {
  cleanup()
})

/** In the order the page lays them out (T378). */
const SECTION_HEADINGS = [
  'Why it matters',
  'How it works',
  'Consistent with, never a conclusion',
  'Privacy by design',
  'Built with',
]

const DAY_MS = 24 * 60 * 60 * 1000

describe('landing page', () => {
  it('leads with what Routine Watch is', () => {
    render(<Landing />)

    expect(screen.getByRole('heading', { level: 1, name: 'Routine Watch' })).toBeTruthy()
    expect(screen.getByText(/flags a change for review/)).toBeTruthy()
  })

  it('shows every section, in order', () => {
    render(<Landing />)

    const sections = screen
      .getAllByRole('heading', { level: 2 })
      .map((heading) => heading.textContent)
    expect(sections).toEqual(SECTION_HEADINGS)
  })

  it('sends a judge into the dashboard', () => {
    render(<Landing />)

    expect(screen.getByRole('link', { name: 'Open the dashboard' }).getAttribute('href')).toBe('/')
    expect(screen.getByRole('link', { name: 'Take the guided tour.' }).getAttribute('href')).toBe(
      '/?tour=1',
    )
  })

  it('points "Watch the demo" at a section that exists', () => {
    render(<Landing />)

    const href = screen.getByRole('link', { name: 'Watch the demo' }).getAttribute('href') ?? ''
    expect(href.startsWith('#')).toBe(true)
    expect(screen.getByRole('heading', { level: 2, name: 'How it works' }).id).toBe(href.slice(1))
  })

  it('walks through the pipeline, camera to nurse', () => {
    render(<Landing />)

    const stages = screen.getAllByRole('listitem').map((item) => item.textContent ?? '')
    const labels = ['Camera', 'Skeleton only', 'Task graph', 'Personal baseline', 'Patterns', 'Nurse']
    for (const label of labels) {
      expect(stages.some((stage) => stage.includes(label))).toBe(true)
    }
  })

  it('gives each pattern example as something a change is consistent with', () => {
    render(<Landing />)

    for (const name of ['Sudden change', 'Slow drift', 'Evening worsening']) {
      const example = screen.getByRole('heading', { level: 3, name }).closest('li')
      expect(example?.textContent).toContain('Consistent with')
    }
  })

  it('names the privacy promises and the stack', () => {
    render(<Landing />)

    expect(screen.getByText(/No video is stored/)).toBeTruthy()
    expect(screen.getByText(/No face recognition/)).toBeTruthy()
    expect(screen.getByText(/switches off per room/)).toBeTruthy()
    for (const tool of ['Gemini', 'Tiger Data', 'Vultr', 'Claude', 'Roboflow']) {
      expect(screen.getByText(tool)).toBeTruthy()
    }
  })

  it('has a main landmark, a footer and headings in order', () => {
    render(<Landing />)

    expect(screen.getByRole('main')).toBeTruthy()
    const footer = screen.getByRole('contentinfo')
    expect(footer.textContent).toContain('Hack the Valley 11')
    expect(screen.getByRole('link', { name: /GitHub/ }).getAttribute('href')).toMatch(/^https:/)

    const levels = screen
      .getAllByRole('heading')
      .map((heading) => Number(heading.tagName.slice(1)))
    expect(levels[0]).toBe(1)
    levels.forEach((level, index) => {
      if (index > 0) expect(level).toBeLessThanOrEqual(levels[index - 1] + 1)
    })
  })

  it('never reaches for banned wording (SPEC section 7.5)', () => {
    const { container } = render(<Landing />)
    const copy = container.textContent ?? ''

    for (const banned of [/diagnos/i, /suffers from/i, /has delirium/i, /has dementia/i]) {
      expect(copy).not.toMatch(banned)
    }
  })

  it('stays short enough to read in one pass', () => {
    const { container } = render(<Landing />)

    /* The hero chart's own text - axis labels, the value of every reading, the keyboard
       instructions - is the accessible equivalent of the picture, not copy anyone reads
       top to bottom, so the prose budget is measured without it (T407). */
    const prose = container.cloneNode(true) as HTMLElement
    prose.querySelectorAll('figure').forEach((figure) => figure.remove())
    const words = (prose.textContent ?? '').split(/\s+/).filter((word) => /[a-z]/i.test(word))
    expect(words.length).toBeLessThanOrEqual(350)
  })
})

describe('the hero chart', () => {
  it('draws one resident against her own usual range, latest reading tagged', () => {
    const { container } = render(<Landing />)

    const chart = screen.getByRole('figure', { name: /Mrs\. K/ })
    expect(chart.textContent).toContain('Usual range: 0.07–0.17 (mean 0.12).')
    expect(container.querySelector('.line-chart__band')).toBeTruthy()
    /* The end-of-line tag: the latest score, next to the point, without hovering. */
    expect(container.querySelector('foreignObject .pill')?.textContent).toBe('0.78')
    expect(screen.getByText('Latest: 1 Jan: 0.78, change flagged for review')).toBeTruthy()
  })

  it('says in words, not only in colour, that two readings are above her threshold', () => {
    const { container } = render(<Landing />)

    expect(
      screen.getByText('2 readings above the flag threshold: change flagged for review.'),
    ).toBeTruthy()
    expect(container.querySelectorAll('.line-chart__marker--flagged')).toHaveLength(2)
    expect(screen.getByText('Flagged').getAttribute('aria-label')).toBe('Change flagged for review')
  })

  it('puts the numbers behind the chart beside it', () => {
    render(<Landing />)

    const stat = (label: string) => screen.getByText(label).closest('.landing-stat')?.textContent
    expect(stat('Her own baseline')).toContain('14')
    expect(stat('Above her usual range')).toContain('2')
    expect(stat('Video kept')).toContain('0')
  })

  it('keeps her quiet fortnight inside the band and the flagged day outside it', () => {
    const flagged = HERO_READINGS.filter((reading) => reading.value > HERO_FLAG_THRESHOLD)
    const quiet = HERO_READINGS.filter((reading) => reading.value <= HERO_FLAG_THRESHOLD)

    expect(quiet).toHaveLength(HERO_READINGS.length - 2)
    for (const reading of quiet) {
      expect(reading.value).toBeGreaterThanOrEqual(HERO_BASELINE.mean - HERO_BASELINE.threshold)
      expect(reading.value).toBeLessThanOrEqual(HERO_BASELINE.mean + HERO_BASELINE.threshold)
    }
    /* Two sessions over her own threshold within 24 h is what a flag takes (SPEC §7). */
    expect(flagged).toHaveLength(2)
    expect(flagged[1].time - flagged[0].time).toBeLessThan(DAY_MS)
  })
})
