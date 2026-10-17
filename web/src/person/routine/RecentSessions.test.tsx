import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { RecentSessions } from './RecentSessions.tsx'
import type { PersonRoutine, RoutineSession } from './types.ts'

afterEach(cleanup)

function session(overrides: Partial<RoutineSession> = {}): RoutineSession {
  return {
    session_id: 's1',
    started_at: '2026-01-01T08:10:00+00:00',
    task: 'Making tea',
    duration_s: 180,
    errors: {},
    ...overrides,
  }
}

function routine(sessions: RoutineSession[]): PersonRoutine {
  return {
    person_id: 'sam',
    now: '2026-01-01T20:10:00+00:00',
    status: 'flagged',
    usual_minutes: 3,
    days: [],
    sessions,
    patterns: [],
  }
}

describe('RecentSessions', () => {
  it('says what went the usual way, and when', () => {
    render(<RecentSessions routine={routine([session()])} />)

    expect(screen.getByText('Making tea')).toBeTruthy()
    expect(
      screen.getByText('This morning · The whole routine went the way it usually does.'),
    ).toBeTruthy()
    expect(screen.getByText('3 min')).toBeTruthy()
    expect(screen.getByText('Like your usual')).toBeTruthy()
  })

  it('says what looked different without making it a verdict', () => {
    render(
      <RecentSessions
        routine={routine([
          session({
            session_id: 's2',
            started_at: '2026-01-01T18:40:00+00:00',
            duration_s: 318,
            errors: { omission: 1 },
          }),
        ])}
      />,
    )

    expect(
      screen.getByText(
        'This evening · A step was missed and it took about 5 min instead of your usual 3 min. The rest went the way it usually does.',
      ),
    ).toBeTruthy()
    expect(screen.getByText('A bit different')).toBeTruthy()
  })

  it('shows the newest few and no more', () => {
    const sessions = Array.from({ length: 8 }, (_, index) =>
      session({ session_id: `s${index}`, task: `Routine ${index}` }))

    render(<RecentSessions routine={routine(sessions)} />)

    expect(screen.getAllByRole('listitem').length).toBe(5)
    expect(screen.getByText('Routine 0')).toBeTruthy()
    expect(screen.queryByText('Routine 5')).toBeNull()
  })

  it('has an empty state before the first session', () => {
    render(<RecentSessions routine={routine([])} />)

    expect(screen.getByText('No sessions yet. They show up here as you go.')).toBeTruthy()
    expect(screen.queryByRole('listitem')).toBeNull()
  })
})
