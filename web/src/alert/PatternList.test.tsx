import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import type { PatternMatch } from '../contracts.ts'
import patternListCss from './PatternList.css?raw'
import { PatternList } from './PatternList.tsx'

afterEach(cleanup)

function pattern(overrides: Partial<PatternMatch> = {}): PatternMatch {
  return {
    pattern_id: 'delirium',
    name: 'Sudden change (delirium)',
    confidence: 0.82,
    urgency: 'same_shift',
    evidence: ['3 omissions in the last session', 'new antibiotic 2 days ago'],
    checks: ['Check for infection / UTI', 'Check hydration'],
    ...overrides,
  }
}

/** The confidence line of the nth pattern card: a big number plus the word, so the
 * number is its own element and `getByText` can't read the pair as one node. */
function confidence(index: number): string {
  const card = screen.getByRole('list', { name: 'Possible patterns' }).children[index]
  return card.querySelector('.pattern__confidence')?.textContent ?? ''
}

describe('PatternList', () => {
  it('renders patterns in order with name, confidence, evidence and checks', () => {
    const patterns = [
      pattern({ pattern_id: 'delirium', name: 'Sudden change (delirium)', confidence: 0.82 }),
      pattern({ pattern_id: 'drift', name: 'Slow cognitive drift', confidence: 0.4, evidence: ['slower over 3 weeks'], checks: ['Review recent medication changes'] }),
    ]
    render(<PatternList patterns={patterns} />)

    const headings = screen.getAllByRole('heading', { level: 3 }).map((h) => h.textContent)
    expect(headings).toEqual([
      'Consistent with: Sudden change (delirium)',
      'Consistent with: Slow cognitive drift',
    ])

    expect(screen.getByText('Consistent with: Sudden change (delirium)')).toBeTruthy()
    expect(confidence(0)).toBe('82% confidence')
    expect(screen.getByText('3 omissions in the last session')).toBeTruthy()
    expect(screen.getByText('new antibiotic 2 days ago')).toBeTruthy()
    expect(screen.getAllByText('Consider ruling out:').length).toBe(2)
    expect(screen.getByText('Check for infection / UTI')).toBeTruthy()

    expect(screen.getByText('Consistent with: Slow cognitive drift')).toBeTruthy()
    expect(confidence(1)).toBe('40% confidence')
    expect(screen.getByText('slower over 3 weeks')).toBeTruthy()
    expect(screen.getByText('Review recent medication changes')).toBeTruthy()
  })

  it('marks only the urgent pattern with the urgent class, and labels it in words', () => {
    render(
      <PatternList
        patterns={[
          pattern({ pattern_id: 'delirium', urgency: 'urgent' }),
          pattern({ pattern_id: 'drift', urgency: 'routine' }),
        ]}
      />,
    )

    const [urgentItem, routineItem] = Array.from(
      screen.getByRole('list', { name: 'Possible patterns' }).children,
    )
    expect(urgentItem.className).toContain('pattern--urgent')
    expect(routineItem.className).not.toContain('pattern--urgent')

    // Never colour alone: the urgency is also spelled out (web guide, a11y).
    expect(screen.getByText('Urgent').className).toContain('pattern__urgency--urgent')
    expect(screen.getByText('Routine').className).toContain('pattern__urgency--routine')
  })

  it('draws a confidence bar as wide as the confidence, and hides it from screen readers', () => {
    render(
      <PatternList
        patterns={[pattern({ pattern_id: 'delirium', confidence: 0.82 }), pattern({ pattern_id: 'drift', confidence: 0.4 })]}
      />,
    )

    const [first, second] = Array.from(screen.getByRole('list', { name: 'Possible patterns' }).children)
    expect(first.querySelector('.pattern__meter-fill')?.getAttribute('style')).toContain('--confidence: 0.82')
    expect(second.querySelector('.pattern__meter-fill')?.getAttribute('style')).toContain('--confidence: 0.4')
    // The percentage is the signal; the bar only makes the two comparable at a glance.
    expect(first.querySelector('.pattern__meter')?.getAttribute('aria-hidden')).toBe('true')
    expect(confidence(0)).toBe('82% confidence')
  })

  it('gives the list an accessible name', () => {
    render(<PatternList patterns={[pattern()]} />)
    expect(screen.getByRole('list', { name: 'Possible patterns' })).toBeTruthy()
  })

  it.each([
    ['routine', 'Routine'],
    ['next_round', 'Check next round'],
    ['same_shift', 'Check this shift'],
    ['urgent', 'Urgent'],
  ] as const)('shows a readable label for %s urgency', (urgency, label) => {
    render(<PatternList patterns={[pattern({ urgency })]} />)
    expect(screen.getByText(label)).toBeTruthy()
  })

  it('shows no clear pattern for an empty list', () => {
    render(<PatternList patterns={[]} />)
    expect(screen.getByText('Change detected, no clear pattern.')).toBeTruthy()
    expect(screen.queryByRole('list')).toBeNull()
  })

  it('never uses diagnostic wording', () => {
    const { container } = render(
      <PatternList patterns={[pattern(), pattern({ pattern_id: 'infection', urgency: 'urgent' })]} />,
    )
    expect(container.textContent?.toLowerCase()).not.toContain('diagnos')
  })
})

/** jsdom doesn't evaluate @media conditions for getComputedStyle, so this checks the
 * stylesheet text directly (T238, same approach as T234's overview.css test). */
describe('PatternList.css phone layout', () => {
  it('stacks the pattern name and confidence chip below 480px', () => {
    const mobileBlock = patternListCss.match(/@media \(max-width: 480px\) \{([\s\S]*)\}\s*$/)?.[1]
    expect(mobileBlock).toBeTruthy()

    expect(mobileBlock).toMatch(/\.pattern__header\s*\{[^}]*flex-direction:\s*column/)
  })
})
