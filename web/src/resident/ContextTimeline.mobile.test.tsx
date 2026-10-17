import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { ContextTimeline } from './ContextTimeline.tsx'
import css from './contextTimeline.css?raw'

afterEach(cleanup)

describe('ContextTimeline at phone width', () => {
  it('keeps long care-record notes visible at 375px', () => {
    window.innerWidth = 375
    const note = 'LongCareRecordLabelWithoutAnySpaces'.repeat(8)
    render(
      <ContextTimeline records={[
        { ts: '2026-01-01T10:00:00Z', kind: 'temperature', value: 37, note },
      ]} />,
    )
    expect(screen.getAllByRole('listitem')).toHaveLength(1)
    expect(screen.getByText(note)).toBeTruthy()
  })

  it('stacks the date above text below 480px', () => {
    expect(css).toMatch(/@media \(max-width: 480px\)\s*\{\s*\.context-timeline \.context-record\s*\{[^}]*display: flex;[^}]*flex-direction: column;[^}]*align-items: flex-start;/)
  })

  it('allows dates, labels and notes to wrap long words', () => {
    expect(css).toMatch(/\.context-when,\s*\.context-what,\s*\.context-note\s*\{[^}]*min-width: 0;[^}]*white-space: normal;[^}]*overflow-wrap: anywhere;/)
  })
})
