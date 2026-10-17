import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from '../App.tsx'
import { apiUrl } from '../config.ts'
import { mockResidentDetail } from '../mock/residentDetail.ts'
import { ResidentDetail } from './ResidentDetail.tsx'
import { fetchDrift, fetchResident } from './api.ts'
import { dailyScores } from './days.ts'
import { formatDuration, formatErrors } from './format.ts'
import type { Resident } from './types.ts'

vi.mock('./api.ts', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./api.ts')>()
  return { ...actual, fetchResident: vi.fn(actual.fetchResident) }
})

const MRS_K = mockResidentDetail('mrs-k') as Resident

function offline() {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')))
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.mocked(fetchResident).mockClear()
})

describe('ResidentDetail', () => {
  it('shows the slow-drift mock card for the trending resident', async () => {
    offline()
    render(<ResidentDetail residentId="mr-chen" onBack={() => {}} />)

    const card = await screen.findByRole('region', { name: 'Slow drift' })
    expect(card.getAttribute('data-state')).toBe('trending')
    expect(card.textContent).toContain('Error score rising about +0.70 per day over 7 days.')
  })

  it('omits the drift card when the resident has no drift data', async () => {
    offline()
    render(<ResidentDetail residentId="mrs-k" onBack={() => {}} />)
    await screen.findByRole('heading', { level: 2, name: 'Mrs. K' })

    expect(screen.queryByRole('region', { name: 'Slow drift' })).toBeNull()
  })

  it('falls back to the mock resident when the API is unreachable', async () => {
    offline()

    const { container } = render(<ResidentDetail residentId="mrs-k" onBack={() => {}} />)

    expect(await screen.findByRole('heading', { level: 2, name: 'Mrs. K' })).toBeTruthy()
    expect(screen.getByText('Room 204')).toBeTruthy()
    expect(screen.getByText('Flagged')).toBeTruthy()
    expect(container.querySelectorAll('.session-row')).toHaveLength(MRS_K.sessions.length)
  })

  it('renders the baseline chart with the threshold and the latest session', async () => {
    offline()

    render(<ResidentDetail residentId="mrs-k" onBack={() => {}} />)

    const chart = await screen.findByRole('img', { name: /baseline chart/i })
    const label = chart.getAttribute('aria-label') ?? ''
    expect(label).toContain(`${MRS_K.scores.length} sessions`)
    expect(label).toContain('latest score 5.0')
    expect(label).toContain('flag threshold 4.5')
    expect(label).toContain('2 sessions above it')
    expect(screen.getByText('Latest session 5.0')).toBeTruthy()
    // The newest point is drawn large and in the alarm colour.
    const latest = chart.querySelector('.chart-point--latest')
    expect(latest?.getAttribute('r')).toBe('6')
    expect(latest?.getAttribute('class')).toContain('chart-point--above')
  })

  it('renders the sessions newest first with scores, errors and duration', async () => {
    offline()

    const { container } = render(<ResidentDetail residentId="mrs-k" onBack={() => {}} />)
    await screen.findByRole('heading', { level: 2, name: 'Mrs. K' })

    const rows = [...container.querySelectorAll('.session-row')]
    expect(rows[0].querySelector('.session-when')?.textContent).toBe('1 Jan, 18:02')
    expect(rows[0].querySelector('.session-score')?.textContent).toBe('5.0')
    expect(rows[0].querySelector('.session-detail')?.textContent).toContain(
      'skipped step ×1 · long pause ×2',
    )
    expect(rows[0].querySelector('.session-detail')?.textContent).toContain('above threshold')
    expect(rows[0].querySelector('.session-duration')?.textContent).toBe('4m 01s')
    expect(rows[0].className).toContain('session-row--above')

    const quiet = rows[rows.length - 1]
    expect(quiet.querySelector('.session-when')?.textContent).toBe('25 Dec, 08:10')
    expect(quiet.querySelector('.session-detail')?.textContent).toBe('no errors')
    expect(quiet.className).not.toContain('session-row--above')
  })

  it('renders the care records a nurse reads next to the chart', async () => {
    offline()

    const { container } = render(<ResidentDetail residentId="mrs-k" onBack={() => {}} />)
    await screen.findByRole('heading', { level: 2, name: 'Mrs. K' })

    expect(container.querySelectorAll('.context-record')).toHaveLength(MRS_K.care_records.length)
    expect(screen.getByText('Medication change: amoxicillin')).toBeTruthy()
    expect(screen.getByText('new antibiotic started')).toBeTruthy()
    expect(screen.getByText('Temperature 38.1 °C')).toBeTruthy()
    expect(screen.getByText('Fluid intake 700 ml')).toBeTruthy()
    const newest = container.querySelector('.context-record')
    expect(newest?.querySelector('.context-when')?.textContent).toBe('1 Jan, 20:00')
  })

  it('fills the heat calendar slot with one cell per day', async () => {
    offline()

    render(<ResidentDetail residentId="mrs-k" onBack={() => {}} />)
    await screen.findByRole('heading', { level: 2, name: 'Mrs. K' })

    const calendar = screen.getByRole('grid', { name: /daily error scores/i })
    expect(calendar.querySelectorAll('[role="gridcell"]')).toHaveLength(
      dailyScores(MRS_K.scores).length,
    )
  })

  it('renders what the API serves when it is reachable', async () => {
    const payload: Resident = {
      id: 'mr-okafor',
      name: 'Mr. Okafor',
      room: '301',
      status: 'watch',
      top_pattern: null,
      scores: [
        { ts: '2026-01-01T08:00:00+00:00', score: 0 },
        { ts: '2026-01-02T08:00:00+00:00', score: 3 },
      ],
      sessions: [
        {
          resident_id: 'mr-okafor',
          ts: '2026-01-02T08:00:00+00:00',
          task: 'tea',
          errors: { omission: 1 },
          self_corrected: 0,
          duration_s: 195,
          assisted: false,
        },
      ],
      care_records: [
        {
          resident_id: 'mr-okafor',
          ts: '2026-01-02T08:00:00+00:00',
          kind: 'temperature',
          value: 37.4,
          note: '',
        },
      ],
      baseline: { mean: 1.5, std: 1.5, threshold: 4.5 },
    }
    const fetchMock = vi.fn().mockImplementation(async (url: string) => ({
      ok: true, json: async () => url.endsWith('/drift') ? null : payload,
    }))
    vi.stubGlobal('fetch', fetchMock)

    render(<ResidentDetail residentId="mr-okafor" onBack={() => {}} />)

    expect(await screen.findByRole('heading', { level: 2, name: 'Mr. Okafor' })).toBeTruthy()
    expect(fetchMock).toHaveBeenCalledWith(`${apiUrl}/residents/mr-okafor`)
    expect(screen.getByText('Temperature 37.4 °C')).toBeTruthy()
    expect(screen.getByText('skipped step ×1')).toBeTruthy()
  })

  it('says so when neither the API nor the mocks know the resident (404)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, json: async () => ({}) }))

    render(<ResidentDetail residentId="nobody" onBack={() => {}} />)

    expect(await screen.findByText('Resident not found.')).toBeTruthy()
    expect(screen.getByRole('button', { name: /unit overview/i })).toBeTruthy()
  })

  it('shows an error with a retry button when the resident fetch fails, and recovers on retry', async () => {
    offline()
    vi.mocked(fetchResident).mockRejectedValueOnce(new Error('down'))

    render(<ResidentDetail residentId="mrs-k" onBack={() => {}} />)

    expect(await screen.findByText(/Could not reach the server/)).toBeTruthy()
    expect(screen.queryByRole('heading', { level: 2 })).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: /try again/i }))

    expect(await screen.findByRole('heading', { level: 2, name: 'Mrs. K' })).toBeTruthy()
  })

  it('shows empty-state copy instead of blank charts for a resident with zero sessions', async () => {
    const empty: Resident = {
      id: 'mr-new',
      name: 'Mr. New',
      room: '101',
      status: 'normal',
      top_pattern: null,
      scores: [],
      sessions: [],
      care_records: [],
      baseline: { mean: 0, std: 0, threshold: 0 },
    }
    const fetchMock = vi.fn().mockImplementation(async (url: string) => ({
      ok: true, json: async () => url.endsWith('/drift') ? null : empty,
    }))
    vi.stubGlobal('fetch', fetchMock)

    render(<ResidentDetail residentId="mr-new" onBack={() => {}} />)

    expect(await screen.findByRole('heading', { level: 2, name: 'Mr. New' })).toBeTruthy()
    expect(screen.getAllByText('No scored sessions yet.').length).toBeGreaterThan(0)
    expect(screen.getByText('No sessions recorded yet.')).toBeTruthy()
    expect(screen.queryByRole('img', { name: /baseline chart/i })).toBeNull()
    expect(screen.queryByRole('grid', { name: /daily error scores/i })).toBeNull()
  })

  it('calls onBack when the back button is clicked', async () => {
    offline()
    const onBack = vi.fn()

    render(<ResidentDetail residentId="mrs-k" onBack={onBack} />)

    fireEvent.click(await screen.findByRole('button', { name: /unit overview/i }))
    expect(onBack).toHaveBeenCalledTimes(1)
  })
})

describe('fetchDrift', () => {
  it('fetches the API drift assessment with an encoded resident id', async () => {
    const drift = { resident_id: 'resident/1', slope_per_day: 0.4, days: 14, trending: true }
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => drift })
    vi.stubGlobal('fetch', fetchMock)

    expect(await fetchDrift('resident/1')).toEqual(drift)
    expect(fetchMock).toHaveBeenCalledWith(`${apiUrl}/residents/resident%2F1/drift`)
  })

  it('uses mock drift data on an unsuccessful API response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false }))

    expect(await fetchDrift('mr-chen')).toEqual({
      resident_id: 'mr-chen', slope_per_day: 0.7, days: 7, trending: true,
    })
    expect(await fetchDrift('nobody')).toBeNull()
  })
})

describe('resident detail navigation', () => {
  it('opens a resident from the overview and comes back', async () => {
    offline()

    render(<App />)

    fireEvent.click(await screen.findByRole('button', { name: /open mrs\. k/i }))

    expect(await screen.findByRole('heading', { level: 2, name: 'Mrs. K' })).toBeTruthy()
    expect(screen.queryByRole('heading', { level: 2, name: 'Unit overview' })).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: /unit overview/i }))

    expect(
      await screen.findByRole('heading', { level: 2, name: 'Unit overview' }),
    ).toBeTruthy()
    expect(screen.queryByRole('heading', { level: 2, name: 'Mrs. K' })).toBeNull()
  })
})

describe('mock resident detail', () => {
  it('keeps the demo resident consistent: two sessions above her own threshold', () => {
    const above = MRS_K.scores.filter((point) => point.score > MRS_K.baseline.threshold)

    expect(MRS_K.status).toBe('flagged')
    expect(above).toHaveLength(2)
    expect(above.map((point) => point.ts.slice(0, 10))).toEqual(['2026-01-01', '2026-01-01'])
    expect(MRS_K.sessions).toHaveLength(MRS_K.scores.length)
  })

  it('has no detail for an unknown resident', () => {
    expect(mockResidentDetail('nobody')).toBeNull()
  })
})

describe('resident helpers', () => {
  it('gives the heat calendar the worst score per day and null for quiet days', () => {
    expect(
      dailyScores([
        { ts: '2026-01-01T08:00:00+00:00', score: 1 },
        { ts: '2026-01-01T18:00:00+00:00', score: 4 },
        { ts: '2026-01-03T08:00:00+00:00', score: 0 },
      ]),
    ).toEqual([
      { date: '2026-01-01', score: 4 },
      { date: '2026-01-02', score: null },
      { date: '2026-01-03', score: 0 },
    ])
    expect(dailyScores([])).toEqual([])
  })

  it('formats durations and error counts in plain language', () => {
    expect(formatDuration(226)).toBe('3m 46s')
    expect(formatDuration(60)).toBe('1m 00s')
    expect(formatErrors({ omission: 1, hesitation: 2 })).toBe('skipped step ×1 · long pause ×2')
    expect(formatErrors({})).toBe('')
  })
})
