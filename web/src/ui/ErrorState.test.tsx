import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { ErrorState } from './ErrorState.tsx'

afterEach(() => {
  cleanup()
})

describe('ErrorState', () => {
  it('announces the message as an alert', () => {
    render(<ErrorState message="Couldn't reach the server." />)
    expect(screen.getByRole('alert').textContent).toBe("Couldn't reach the server.")
  })
})
