import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiUrl } from '../config.ts'
import type { Alert } from '../contracts.ts'
import { mockAlerts } from '../mock/alerts.ts'
import { mockResidentDetail } from '../mock/residentDetail.ts'
import { alertText } from './alertText.ts'
import alertCss from './alert.css?raw'
import { AlertView } from './AlertView.tsx'

const MRS_K = mockAlerts[0]
const MRS_K_DETAIL = mockResidentDetail('mrs-k')

function offline() {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')))
}

/** The number under one label in the recap card's stat strip ("Error score" -> "5.0"),
 * which is where the baseline comparison lives since T405. */
function stat(label: string): string {
  const term = screen.getByText(label)
  return term.nextElementSibling?.querySelector('.alert-stat__number')?.textContent ?? ''
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  mockAlerts[0].feedback = null
})

describe('AlertView', () => {
  it('reads in 10 seconds: summary, baseline comparison, errors and checks', async () => {
    offline()

    render(<AlertView alertId={MRS_K.alert_id} onBack={() => {}} />)

    expect(await screen.findByText(MRS_K.summary)).toBeTruthy()
    expect(stat('Error score')).toBe('5.0')
    expect(stat('Their usual')).toBe('0.2')
    expect(screen.getByText('over 14 days')).toBeTruthy()
    expect(stat('Flag threshold')).toBe('1.2')
    expect(screen.getByText('0:42')).toBeTruthy()
    expect(screen.getByText('1:15')).toBeTruthy()
    expect(screen.getAllByRole('button', { name: /open evidence/i })).toHaveLength(2)
    expect(screen.getByText('Consistent with: Sudden change')).toBeTruthy()
    expect(screen.getByText('Rule out acute infection before assuming cognitive decline')).toBeTruthy()
    expect(screen.getByText('Check for infection / UTI')).toBeTruthy()
    expect(screen.getByText('Check hydration')).toBeTruthy()
    expect(screen.getByText('Review recent medication changes')).toBeTruthy()
    expect(screen.getByText('Run a CAM delirium screen')).toBeTruthy()
    expect(await screen.findByRole('button', { name: /play/i })).toBeTruthy()
    expect(document.body.textContent?.toLowerCase()).not.toContain('diagnos')
  })

  it('leads with a recap card: the flagged chip, the summary and the numbers under it', async () => {
    offline()

    render(<AlertView alertId={MRS_K.alert_id} onBack={() => {}} />)
    await screen.findByText(MRS_K.summary)

    // The status is a chip beside the heading, and says what it means in words.
    expect(screen.getByLabelText('Change flagged for review')).toBeTruthy()

    const recap = screen.getByRole('heading', { name: 'What changed' }).closest('.card') as HTMLElement
    expect(recap.className).toContain('alert-recap')
    expect(within(recap).getByText(MRS_K.summary)).toBeTruthy()
    expect(Array.from(recap.querySelectorAll('.alert-stat__label')).map((label) => label.textContent))
      .toEqual(['Error score', 'Their usual', 'Flag threshold'])
    expect(within(recap).getByRole('button', { name: 'Copy summary' })).toBeTruthy()
  })

  it('shows each error as one dense row: type pill, what happened, timestamp', async () => {
    offline()

    render(<AlertView alertId={MRS_K.alert_id} onBack={() => {}} />)
    await screen.findByText('0:42')

    const rows = screen.getAllByRole('button', { name: /open evidence/i })
    expect(rows[0].className).toContain('row--interactive')
    const first = within(rows[0])
    expect(first.getByText('omission').className).toBe('error-chip error-chip--red')
    expect(first.getByText('skipped teabag in cup')).toBeTruthy()
    expect(first.getByText('0:42').className).toContain('tabular-nums')
  })

  it('puts the replay and the ghost overlay in their own labelled media frames', async () => {
    offline()

    const { container } = render(<AlertView alertId={MRS_K.alert_id} onBack={() => {}} />)
    await screen.findByRole('button', { name: /play/i })

    const labels = Array.from(container.querySelectorAll('.media-frame .media-frame__label'))
    expect(labels.map((label) => label.textContent)).toEqual(['This session', 'Today over usual'])
  })

  it('copies the alert summary and announces success for two seconds', async () => {
    offline()
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    render(<AlertView alertId={MRS_K.alert_id} onBack={() => {}} />)
    await screen.findByText(MRS_K.summary)
    await screen.findByRole('heading', { level: 1, name: /mrs\. k/i })
    vi.useFakeTimers()

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Copy summary' }))
    })

    expect(writeText).toHaveBeenCalledWith(alertText(MRS_K, 'Mrs. K'))
    expect(screen.getByText('Copied').getAttribute('role')).toBe('status')
    act(() => { vi.advanceTimersByTime(2000) })
    expect(screen.queryByText('Copied')).toBeNull()
    vi.useRealTimers()
  })

  it('names the resident by the name the API has, not one guessed from the id', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    vi.stubGlobal('fetch', vi.fn((url: string) => {
      if (url.includes(`/alerts/${MRS_K.alert_id}`)) {
        return Promise.resolve({ ok: true, json: async () => MRS_K })
      }
      if (url.includes('/residents/mrs-k')) {
        return Promise.resolve({ ok: true, json: async () => ({ ...MRS_K_DETAIL, name: 'Mrs. Kowalski' }) })
      }
      return Promise.reject(new Error('offline'))
    }))

    render(<AlertView alertId={MRS_K.alert_id} onBack={() => {}} />)

    expect(await screen.findByRole('heading', { level: 1, name: 'Mrs. Kowalski flagged for review' })).toBeTruthy()

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Copy summary' }))
    })

    expect(writeText).toHaveBeenCalledWith(alertText(MRS_K, 'Mrs. Kowalski'))
    expect(writeText.mock.calls[0][0]).toContain('Person: Mrs. Kowalski')
  })

  it('falls back to the resident id when the API has no name for them', async () => {
    const alert: Alert = { ...MRS_K, alert_id: 'nobody-alert', resident_id: 'resident-7' }
    vi.stubGlobal('fetch', vi.fn((url: string) => {
      if (url.includes('/alerts/nobody-alert')) {
        return Promise.resolve({ ok: true, json: async () => alert })
      }
      return Promise.reject(new Error('offline'))
    }))

    render(<AlertView alertId="nobody-alert" onBack={() => {}} />)

    expect(await screen.findByRole('heading', { level: 1, name: 'resident-7 flagged for review' })).toBeTruthy()
  })

  it('shows a recent care record from the resident near the alert', async () => {
    const alert: Alert = { ...MRS_K, created_at: '2026-01-01T20:30:00Z' }
    const fetchMock = vi.fn((url: string) => {
      if (url.includes(`/alerts/${MRS_K.alert_id}`)) {
        return Promise.resolve({ ok: true, json: async () => alert })
      }
      return Promise.reject(new Error('offline'))
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<AlertView alertId={MRS_K.alert_id} onBack={() => {}} />)

    expect(await screen.findByText('Recent care records')).toBeTruthy()
    expect(await screen.findByText('Medication change: amoxicillin')).toBeTruthy()
  })

  it('shows no clear pattern when an alert has no patterns', async () => {
    const alert: Alert = { ...MRS_K, patterns: [] }
    const fetchMock = vi.fn((url: string) => {
      if (url.includes(`/alerts/${MRS_K.alert_id}`)) {
        return Promise.resolve({ ok: true, json: async () => alert })
      }
      return Promise.reject(new Error('offline'))
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<AlertView alertId={MRS_K.alert_id} onBack={() => {}} />)

    expect(await screen.findByText('Change detected, no clear pattern.')).toBeTruthy()
  })

  it('shows the evidence replay card with the skeleton replay and ghost overlay', async () => {
    offline()

    const { container } = render(<AlertView alertId={MRS_K.alert_id} onBack={() => {}} />)

    expect(await screen.findByRole('button', { name: /play/i })).toBeTruthy()
    expect(screen.getByRole('slider', { name: /replay position/i })).toBeTruthy()
    expect(screen.getByRole('img', { name: /today's routine drawn over the usual routine/i })).toBeTruthy()
    expect(container.querySelectorAll('video, img')).toHaveLength(0)
  })

  it('shows a loading state for the evidence card before the replay resolves', async () => {
    const releases: Array<() => void> = []
    const fetchMock = vi.fn((url: string) => {
      if (url.includes('/alerts/')) return Promise.resolve({ ok: true, json: async () => MRS_K })
      return new Promise((resolve) => {
        releases.push(() => resolve({ ok: true, json: async () => ({ frames: [] }) }))
      })
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<AlertView alertId={MRS_K.alert_id} onBack={() => {}} />)

    expect(await screen.findByText('Loading replay…')).toBeTruthy()

    await act(async () => {
      releases.forEach((release) => release())
    })
    await waitFor(() => expect(screen.getByText('No replay available')).toBeTruthy(), { timeout: 5000 })
  })

  it('shows an empty state for the evidence card when no replay is available', async () => {
    const alert: Alert = { ...MRS_K, alert_id: 'no-replay-alert' }
    const fetchMock = vi.fn((url: string) => {
      if (url.includes('/alerts/no-replay-alert')) {
        return Promise.resolve({ ok: true, json: async () => alert })
      }
      return Promise.reject(new Error('offline'))
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<AlertView alertId="no-replay-alert" onBack={() => {}} />)

    expect(await screen.findByText('No skeleton replay available for this alert.')).toBeTruthy()
  })

  it('opens an error row through onOpenEvidence', async () => {
    offline()
    const onOpenEvidence = vi.fn()

    render(<AlertView alertId={MRS_K.alert_id} onBack={() => {}} onOpenEvidence={onOpenEvidence} />)
    await screen.findByText('0:42')

    fireEvent.click(screen.getByRole('button', { name: /skipped teabag in cup at 0:42/i }))

    expect(onOpenEvidence).toHaveBeenCalledWith(MRS_K.errors[0])
  })

  it('calls onBack when the back button is clicked', async () => {
    offline()
    const onBack = vi.fn()

    render(<AlertView alertId={MRS_K.alert_id} onBack={onBack} />)
    await screen.findByText('0:42')

    fireEvent.click(screen.getByRole('button', { name: /back/i }))

    expect(onBack).toHaveBeenCalledTimes(1)
  })

  it('posts feedback and shows the updated threshold after "False alarm"', async () => {
    const updated: Alert = {
      ...MRS_K,
      baseline: { ...MRS_K.baseline, threshold: 2.5 },
      feedback: { verdict: 'false_alarm', by: 'nurse', at: '2026-10-17T10:00:00Z' },
    }
    const fetchMock = vi.fn((_url: string, init?: RequestInit) => {
      if (init?.method === 'POST') {
        return Promise.resolve({ ok: true, json: async () => updated })
      }
      return Promise.reject(new Error('offline'))
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<AlertView alertId={MRS_K.alert_id} onBack={() => {}} />)
    await screen.findByText('Flag threshold')
    expect(stat('Flag threshold')).toBe('1.2')

    fireEvent.click(screen.getByRole('button', { name: 'False alarm' }))

    await waitFor(() => expect(stat('Flag threshold')).toBe('2.5'))
    expect(fetchMock).toHaveBeenCalledWith(
      `${apiUrl}/alerts/${MRS_K.alert_id}/feedback`,
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('asks what it was after confirming, and posts the pattern the nurse picks', async () => {
    const confirmed: Alert = {
      ...MRS_K,
      feedback: { verdict: 'confirmed', by: 'nurse', at: '2026-10-17T10:00:00Z', cause: null },
    }
    const withCause: Alert = { ...confirmed, feedback: { ...confirmed.feedback!, cause: 'sudden_change' } }
    const posted: string[] = []
    const fetchMock = vi.fn((_url: string, init?: RequestInit) => {
      if (init?.method === 'POST') {
        posted.push(String(init.body))
        return Promise.resolve({ ok: true, json: async () => (posted.length > 1 ? withCause : confirmed) })
      }
      return Promise.reject(new Error('offline'))
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<AlertView alertId={MRS_K.alert_id} onBack={() => {}} />)
    await screen.findByText('Flag threshold')
    fireEvent.click(screen.getByRole('button', { name: 'Confirmed' }))

    const picker = await screen.findByRole('group', { name: 'What was it? (optional)' })
    fireEvent.click(within(picker).getByRole('button', { name: 'Sudden change' }))

    expect(await screen.findByRole('button', { name: 'Sudden change', pressed: true })).toBeTruthy()
    expect(posted).toEqual([
      JSON.stringify({ verdict: 'confirmed', cause: null }),
      JSON.stringify({ verdict: 'confirmed', cause: 'sudden_change' }),
    ])
  })

  it('has one h1 naming the resident, with h2 sections in reading order', async () => {
    offline()

    render(<AlertView alertId={MRS_K.alert_id} onBack={() => {}} />)
    await screen.findByText(MRS_K.summary)
    await screen.findByRole('heading', { level: 1, name: /mrs\. k.*flagged for review/i })

    const headings = screen.getAllByRole('heading')
    const h1s = headings.filter((h) => h.tagName === 'H1')
    expect(h1s).toHaveLength(1)

    const h2Titles = headings.filter((h) => h.tagName === 'H2').map((h) => h.textContent)
    expect(h2Titles).toEqual([
      'What changed',
      'Possible patterns',
      'Errors',
      'Evidence',
      'Suggested checks',
      'Feedback',
    ])
  })

  it('moves focus to the h1 once the alert loads', async () => {
    offline()

    render(<AlertView alertId={MRS_K.alert_id} onBack={() => {}} />)

    const heading = await screen.findByRole('heading', { level: 1 })
    await waitFor(() => expect(document.activeElement).toBe(heading))
  })

  it('wraps the view in a landmark labelled by the h1', async () => {
    offline()

    render(<AlertView alertId={MRS_K.alert_id} onBack={() => {}} />)
    const heading = await screen.findByRole('heading', { level: 1 })

    expect(screen.getByRole('region', { name: heading.textContent ?? '' })).toBeTruthy()
  })

  it('shows loading until an empty alert result resolves, then the shared empty state', async () => {
    let resolveFetch!: (response: { ok: boolean; status: number }) => void
    vi.stubGlobal('fetch', vi.fn(() => new Promise((resolve) => {
      resolveFetch = resolve
    })))

    render(<AlertView alertId="nobody" onBack={() => {}} />)

    expect(screen.getByText('Loading alert…')).toBeTruthy()
    expect(screen.queryByText('No change flagged for review.')).toBeNull()

    resolveFetch({ ok: false, status: 404 })

    const emptyState = await screen.findByText('No change flagged for review.')
    expect(emptyState.className).toBe('empty-state')
    expect(screen.queryByText('Loading alert…')).toBeNull()
  })

  it('marks the back button, replay evidence and feedback as no-print, keeping the rest printable', async () => {
    offline()

    render(<AlertView alertId={MRS_K.alert_id} onBack={() => {}} />)
    await screen.findByText(MRS_K.summary)

    expect(screen.getByRole('button', { name: /back/i }).className).toContain('no-print')

    const evidenceHeading = screen.getByRole('heading', { name: 'Evidence' })
    expect(evidenceHeading.closest('.card')?.className).toContain('no-print')

    const feedbackHeading = screen.getByRole('heading', { name: 'Feedback' })
    expect(feedbackHeading.closest('.card')?.className).toContain('no-print')

    const errorsHeading = screen.getByRole('heading', { name: 'Errors' })
    expect(errorsHeading.closest('.card')?.className ?? '').not.toContain('no-print')

    const patternsHeading = screen.getByRole('heading', { name: 'Possible patterns' })
    expect(patternsHeading.closest('.card')?.className ?? '').not.toContain('no-print')

    const checksHeading = screen.getByRole('heading', { name: 'Suggested checks' })
    expect(checksHeading.closest('.card')?.className ?? '').not.toContain('no-print')
  })

  it('prints the alert when the Print button is clicked, and hides the button itself', async () => {
    offline()
    const printSpy = vi.fn()
    vi.stubGlobal('print', printSpy)

    render(<AlertView alertId={MRS_K.alert_id} onBack={() => {}} />)
    await screen.findByText(MRS_K.summary)

    const printButton = screen.getByRole('button', { name: 'Print' })
    expect(printButton.className).toContain('no-print')

    fireEvent.click(printButton)

    expect(printSpy).toHaveBeenCalledTimes(1)
  })
})

/** jsdom doesn't evaluate @media conditions for getComputedStyle, so this checks the
 * stylesheet text directly (verified against a real Chrome print preview of the Mrs. K
 * alert for T289: resident, errors, patterns, rule-outs and checks print in black on
 * white over 1-2 pages, with no dark backgrounds, nav, replay or feedback buttons).
 * The shared no-print/black-on-white rules moved to print.css in T353; see
 * print.test.ts. This file keeps the screen-specific app-shell rule. */
describe('alert.css print layout', () => {
  it('hides the app shell header and demo banner while an alert is open', () => {
    const printBlock = alertCss.match(/@media print \{([\s\S]*)\}\s*$/)?.[1]
    expect(printBlock).toBeTruthy()

    expect(printBlock).toMatch(/\.app:has\(\.alert-view\) > header\s*,/)
    expect(printBlock).toMatch(/\.app:has\(\.alert-view\) > \.demo-banner\s*\{[^}]*display:\s*none/)
  })
})
