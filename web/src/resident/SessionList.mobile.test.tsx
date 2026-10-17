import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { SessionList } from './SessionList.tsx'
import css from './sessionList.css?raw'

afterEach(cleanup)

describe('SessionList at phone width', () => {
  it('renders every session at 375px', () => {
    window.innerWidth = 375
    render(
      <SessionList
        sessions={[
          {
            ts: '2026-01-01T10:00:00Z',
            resident_id: 'r1',
            task: 'tea',
            duration_s: 120,
            assisted: false,
            self_corrected: 0,
            errors: {},
          },
          {
            ts: '2026-01-02T10:00:00Z',
            resident_id: 'r1',
            task: 'tea',
            duration_s: 90,
            assisted: false,
            self_corrected: 1,
            errors: {},
          },
        ]}
        scores={[
          { ts: '2026-01-01T10:00:00Z', score: 0.1 },
          { ts: '2026-01-02T10:00:00Z', score: 0.2 },
        ]}
        threshold={0.5}
      />,
    )
    expect(screen.getAllByRole('listitem')).toHaveLength(2)
  })

  it('has a 480px media rule that stacks the row', () => {
    expect(css).toMatch(/@media \(max-width: 480px\)/)
    expect(css).toMatch(/\.session-row/)
  })
})
