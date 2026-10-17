import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { SessionSummary } from './SessionSummary.tsx'

afterEach(() => {
  cleanup()
})

function summaryLine(): HTMLElement {
  return document.querySelector('.session-summary__line') as HTMLElement
}

describe('SessionSummary', () => {
  it('shows duration and error count with no "usually" comparison when there is no baseline', () => {
    render(<SessionSummary durationS={220} errorCount={2} />)

    expect(summaryLine().textContent).toBe('Finished in 3m 40s · 2 errors')
    expect(screen.queryByText(/usually/)).toBeNull()
  })

  it('adds the resident\'s usual duration and error count when a baseline is given', () => {
    render(<SessionSummary durationS={220} errorCount={2} usualDurationS={170} usualErrors={1} />)

    expect(summaryLine().textContent).toBe('Finished in 3m 40s (usually ~2m 50s) · 2 errors (usually ~1)')
  })

  it('shows only the usual duration when the usual error count is unavailable', () => {
    render(<SessionSummary durationS={60} errorCount={0} usualDurationS={90} />)

    expect(summaryLine().textContent).toBe('Finished in 1m 0s (usually ~1m 30s) · 0 errors')
  })

  it('singularizes "error" for a count of one', () => {
    render(<SessionSummary durationS={30} errorCount={1} />)

    expect(summaryLine().textContent).toBe('Finished in 30s · 1 error')
  })

  it('rounds a fractional usual error count to one decimal place', () => {
    render(<SessionSummary durationS={30} errorCount={1} usualErrors={0.538} />)

    expect(summaryLine().textContent).toBe('Finished in 30s · 1 error (usually ~0.5)')
  })

  it('never uses the word "diagnose" or any of its forms', () => {
    render(<SessionSummary durationS={220} errorCount={2} usualDurationS={170} usualErrors={1} />)

    expect(document.body.textContent).not.toMatch(/diagnos/i)
  })

  it('uses the shared Card and SectionHeader components, no inline styles', () => {
    render(<SessionSummary durationS={220} errorCount={2} />)

    const card = document.querySelector('.card') as HTMLElement
    expect(card).toBeTruthy()
    expect(card.className).toContain('session-summary')
    expect(screen.getByText('Session summary').className).toBe('section-header__title')
    expect(card.querySelector('[style]')).toBeNull()
  })

  it('shows the comparison for a session the capture could be read (quality "ok")', () => {
    render(<SessionSummary durationS={220} errorCount={2} usualDurationS={170} quality="ok" />)

    expect(summaryLine().textContent).toBe('Finished in 3m 40s (usually ~2m 50s) · 2 errors')
    expect(screen.queryByText(/unclear/i)).toBeNull()
  })

  /** SPEC section 12: low-confidence capture is unclear, never an error. The pipeline
   * scores such a session 0.0 and leaves it out of the resident's history, so showing
   * the comparison here would read as a session that went perfectly (T343). */
  describe('unclear capture', () => {
    it("says the session wasn't scored, and why, instead of the comparison", () => {
      render(<SessionSummary durationS={220} errorCount={2} usualDurationS={170} usualErrors={1} quality="unclear" />)

      expect(screen.getByText("Capture unclear — this session wasn't scored")).toBeTruthy()
      expect(screen.getByText(/low light, the view blocked, or a walker or wheelchair/)).toBeTruthy()
      expect(screen.getByText(/Nothing in it is counted as an error/)).toBeTruthy()
    })

    it('shows no score, no duration and no comparison with the resident\'s normal', () => {
      render(<SessionSummary durationS={220} errorCount={2} usualDurationS={170} usualErrors={1} quality="unclear" />)

      expect(summaryLine()).toBeNull()
      expect(screen.queryByText(/Finished in/)).toBeNull()
      expect(screen.queryByText(/2 errors/)).toBeNull()
      expect(screen.queryByText(/usually/)).toBeNull()
    })

    it('keeps the heading, and announces the notice as a status', () => {
      render(<SessionSummary durationS={220} errorCount={2} quality="unclear" />)

      expect(screen.getByRole('heading', { name: 'Session summary' })).toBeTruthy()
      const status = screen.getByRole('status')
      expect(status.textContent).toContain("Capture unclear — this session wasn't scored")
    })

    it('never uses the word "diagnose" or any of its forms, and never calls this a failure', () => {
      render(<SessionSummary durationS={220} errorCount={2} quality="unclear" />)

      // SPEC section 12: unclear capture is uncertainty to show, not an error to
      // report - neither the resident's nor the camera's.
      expect(document.body.textContent).not.toMatch(/diagnos/i)
      expect(document.body.textContent).not.toMatch(/failed|failure/i)
    })
  })
})
