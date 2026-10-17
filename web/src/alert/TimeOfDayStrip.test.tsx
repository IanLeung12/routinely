import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Alert, TimeOfDayErrors } from '../contracts.ts'
import { mockAlerts } from '../mock/alerts.ts'
import { AlertView } from './AlertView.tsx'
import { TimeOfDayStrip } from './TimeOfDayStrip.tsx'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

/** An evening-only worsening as the API sends it (SPEC section 7.5): clean mornings,
 * no afternoon sessions at all, every error late in the day. */
const EVENING_ONLY: TimeOfDayErrors[] = [
  { bucket: 'morning', sessions: 14, errors: 1 },
  { bucket: 'afternoon', sessions: 0, errors: 0 },
  { bucket: 'evening', sessions: 14, errors: 15 },
]

function rows() {
  return Array.from(screen.getByRole('list', { name: 'Errors by time of day' }).children)
}

describe('TimeOfDayStrip', () => {
  it('shows the three parts of the day in order, each labelled in words', () => {
    render(<TimeOfDayStrip buckets={EVENING_ONLY} />)

    expect(screen.getByText('Errors by time of day, last 14 days')).toBeTruthy()
    expect(rows().map((row) => row.textContent)).toEqual([
      'Morning before 12:00 0.1 per session (1 error in 14 sessions)',
      'Afternoon 12:00–17:00 No sessions',
      'Evening from 17:00 1.1 per session (15 errors in 14 sessions)',
    ])
  })

  it('reads the evening as the worst part of the day without relying on colour', () => {
    render(<TimeOfDayStrip buckets={EVENING_ONLY} />)
    const [morning, , evening] = rows()

    // Every number a nurse needs is text, so the bars carry nothing on their own.
    expect(within(morning as HTMLElement).getByText('0.1 per session')).toBeTruthy()
    expect(within(evening as HTMLElement).getByText('1.1 per session')).toBeTruthy()

    // The bar is errors per session against the worst part of her own day.
    const share = (row: Element) =>
      row.querySelector('.time-of-day__fill')?.getAttribute('style')
    expect(share(evening)).toContain('--share: 1')
    expect(share(morning)).toContain('--share: 0.0')
  })

  it('counts a part of the day the payload leaves out as no sessions', () => {
    render(<TimeOfDayStrip buckets={[{ bucket: 'evening', sessions: 2, errors: 4 }]} />)

    expect(rows().map((row) => row.textContent)).toEqual([
      'Morning before 12:00 No sessions',
      'Afternoon 12:00–17:00 No sessions',
      'Evening from 17:00 2.0 per session (4 errors in 2 sessions)',
    ])
  })

  it('draws no bar at all for a part of the day with no sessions', () => {
    render(<TimeOfDayStrip buckets={EVENING_ONLY} />)
    const [, afternoon] = rows()

    expect(within(afternoon as HTMLElement).getByText('No sessions')).toBeTruthy()
    expect(afternoon.querySelector('.time-of-day__fill')?.getAttribute('style')).toContain(
      '--share: 0',
    )
  })

  it('is hidden when the alert has no strip', () => {
    const { container } = render(<TimeOfDayStrip buckets={null} />)

    expect(container.innerHTML).toBe('')
    expect(screen.queryByText(/errors by time of day/i)).toBeNull()
  })

  it('is hidden when the field is absent, as it is offline', () => {
    const { container } = render(<TimeOfDayStrip />)

    expect(container.innerHTML).toBe('')
    expect(screen.queryByText(/errors by time of day/i)).toBeNull()
  })

  it('never puts the strip in diagnostic language', () => {
    render(<TimeOfDayStrip buckets={EVENING_ONLY} />)

    expect(document.body.textContent?.toLowerCase()).not.toContain('diagnos')
    expect(document.body.textContent?.toLowerCase()).not.toContain('sundown')
  })

  it('sits under the error list on the alert screen when the API sends it', async () => {
    const alert: Alert = { ...mockAlerts[0], errors_by_time_of_day: EVENING_ONLY }
    vi.stubGlobal('fetch', vi.fn((url: string) => (
      url.includes(`/alerts/${alert.alert_id}`)
        ? Promise.resolve({ ok: true, json: async () => alert })
        : Promise.reject(new Error('offline'))
    )))

    render(<AlertView alertId={alert.alert_id} onBack={() => {}} />)

    const strip = await screen.findByRole('list', { name: 'Errors by time of day' })
    expect(screen.getByText('Errors by time of day, last 14 days')).toBeTruthy()
    expect(within(strip).getByText('1.1 per session')).toBeTruthy()

    // Under the error list, inside the same card: the strip is evidence about those
    // errors, not a section of its own (SPEC section 9, screen 4).
    const errorList = strip.closest('.card')?.querySelector('.error-list')
    expect(errorList).toBeTruthy()
    expect(errorList?.compareDocumentPosition(strip)).toBe(Node.DOCUMENT_POSITION_FOLLOWING)
  })

  it('stays off the alert screen when the API sends no strip', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')))

    render(<AlertView alertId={mockAlerts[0].alert_id} onBack={() => {}} />)

    await screen.findByText(mockAlerts[0].summary)
    expect(screen.queryByText(/errors by time of day/i)).toBeNull()
  })
})
