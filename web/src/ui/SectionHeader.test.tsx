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
})
