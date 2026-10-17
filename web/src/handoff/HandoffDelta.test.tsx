import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { HandoffDelta } from './HandoffDelta.tsx'

afterEach(cleanup)

/** The phrase without the arrow beside it: what a nurse actually reads. */
function phrase(): string | null {
  return document.querySelector('.handoff-delta__label')?.textContent ?? null
}

function tone(): string | undefined {
  return document.querySelector('.handoff-delta')?.className
}

describe('HandoffDelta', () => {
  it('says how many more sessions were flagged than last shift', () => {
    render(<HandoffDelta flags={2} previousFlags={0} />)

    expect(screen.getByText('2 more than last shift')).toBeTruthy()
    expect(tone()).toContain('pill--negative')
  })

  it('counts one more as one, not "1 more sessions"', () => {
    render(<HandoffDelta flags={3} previousFlags={2} />)

    expect(phrase()).toBe('1 more than last shift')
  })

  it('says how many fewer when the shift is better than the last one', () => {
    render(<HandoffDelta flags={1} previousFlags={4} />)

    expect(screen.getByText('3 fewer than last shift')).toBeTruthy()
    expect(tone()).toContain('pill--positive')
    expect(document.querySelector('.pill__arrow')?.textContent).toBe('\u2193')
  })

  it('says the same when the count has not moved', () => {
    render(<HandoffDelta flags={2} previousFlags={2} />)

    expect(screen.getByText('Same as last shift')).toBeTruthy()
    expect(tone()).toContain('pill--neutral')
    expect(document.querySelector('.pill__arrow')).toBeNull()
  })

  it('says nothing was flagged either shift rather than "same" over two zeros', () => {
    render(<HandoffDelta flags={0} previousFlags={0} />)

    expect(screen.getByText('Nothing flagged either shift')).toBeTruthy()
    expect(tone()).toContain('pill--neutral')
    expect(document.querySelector('.pill__arrow')).toBeNull()
  })

  it('reads a drop to zero as fewer, not as a quiet shift', () => {
    render(<HandoffDelta flags={0} previousFlags={2} />)

    expect(phrase()).toBe('2 fewer than last shift')
  })

  it('shows nothing when the payload sent no previous count', () => {
    // `previous_flags` is optional (T292, T311): an older or trimmed `/handoff` has
    // no comparison to make, which is not the same as "no change".
    const { container } = render(<HandoffDelta flags={2} />)

    expect(container.textContent).toBe('')
    expect(phrase()).toBeNull()
  })

  it('shows nothing when the previous count is null', () => {
    const { container } = render(<HandoffDelta flags={2} previousFlags={null} />)

    expect(container.textContent).toBe('')
  })

  it('never leans on colour or the arrow alone', () => {
    render(<HandoffDelta flags={4} previousFlags={1} />)

    // The direction is in the words; the arrow is decorative and hidden from
    // assistive tech, so nothing is lost without it (web guide, SPEC section 9).
    expect(phrase()).toBe('3 more than last shift')
    const glyph = document.querySelector('.pill__arrow')
    expect(glyph?.getAttribute('aria-hidden')).toBe('true')
    expect(glyph?.textContent).toBe('↑')
  })

  it('describes counts only, never a resident', () => {
    render(<HandoffDelta flags={5} previousFlags={0} />)

    const text = document.querySelector('.handoff-delta')?.textContent ?? ''
    expect(text.toLowerCase()).not.toMatch(/diagnos|worse|better|declin/)
  })
})
