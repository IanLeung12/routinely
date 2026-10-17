import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { personStatus } from '../personNotes.ts'
import { RoutineStatus } from './RoutineStatus.tsx'
import type { PersonRoutine } from './types.ts'

afterEach(cleanup)

function routine(overrides: Partial<PersonRoutine> = {}): PersonRoutine {
  return {
    person_id: 'sam',
    now: '2026-01-01T20:10:00+00:00',
    status: 'normal',
    usual_minutes: 3,
    days: [
      { date: '2025-12-31', minutes: 3, usual_minutes: 3 },
      { date: '2026-01-01', minutes: 4.2, usual_minutes: 3 },
    ],
    sessions: [],
    patterns: [],
    ...overrides,
  }
}

describe('RoutineStatus', () => {
  it('says how the week looks in the person\'s own words', () => {
    render(<RoutineStatus routine={routine()} />)

    expect(screen.getByText(personStatus('normal'))).toBeTruthy()
    expect(screen.queryByText('Change flagged for review')).toBeNull()
  })

  it('uses the flagged wording without sounding like an alert', () => {
    render(<RoutineStatus routine={routine({ status: 'flagged' })} />)

    expect(screen.getByText(personStatus('flagged'))).toBeTruthy()
  })

  it('puts today next to their own usual', () => {
    render(<RoutineStatus routine={routine()} />)

    expect(screen.getByText('Today')).toBeTruthy()
    expect(screen.getByText('4 min')).toBeTruthy()
    expect(screen.getByText('Your usual')).toBeTruthy()
    expect(screen.getByText('3 min')).toBeTruthy()
    expect(screen.getByText('about 1 min longer')).toBeTruthy()
    // Never colour alone: the direction is in the pill's own arrow and words.
    expect(screen.getByText('↑')).toBeTruthy()
  })

  it('says when today was about the same, or quicker', () => {
    render(
      <RoutineStatus
        routine={routine({ days: [{ date: '2026-01-01', minutes: 3.2, usual_minutes: 3 }] })}
      />,
    )
    expect(screen.getByText('About the same as usual')).toBeTruthy()

    cleanup()
    render(
      <RoutineStatus
        routine={routine({ days: [{ date: '2026-01-01', minutes: 1.8, usual_minutes: 3 }] })}
      />,
    )
    expect(screen.getByText('about 1 min quicker')).toBeTruthy()
    expect(screen.getByText('↓')).toBeTruthy()
  })

  it('has something calm to say before any routine is recorded', () => {
    render(<RoutineStatus routine={routine({ days: [] })} />)

    expect(screen.getByText(/Nothing recorded yet/)).toBeTruthy()
    expect(screen.queryByText('Today')).toBeNull()
  })
})
