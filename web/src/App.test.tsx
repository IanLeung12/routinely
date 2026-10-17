import { act, cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App.tsx'

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('API unavailable in tests')))
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('App', () => {
  it('renders the dashboard shell', async () => {
    // Flush the rejected request and fallback state update before jsdom teardown.
    await act(async () => {
      render(<App />)
    })

    expect(screen.getByRole('heading', { level: 1, name: 'Routine Watch' })).toBeTruthy()
    expect(screen.getByRole('heading', { level: 2, name: 'Unit overview' })).toBeTruthy()
  })
})
