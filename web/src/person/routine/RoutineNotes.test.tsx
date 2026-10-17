import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { PatternMatch } from '../../contracts.ts'
import { personNote } from '../personNotes.ts'
import { RoutineNotes } from './RoutineNotes.tsx'

afterEach(cleanup)

function pattern(pattern_id: string): PatternMatch {
  return {
    pattern_id,
    name: 'Motor slowing / medication effect',
    confidence: 0.61,
    urgency: 'next_round',
    evidence: ['step durations up to 4.2 min a session from 3.0'],
    checks: ['medication_review'],
  }
}

const PATTERNS = [pattern('motor_slowing'), pattern('evening_worsening')]

describe('RoutineNotes', () => {
  it('says nothing at all when nothing was flagged', () => {
    const { container } = render(<RoutineNotes patterns={[]} supervisorNames={['Lena']} />)

    expect(container.innerHTML).toBe('')
  })

  it('rephrases each pattern for the person, naming who to mention it to', () => {
    render(<RoutineNotes patterns={PATTERNS} supervisorNames={['Lena']} />)

    for (const match of PATTERNS) {
      const note = personNote(match, 'Lena')
      expect(screen.getByRole('heading', { name: note.title })).toBeTruthy()
      expect(screen.getByText(note.body)).toBeTruthy()
    }
    // The supervisor's reading - confidence, urgency, what to rule out - stays theirs.
    expect(screen.queryByText(/Motor slowing/)).toBeNull()
    expect(screen.queryByText(/medication_review/)).toBeNull()
  })

  it('offers to tell the one person watching, and confirms once it has', () => {
    const onTell = vi.fn()
    render(
      <RoutineNotes
        patterns={[pattern('motor_slowing')]}
        supervisorNames={['Lena']}
        onTell={onTell}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Tell Lena' }))

    expect(onTell).toHaveBeenCalledWith('motor_slowing')
    expect(screen.queryByRole('button', { name: 'Tell Lena' })).toBeNull()
    expect(
      screen.getByText('Lena sees this the next time they open Routine Watch.'),
    ).toBeTruthy()
    expect(screen.getByRole('status').textContent).toBe('Shared with Lena.')
  })

  it('tells several supervisors at once', () => {
    render(<RoutineNotes patterns={[pattern('slow_drift')]} supervisorNames={['Lena', 'Ana']} />)

    fireEvent.click(screen.getByRole('button', { name: 'Tell my supervisors' }))

    expect(screen.getByRole('status').textContent).toBe('Shared with Lena and Ana.')
    expect(
      screen.getByText('Lena and Ana see this the next time they open Routine Watch.'),
    ).toBeTruthy()
  })

  it('points a person watching alone at their own next step', () => {
    render(<RoutineNotes patterns={[pattern('motor_slowing')]} supervisorNames={[]} />)

    expect(screen.queryByRole('button')).toBeNull()
    expect(screen.getByText(/Nobody else can see your routine yet/)).toBeTruthy()
    expect(screen.getByText(personNote(pattern('motor_slowing')).body)).toBeTruthy()
  })
})
