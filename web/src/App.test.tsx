import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App.tsx'

describe('App', () => {
  it('renders the dashboard shell', () => {
    render(<App />)

    expect(screen.getByRole('heading', { level: 1, name: 'Routine Watch' })).toBeTruthy()
    expect(screen.getByRole('heading', { level: 2, name: 'Unit overview' })).toBeTruthy()
  })
})
