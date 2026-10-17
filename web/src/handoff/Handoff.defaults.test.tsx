import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Handoff } from './Handoff.tsx'
import type { Handoff as HandoffData } from './types.ts'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

/** T292 made `Handoff.paused` and `HandoffResident.monitoring_paused` optional with
 * defaults on the pipeline side (T311); this is the same payload an older or
 * trimmed `/handoff` response would send - both fields simply absent, not `[]`/
 * `false` - and the screen has to render it without crashing. */
const payloadWithoutDefaults = {
  window_hours: 12,
  residents: [
    { resident_id: 'mrs-k', name: 'Mrs. K', room: '204', flags: 0, pending_review: 0, trending: false },
  ],
  summary: 'Nothing to review.',
} as HandoffData

function serve(handoff: HandoffData) {
  const fetch = vi.fn().mockImplementation((url: string) => {
    if (url.includes('/handoff')) {
      return Promise.resolve({ ok: true, json: async () => handoff })
    }
    // /alerts, /residents/{id}, /rooms/{room}/monitoring/history: nothing to offer.
    return Promise.resolve({ ok: false })
  })
  vi.stubGlobal('fetch', fetch)
  return fetch
}

describe('Handoff with a payload missing paused/monitoring_paused', () => {
  it('renders the resident row with no crash', async () => {
    serve(payloadWithoutDefaults)

    render(<Handoff onBack={() => {}} />)

    expect(await screen.findByText('Mrs. K')).toBeTruthy()
    expect(screen.getByText('Room 204')).toBeTruthy()
  })

  it('shows no paused-rooms line', async () => {
    serve(payloadWithoutDefaults)

    render(<Handoff onBack={() => {}} />)

    await screen.findByText('Mrs. K')
    expect(screen.queryByText(/monitoring paused/i)).toBeNull()
  })

  it('puts no "paused" label on the resident row', async () => {
    serve(payloadWithoutDefaults)

    render(<Handoff onBack={() => {}} />)

    const row = (await screen.findByText('Mrs. K')).closest('li')
    expect(row?.textContent).not.toMatch(/paused/i)
    expect(row?.textContent).toContain('No change flagged')
  })
})
