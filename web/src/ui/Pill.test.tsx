import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { Pill } from './Pill.tsx'

afterEach(() => {
  cleanup()
})

describe('Pill', () => {
  it('shows its value and defaults to the neutral tone', () => {
    render(<Pill>3 errors</Pill>)
    const pill = screen.getByText('3 errors')
    expect(pill.className).toContain('pill')
    expect(pill.className).toContain('pill--neutral')
  })

  it('tints itself for each tone', () => {
    const tones = ['neutral', 'positive', 'watch', 'negative'] as const
    for (const tone of tones) {
      render(<Pill tone={tone}>+2</Pill>)
      expect(screen.getByText('+2').className).toContain(`pill--${tone}`)
      cleanup()
    }
  })

  it('reads the same with no colour: the value is always in the text', () => {
    render(
      <Pill tone="negative" direction="up">
        +3 vs usual
      </Pill>,
    )
    expect(screen.getByText(/\+3 vs usual/)).toBeTruthy()
  })

  it('adds a direction arrow that screen readers skip, since the sign is in the text', () => {
    const { container } = render(
      <Pill tone="positive" direction="down">
        −1
      </Pill>,
    )
    const arrow = container.querySelector('.pill__arrow')
    expect(arrow?.textContent).toBe('↓')
    expect(arrow?.getAttribute('aria-hidden')).toBe('true')
  })

  it('leaves the arrow out when no direction is given', () => {
    const { container } = render(<Pill>12</Pill>)
    expect(container.querySelector('.pill__arrow')).toBeNull()
  })
})
