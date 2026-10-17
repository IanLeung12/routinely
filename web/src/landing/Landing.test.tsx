import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import Landing from './Landing.tsx'

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

    const words = (container.textContent ?? '')
      .split(/\s+/)
      .filter((word) => /[a-z]/i.test(word))
    expect(words.length).toBeLessThanOrEqual(350)
  })
})
