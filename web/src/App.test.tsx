import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
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

  it('opens the mock alert evidence and returns to the overview', async () => {
    await act(async () => { render(<App />) })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'mrs-k: Change flagged for review' }))
    })
    expect(await screen.findByText(/^Flagged for review:/)).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Suggested checks' })).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Unit overview' })).toBeNull()

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Back/ }))
    })
    expect(screen.getByRole('heading', { name: 'Unit overview' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'mrs-k: Change flagged for review' })).toBeTruthy()
  })

  it('opens the shift handoff from the header and returns to the overview', async () => {
    await act(async () => { render(<App />) })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Shift handoff' }))
    })

    expect(await screen.findByRole('heading', { name: 'Shift handoff' })).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Unit overview' })).toBeNull()

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Back/ }))
    })
    expect(screen.getByRole('heading', { name: 'Unit overview' })).toBeTruthy()
  })
})
