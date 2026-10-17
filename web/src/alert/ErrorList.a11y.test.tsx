import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import type { TaskError } from '../contracts.ts'
import { ErrorList } from './ErrorList.tsx'

afterEach(cleanup)

const ERRORS: TaskError[] = [
  {
    error_id: 'e1',
    session_id: 's1',
    type: 'omission',
    step_id: 'pour_teabag',
    t_start: 65,
    t_end: 70,
    evidence: [],
  },
]

describe('ErrorList accessibility', () => {
  it('gives every error item an accessible name with its time and step', () => {
    render(<ErrorList errors={ERRORS} onOpen={() => {}} />)

    expect(
      screen.getByRole('button', { name: 'Open evidence: skipped pour teabag at 1:05' }),
    ).toBeTruthy()
  })
})
