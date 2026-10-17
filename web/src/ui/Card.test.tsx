import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { Card } from './Card.tsx'

afterEach(() => {
  cleanup()
})

describe('Card', () => {
  it('renders its children inside a card surface', () => {
    render(<Card>hello</Card>)
    const card = screen.getByText('hello')
    expect(card.className).toContain('card')
    expect(card.className).not.toContain('card--wide')
  })

  it('adds the wide modifier when asked', () => {
    render(<Card wide>hello</Card>)
    expect(screen.getByText('hello').className).toContain('card--wide')
  })
})
