import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { SessionList } from './SessionList.tsx'
import type { ResidentSession } from './types.ts'

afterEach(cleanup)

function session(ts: string, overrides: Partial<ResidentSession> = {}): ResidentSession {
  return {
    resident_id: 'resident', ts, task: 'tea', errors: {}, self_corrected: 0,
    duration_s: 125, assisted: false, ...overrides,
  }
}

describe('SessionList', () => {
  it('renders one row per session newest first with formatted dates, scores, and errors', () => {
    const earlier = session('2026-01-01T08:12:00Z')
    const later = session('2026-01-02T18:03:00Z', { errors: { omission: 1, hesitation: 2 } })
    const sessions = [earlier, later]
    render(<SessionList sessions={sessions} scores={[
      { ts: earlier.ts, score: 0 }, { ts: later.ts, score: 5 },
    ]} threshold={4} />)

    const rows = screen.getAllByRole('listitem')
    expect(rows).toHaveLength(2)
    expect(within(rows[0]).getByText('2 Jan, 18:03')).toBeTruthy()
    expect(within(rows[0]).getByText('5.0')).toBeTruthy()
    expect(within(rows[0]).getByText('skipped step ×1').className).toContain('pill--negative')
    expect(within(rows[0]).getByText('long pause ×2').className).toContain('pill--neutral')
    expect(within(rows[0]).getByText('2m 05s')).toBeTruthy()
    expect(rows[0].classList.contains('session-row--above')).toBe(true)
    expect(within(rows[1]).getByText('1 Jan, 08:12')).toBeTruthy()
    expect(within(rows[1]).getByText('0.0')).toBeTruthy()
    expect(within(rows[1]).getByText('no errors')).toBeTruthy()
    expect(sessions).toEqual([earlier, later])
  })

  it('shows assistance, self-corrected slips, and missing scores', () => {
    render(<SessionList sessions={[
      session('2026-01-01T08:00:00Z', { assisted: true, self_corrected: 1, errors: { omission: 1 } }),
    ]} scores={[]} threshold={4} />)

    expect(screen.getByText('assisted, not counted')).toBeTruthy()
    expect(screen.getByText('· 1 self-corrected')).toBeTruthy()
    expect(screen.getByText('—')).toBeTruthy()
    expect(screen.queryByText('skipped step ×1')).toBeNull()
    expect(screen.getByRole('listitem').classList.contains('session-row--above')).toBe(false)
  })

  it('does not mark a score equal to the threshold as above it', () => {
    const recorded = session('2026-01-01T08:00:00Z')
    render(<SessionList sessions={[recorded]} scores={[{ ts: recorded.ts, score: 4 }]} threshold={4} />)
    expect(screen.getByRole('listitem').classList.contains('session-row--above')).toBe(false)
  })

  it('shows the empty state when there are no sessions', () => {
    render(<SessionList sessions={[]} scores={[]} threshold={4} />)
    expect(screen.getByText('No sessions recorded yet.')).toBeTruthy()
    expect(screen.queryByRole('list')).toBeNull()
  })
})
