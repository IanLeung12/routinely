import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiUrl } from '../config.ts'
import type { Alert } from '../contracts.ts'
import { mockAlerts } from '../mock/alerts.ts'
import { alertText } from './alertText.ts'
import { AlertView } from './AlertView.tsx'

const MRS_K = mockAlerts[0]

function offline() {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')))
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
    expect(screen.getByText('5.0 vs 0.2 normal over 14 days')).toBeTruthy()
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

  it('copies the alert summary and announces success for two seconds', async () => {
    offline()
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    render(<AlertView alertId={MRS_K.alert_id} onBack={() => {}} />)
    await screen.findByText(MRS_K.summary)
    vi.useFakeTimers()

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Copy summary' }))
    })

    expect(writeText).toHaveBeenCalledWith(alertText(MRS_K))
    expect(screen.getByText('Copied').getAttribute('role')).toBe('status')
    act(() => { vi.advanceTimersByTime(2000) })
    expect(screen.queryByText('Copied')).toBeNull()
    vi.useRealTimers()
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
    expect(screen.getByRole('img', { name: /today and usual skeleton replay/i })).toBeTruthy()
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

    releases.forEach((release) => release())
    expect(await screen.findByText('No replay available')).toBeTruthy()
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
    await screen.findByText('Current threshold: 1.2')

    fireEvent.click(screen.getByRole('button', { name: 'False alarm' }))

    expect(await screen.findByText('Current threshold: 2.5')).toBeTruthy()
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
    await screen.findByText('Current threshold: 1.2')
    fireEvent.click(screen.getByRole('button', { name: 'Confirmed' }))

    const picker = await screen.findByRole('group', { name: 'What was it? (optional)' })
    fireEvent.click(within(picker).getByRole('button', { name: 'Sudden change' }))

    expect(await screen.findByRole('button', { name: 'Sudden change', pressed: true })).toBeTruthy()
    expect(posted).toEqual([
      JSON.stringify({ verdict: 'confirmed', cause: null }),
      JSON.stringify({ verdict: 'confirmed', cause: 'sudden_change' }),
    ])
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
})
