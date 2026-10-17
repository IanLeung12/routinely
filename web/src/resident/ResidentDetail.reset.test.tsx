import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { mockResidentDetail } from '../mock/residentDetail.ts'
import { ResidentDetail } from './ResidentDetail.tsx'
import type { FeedbackAnswer, Resident, ResidentFeedback } from './types.ts'

/** T312: the dashboard side of T304 (`pipeline/tests/test_feedback_reset.py`) - a demo
 * reset drops `/residents/{id}/feedback` back to nothing answered, so the resident
 * detail's "What nurses said" card has to drop the stale answer with it rather than
 * keep showing what the first run's nurse said. */

const MRS_K = mockResidentDetail('mrs-k') as Resident

const ANSWER: FeedbackAnswer = {
  alert_id: 'alert-mrs-k',
  verdict: 'confirmed',
  cause: 'sudden_change',
  at: '2026-01-01T13:40:00+00:00',
}

const ANSWERED: ResidentFeedback = {
  resident_id: 'mrs-k',
  answers: [ANSWER],
  pattern_weights: { sudden_change: 1.1 },
  pattern_names: { sudden_change: 'Sudden change (delirium pattern)' },
}

const RESET: ResidentFeedback = {
  resident_id: 'mrs-k',
  answers: [],
  pattern_weights: {},
  pattern_names: {},
}

function stubFetch(feedback: ResidentFeedback) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation(async (url: string) => {
      if (url.endsWith('/feedback')) return { ok: true, json: async () => feedback }
      if (url.endsWith('/drift')) return { ok: true, json: async () => null }
      if (url.endsWith('/monitoring/history')) {
        return { ok: true, json: async () => ({ room: '204', history: [] }) }
      }
      if (url.endsWith('/monitoring')) return { ok: true, json: async () => ({ paused_rooms: [] }) }
      return { ok: true, json: async () => MRS_K }
    }),
  )
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('ResidentDetail feedback after a demo reset (T312)', () => {
  it('shows the empty state once the feedback card re-fetches a cleared record', async () => {
    stubFetch(ANSWERED)
    const { unmount } = render(<ResidentDetail residentId="mrs-k" onBack={() => {}} />)

    const card = await screen.findByRole('region', { name: 'What nurses said' })
    await waitFor(() =>
      expect(card.textContent).toContain('Confirmed · consistent with Sudden change (delirium pattern) · 1 Jan, 13:40'),
    )

    // A demo reset happens server-side; the nurse sees it once the screen re-fetches -
    // here, by reopening the resident the way navigating back to it would.
    unmount()
    stubFetch(RESET)
    render(<ResidentDetail residentId="mrs-k" onBack={() => {}} />)

    const reopened = await screen.findByRole('region', { name: 'What nurses said' })
    await waitFor(() => expect(reopened.textContent).toContain('No nurse answers yet'))
    expect(reopened.textContent).not.toContain('Confirmed')
  })
})
