import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { SessionSummary } from './SessionSummary.tsx'

afterEach(cleanup)

describe('SessionSummary accessibility', () => {
  it('names the summary heading and labels duration and errors in text', () => {
    render(<SessionSummary durationS={220} errorCount={2} />)

    expect(screen.getByRole('heading', { name: 'Session summary' })).toBeTruthy()
    expect(screen.getByText(/Finished in 3m 40s/)).toBeTruthy()
    expect(screen.getByText(/2 errors/)).toBeTruthy()
  })

  it('keeps labels readable with baseline comparisons and zero errors', () => {
    render(<SessionSummary durationS={30} errorCount={0} usualDurationS={60} usualErrors={1} />)

    expect(screen.getByRole('heading', { name: 'Session summary' })).toBeTruthy()
    expect(screen.getByText(/Finished in 30s/)).toBeTruthy()
    expect(screen.getByText(/0 errors/)).toBeTruthy()
    expect(screen.getByText('(usually ~1m 0s)')).toBeTruthy()
    expect(screen.getByText('(usually ~1)')).toBeTruthy()
  })
})
