import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { SectionHeader } from './SectionHeader.tsx'

afterEach(() => {
  cleanup()
})

describe('SectionHeader', () => {
  it('renders the title as a heading', () => {
    render(<SectionHeader title="Baseline" />)
    expect(screen.getByRole('heading', { name: 'Baseline' })).toBeTruthy()
  })

  it('renders an action alongside the title when given one', () => {
    render(<SectionHeader title="Sessions" action={<button type="button">Refresh</button>} />)
    expect(screen.getByRole('button', { name: 'Refresh' })).toBeTruthy()
  })

  it('names what the numbers are with a muted caption', () => {
    render(<SectionHeader title="Baseline" caption="last 14 days" />)
    const caption = screen.getByText('last 14 days')
    expect(caption.className).toContain('section-header__caption')
  })

  it('leaves the caption out when there is none', () => {
    const { container } = render(<SectionHeader title="Baseline" />)
    expect(container.querySelector('.section-header__caption')).toBeNull()
  })
})
