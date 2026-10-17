import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { EmptyState } from './EmptyState.tsx'

afterEach(() => {
  cleanup()
})

describe('EmptyState', () => {
  it('renders the given message', () => {
    render(<EmptyState message="No sessions recorded yet." />)
    expect(screen.getByText('No sessions recorded yet.')).toBeTruthy()
  })
})
