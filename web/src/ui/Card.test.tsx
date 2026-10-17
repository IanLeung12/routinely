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
    expect(card.className).not.toContain('card--flush')
  })

  it('adds the wide modifier when asked', () => {
    render(<Card wide>hello</Card>)
    expect(screen.getByText('hello').className).toContain('card--wide')
  })

  it('drops its padding when the content draws its own edges', () => {
    render(<Card flush>hello</Card>)
    expect(screen.getByText('hello').className).toContain('card--flush')
  })
})
