import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Handoff } from './Handoff.tsx'
import { mockHandoff } from './mockHandoff.ts'
import type { Handoff as HandoffData } from './types.ts'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

function serve(handoff: HandoffData) {
  const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => handoff })
  vi.stubGlobal('fetch', fetch)
  return fetch
}

function offline() {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network down')))
}

const served: HandoffData = {
  window_hours: 12,
  residents: [
    { resident_id: 'mrs-k', name: 'Mrs. K', flags: 2, pending_review: 1, trending: false },
    { resident_id: 'mr-chen', name: 'Mr. Chen', flags: 0, pending_review: 0, trending: true },
    { resident_id: 'mrs-ahmed', name: 'Mrs. Ahmed', flags: 0, pending_review: 0, trending: false },
  ],
  summary: 'Flagged for review: 2 errors this session vs 0.58 normally over 14 days.',
}

describe('Handoff', () => {
  it('renders the list and the summary from the mock data when the API is unreachable', async () => {
    offline()

    render(<Handoff onBack={() => {}} />)

    expect(await screen.findByText(mockHandoff.summary)).toBeTruthy()
    for (const resident of mockHandoff.residents) {
      expect(screen.getByText(resident.name)).toBeTruthy()
    }
    expect(screen.getAllByRole('listitem')).toHaveLength(mockHandoff.residents.length)
    expect(screen.getByRole('alert').textContent).toContain('Offline')
  })

  it('shows what each resident did in words, not colour alone', async () => {
    serve(served)

    render(<Handoff onBack={() => {}} />)

    expect(await screen.findByText('2 changes flagged for review')).toBeTruthy()
    expect(screen.getByText('1 alert not reviewed yet')).toBeTruthy()
    expect(screen.getByText('Error score trending up')).toBeTruthy()
    expect(screen.getByText('No change flagged')).toBeTruthy()
  })

  it('leads with how many residents need a look', async () => {
    serve(served)

    render(<Handoff onBack={() => {}} />)

    const headline = await screen.findByText('2 of 3 residents to review in the last 12 hours')
    expect(headline.getAttribute('role')).toBe('status')
  })

  it('says so when nothing was flagged for review', async () => {
    serve({
      window_hours: 12,
      residents: [{ resident_id: 'mrs-k', name: 'Mrs. K', flags: 0, pending_review: 0, trending: false }],
      summary: 'No errors this session vs 0.58 normally over 14 days.',
    })

    render(<Handoff onBack={() => {}} />)

    const headline = await screen.findByText('No change flagged for review in the last 12 hours')
    expect(headline.getAttribute('role')).toBe('status')
  })

  it('shows an empty state for a unit with no residents', async () => {
    serve({ window_hours: 12, residents: [], summary: 'Nothing to report.' })

    render(<Handoff onBack={() => {}} />)

    expect(await screen.findByText('No residents on this unit yet.')).toBeTruthy()
    expect(screen.queryAllByRole('listitem')).toHaveLength(0)
  })

  it('loads before it has anything to show', async () => {
    serve(served)

    render(<Handoff onBack={() => {}} />)

    expect(screen.getByRole('status').textContent).toBe('Loading handoff…')
    await screen.findByText(served.summary)
  })

  it('refetches when the nurse picks another window', async () => {
    const twelve: HandoffData = { ...served, window_hours: 12 }
    const day: HandoffData = {
      ...served,
      window_hours: 24,
      summary: 'Flagged for review: a longer window.',
    }
    const fetch = vi.fn().mockImplementation((url: string) => Promise.resolve({
      ok: true,
      json: async () => (url.includes('hours=24') ? day : twelve),
    }))
    vi.stubGlobal('fetch', fetch)

    render(<Handoff onBack={() => {}} />)
    await screen.findByText(twelve.summary)

    fireEvent.change(screen.getByLabelText('Window'), { target: { value: '24' } })

    expect(await screen.findByText(day.summary)).toBeTruthy()
    expect(await screen.findByRole('heading', { name: 'Last 24 hours' })).toBeTruthy()
    expect(fetch.mock.calls.map(([url]) => url as string).some(url => url.includes('hours=24'))).toBe(true)
  })

  it('goes back when asked', async () => {
    serve(served)
    const onBack = vi.fn()

    render(<Handoff onBack={onBack} />)
    await screen.findByText(served.summary)

    fireEvent.click(screen.getByRole('button', { name: /Back/ }))

    expect(onBack).toHaveBeenCalledOnce()
  })

  it('keeps review wording and theme tokens, offline and online', async () => {
    offline()

    const { container } = render(<Handoff onBack={() => {}} />)
    await screen.findByText(mockHandoff.summary)

    expect(container.textContent).not.toMatch(/diagnos/i)
    expect(container.textContent).toMatch(/flagged for review/i)
    for (const element of container.querySelectorAll('[style]')) {
      expect(element.getAttribute('style')).not.toMatch(/#[\da-f]{3,8}\b|hsl\(/i)
    }
  })
})
