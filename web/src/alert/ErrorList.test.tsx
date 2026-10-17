import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { TaskError } from '../contracts.ts'
import { ErrorList } from './ErrorList.tsx'

afterEach(cleanup)

function error(type: TaskError['type'], t_start = 65.9): TaskError {
  return {
    error_id: `error-${type}`, session_id: 'session', type, step_id: 'pour_water',
    t_start, t_end: t_start + 1, evidence: [],
  }
}

describe('ErrorList', () => {
  it.each([
    ['omission', 'skipped pour water', 'red'],
    ['perseveration', 'repeated pour water', 'amber'],
    ['sequence', 'pour water out of order', 'amber'],
    ['substitution', 'wrong object for pour water', 'red'],
    ['hesitation', 'long pause at pour water', 'grey'],
    ['abandonment', 'stopped before pour water', 'grey'],
  ] as const)('describes %s with the right chip and timestamp', (type, phrase, color) => {
    render(<ErrorList errors={[error(type)]} onOpen={() => {}} />)

    expect(screen.getByText(phrase)).toBeTruthy()
    expect(screen.getByText('1:05')).toBeTruthy()
    expect(screen.getByText(type).className).toBe(`error-chip error-chip--${color}`)
    expect(screen.getByRole('button', { name: `Open evidence: ${phrase} at 1:05` })).toBeTruthy()
  })

  it('opens the selected error evidence', () => {
    const selected = error('omission', 5)
    const onOpen = vi.fn()
    render(<ErrorList errors={[selected]} onOpen={onOpen} />)

    fireEvent.click(screen.getByRole('button', { name: 'Open evidence: skipped pour water at 0:05' }))
    expect(onOpen).toHaveBeenCalledWith(selected)
  })

  it('describes errors without a specific step', () => {
    render(<ErrorList errors={[{ ...error('abandonment'), step_id: null }]} onOpen={() => {}} />)
    expect(screen.getByText('stopped before this step')).toBeTruthy()
  })

  it('renders an empty-state message for no errors', () => {
    render(<ErrorList errors={[]} onOpen={() => {}} />)
    expect(screen.getByText('No errors recorded for this alert.')).toBeTruthy()
    expect(screen.queryByRole('button')).toBeNull()
  })
})
