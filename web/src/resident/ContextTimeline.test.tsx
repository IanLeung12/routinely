import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { ContextTimeline } from './ContextTimeline.tsx'
import type { CareRecord } from './types.ts'

afterEach(cleanup)

describe('ContextTimeline', () => {
  it('shows an empty state without care records', () => {
    render(<ContextTimeline records={[]} />)

    expect(screen.getByText('No care records for this resident.')).toBeTruthy()
    expect(screen.queryByRole('list')).toBeNull()
  })

  it('renders readable care records newest first', () => {
    const records: CareRecord[] = [
      { resident_id: 'resident-1', ts: '2026-10-17T08:00:00Z', kind: 'temperature', value: 37.9, note: '' },
      { resident_id: 'resident-1', ts: '2026-10-17T10:00:00Z', kind: 'med_change', value: 'Reduced evening dose', note: 'Review tomorrow' },
      { resident_id: 'resident-1', ts: '2026-10-17T09:00:00Z', kind: 'fluid_intake', value: 800, note: '' },
    ]
    render(<ContextTimeline records={records} />)

    const items = screen.getAllByRole('listitem')
    expect(items).toHaveLength(3)
    expect(within(items[0]).getByText('Medication change: Reduced evening dose')).toBeTruthy()
    expect(within(items[1]).getByText('Fluid intake 800 ml')).toBeTruthy()
    expect(within(items[2]).getByText('Temperature 37.9 °C')).toBeTruthy()
    expect(within(items[0]).getByText('Review tomorrow')).toBeTruthy()
  })
})
