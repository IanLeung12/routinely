import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { Loading } from './Loading.tsx'

afterEach(() => {
  cleanup()
})

describe('Loading', () => {
  it('defaults to a generic loading message', () => {
    render(<Loading />)
    expect(screen.getByRole('status').textContent).toBe('Loading…')
  })

  it('accepts a custom label', () => {
    render(<Loading label="Loading residents…" />)
    expect(screen.getByRole('status').textContent).toBe('Loading residents…')
  })
})
