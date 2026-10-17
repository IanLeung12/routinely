import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { AlertContext } from './AlertContext.tsx'
import type { CareRecord } from '../resident/types.ts'

afterEach(cleanup)

const alertTs = '2026-01-10T12:00:00Z'

function record(overrides: Partial<CareRecord>): CareRecord {
  return {
    resident_id: 'r1',
    ts: '2026-01-10T00:00:00Z',
    kind: 'temperature',
    value: 37,
    note: '',
    ...overrides,
  }
}

describe('AlertContext', () => {
  it('filters to records within the window before the alert', () => {
    const inWindow = record({ ts: '2026-01-09T12:00:00Z', value: 37.5 })
    const outsideWindow = record({ ts: '2026-01-05T00:00:00Z', value: 36 })
    render(<AlertContext records={[inWindow, outsideWindow]} alertTs={alertTs} />)

    expect(screen.getByText('Temperature 37.5 °C')).toBeTruthy()
    expect(screen.queryByText('Temperature 36 °C')).toBeNull()
  })

  it('orders records newest first', () => {
    const older = record({ ts: '2026-01-08T00:00:00Z', kind: 'fluid_intake', value: 200 })
    const newer = record({ ts: '2026-01-09T00:00:00Z', kind: 'fluid_intake', value: 300 })
    render(<AlertContext records={[older, newer]} alertTs={alertTs} />)

    const items = screen.getAllByRole('listitem')
    expect(items[0].textContent).toContain('300 ml')
    expect(items[1].textContent).toContain('200 ml')
  })

  it('labels med_change rows as medication', () => {
    const med = record({ ts: '2026-01-09T00:00:00Z', kind: 'med_change', value: 'Metformin 500mg' })
    render(<AlertContext records={[med]} alertTs={alertTs} />)

    expect(screen.getByText('Medication change: Metformin 500mg')).toBeTruthy()
  })

  it('shows empty state when nothing is in the window', () => {
    render(<AlertContext records={[]} alertTs={alertTs} />)

    expect(screen.getByText('No care-record changes in the last 3 days')).toBeTruthy()
  })
})
