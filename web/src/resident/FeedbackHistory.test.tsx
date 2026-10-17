import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiUrl } from '../config.ts'
import { mockResidentDetail } from '../mock/residentDetail.ts'
import { FeedbackHistory } from './FeedbackHistory.tsx'
import type { FeedbackState } from './FeedbackHistory.tsx'
import { ResidentDetail } from './ResidentDetail.tsx'
import { fetchFeedbackHistory } from './api.ts'
import type { FeedbackAnswer, Resident, ResidentFeedback } from './types.ts'

const SUDDEN = 'Sudden change (delirium pattern)'
const EVENING = 'Evening-only worsening (sundowning pattern)'

const NAMES = { sudden_change: SUDDEN, evening_worsening: EVENING }

function answer(partial: Partial<FeedbackAnswer> = {}): FeedbackAnswer {
  return {
    alert_id: 'alert-mrs-k',
    verdict: 'confirmed',
    cause: 'sudden_change',
    at: '2026-01-01T13:40:00+00:00',
    ...partial,
  }
}

function ok(feedback: Partial<ResidentFeedback> = {}): FeedbackState {
  return {
    status: 'ok',
    feedback: {
      resident_id: 'mrs-k',
      answers: [],
      pattern_weights: {},
      pattern_names: NAMES,
      ...feedback,
    },
  }
}

function rows(): string[] {
  return screen.getAllByRole('listitem').map((item) => item.textContent ?? '')
}

afterEach(cleanup)

describe('FeedbackHistory', () => {
  it('lists what each nurse said, what it was consistent with and when', () => {
    render(
      <FeedbackHistory
        state={ok({
          answers: [
            answer({ alert_id: 'alert-1', at: '2026-01-02T09:15:00+00:00' }),
            answer({ alert_id: 'alert-2', cause: 'evening_worsening' }),
          ],
        })}
      />,
    )

    expect(rows()).toEqual([
      `Confirmed · consistent with ${SUDDEN} · 2 Jan, 09:15`,
      `Confirmed · consistent with ${EVENING} · 1 Jan, 13:40`,
    ])
    expect(screen.getByRole('region', { name: 'What nurses said' })).toBeTruthy()
  })

  it('keeps the order the API sent, which is newest first', () => {
    render(
      <FeedbackHistory
        state={ok({
          answers: [
            answer({ alert_id: 'newest', at: '2026-01-03T08:00:00+00:00' }),
            answer({ alert_id: 'oldest', at: '2025-12-30T08:00:00+00:00' }),
          ],
        })}
      />,
    )

    expect(rows()[0]).toContain('3 Jan, 08:00')
    expect(rows()[1]).toContain('30 Dec, 08:00')
  })

  it('says "another cause" when the answer was something the library has no pattern for', () => {
    render(<FeedbackHistory state={ok({ answers: [answer({ cause: 'other' })] })} />)

    expect(rows()).toEqual(['Confirmed · another cause · 1 Jan, 13:40'])
  })

  it('shows a false alarm as the verdict and the time alone', () => {
    // A cause on a dismissed alert isn't evidence the pattern matched, and the
    // ranking doesn't count it either, so the card doesn't claim it did.
    render(
      <FeedbackHistory
        state={ok({ answers: [answer({ verdict: 'false_alarm', cause: 'sudden_change' })] })}
      />,
    )

    expect(rows()).toEqual(['False alarm · 1 Jan, 13:40'])
  })

  it('tells a confirmed answer from a dismissed one in words, not only colour', () => {
    const { container } = render(
      <FeedbackHistory
        state={ok({
          answers: [
            answer({ alert_id: 'a', verdict: 'confirmed' }),
            answer({ alert_id: 'b', verdict: 'false_alarm' }),
          ],
        })}
      />,
    )

    const verdicts = [...container.querySelectorAll('.feedback-history__verdict')]
    expect(verdicts.map((span) => span.textContent)).toEqual(['Confirmed', 'False alarm'])
    expect(verdicts[0].className).toContain('feedback-history__verdict--confirmed')
    expect(verdicts[1].className).toContain('feedback-history__verdict--false-alarm')
  })

  it('names the pattern those answers now rank first', () => {
    render(
      <FeedbackHistory
        state={ok({
          answers: [answer()],
          pattern_weights: { sudden_change: 1.1, evening_worsening: 1.2 },
        })}
      />,
    )

    expect(screen.getByText(`Ranking now favours: ${EVENING}`)).toBeTruthy()
    expect(screen.queryByText(/Ranked lower/)).toBeNull()
  })

  it('says what a false alarm pushed down the ranking', () => {
    render(
      <FeedbackHistory
        state={ok({
          answers: [answer({ verdict: 'false_alarm', cause: null })],
          pattern_weights: { sudden_change: 0.9 },
        })}
      />,
    )

    expect(screen.getByText(`Ranked lower: ${SUDDEN}`)).toBeTruthy()
    expect(screen.queryByText(/Ranking now favours/)).toBeNull()
  })

  it('says nothing about the ranking when the answers cancelled out', () => {
    render(
      <FeedbackHistory
        state={ok({ answers: [answer()], pattern_weights: { sudden_change: 1 } })}
      />,
    )

    expect(screen.queryByText(/Ranking now favours/)).toBeNull()
    expect(screen.queryByText(/Ranked lower/)).toBeNull()
  })

  it('falls back to the pattern id when the library has no name for it', () => {
    render(
      <FeedbackHistory
        state={{
          status: 'ok',
          feedback: {
            resident_id: 'mrs-k',
            answers: [answer({ cause: 'retired_pattern' })],
            pattern_weights: { retired_pattern: 1.1 },
            pattern_names: {},
          },
        }}
      />,
    )

    expect(rows()[0]).toContain('consistent with retired_pattern')
    expect(screen.getByText('Ranking now favours: retired_pattern')).toBeTruthy()
  })

  it('keeps the card short: only the five most recent answers', () => {
    render(
      <FeedbackHistory
        state={ok({
          answers: Array.from({ length: 7 }, (_, index) =>
            answer({
              alert_id: `alert-${index}`,
              at: `2026-01-01T${String(13 - index).padStart(2, '0')}:40:00+00:00`,
            }),
          ),
        })}
      />,
    )

    expect(rows()).toHaveLength(5)
    expect(rows()[4]).toContain('09:40')
  })

  it('says so when nobody has answered yet', () => {
    render(<FeedbackHistory state={ok()} />)

    expect(screen.getByText('No nurse answers yet')).toBeTruthy()
    expect(screen.queryByRole('list')).toBeNull()
  })

  it('says so when the answers could not be loaded', () => {
    render(<FeedbackHistory state={{ status: 'error' }} />)

    expect(screen.getByRole('alert').textContent).toBe("Couldn't load feedback")
    expect(screen.queryByRole('list')).toBeNull()
  })

  it('shows a loading line while the answers are on their way', () => {
    render(<FeedbackHistory state={{ status: 'loading' }} />)

    expect(screen.getByRole('status').textContent).toBe('Loading nurse answers…')
  })

  it('stays review-only wording: consistent with, never a verdict on the resident', () => {
    const { container } = render(
      <FeedbackHistory
        state={ok({ answers: [answer()], pattern_weights: { sudden_change: 1.2 } })}
      />,
    )

    expect(container.textContent).toContain('consistent with')
    expect(container.textContent?.toLowerCase()).not.toContain('diagnos')
    expect(container.textContent?.toLowerCase()).not.toContain(' has ')
  })
})

describe('fetchFeedbackHistory', () => {
  it('asks the API for this resident, with the id encoded', async () => {
    const payload: ResidentFeedback = {
      resident_id: 'resident/1',
      answers: [answer()],
      pattern_weights: { sudden_change: 1.1 },
      pattern_names: NAMES,
    }
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => payload })
    vi.stubGlobal('fetch', fetchMock)

    expect(await fetchFeedbackHistory('resident/1')).toEqual(payload)
    expect(fetchMock).toHaveBeenCalledWith(`${apiUrl}/residents/resident%2F1/feedback`)

    vi.unstubAllGlobals()
  })

  it('reads a body without the fields as nothing answered yet', async () => {
    // Keeps the card empty rather than broken when something else answers the call.
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) }))

    expect(await fetchFeedbackHistory('mrs-k')).toEqual({
      resident_id: 'mrs-k',
      answers: [],
      pattern_weights: {},
      pattern_names: {},
    })

    vi.unstubAllGlobals()
  })

  it('throws when the API answers with an error, so the card can say so', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 404 }))

    await expect(fetchFeedbackHistory('nobody')).rejects.toThrow('404')

    vi.unstubAllGlobals()
  })
})

describe('FeedbackHistory on the resident detail', () => {
  const MRS_K = mockResidentDetail('mrs-k') as Resident

  function stubFetch(feedback: ResidentFeedback | 'error') {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (url: string) => {
        if (url.endsWith('/feedback')) {
          return feedback === 'error'
            ? { ok: false, status: 500, json: async () => ({}) }
            : { ok: true, json: async () => feedback }
        }
        if (url.endsWith('/drift')) return { ok: true, json: async () => null }
        if (url.endsWith('/monitoring/history')) {
          return { ok: true, json: async () => ({ room: '204', history: [] }) }
        }
        if (url.endsWith('/monitoring')) {
          return { ok: true, json: async () => ({ paused_rooms: [] }) }
        }
        return { ok: true, json: async () => MRS_K }
      }),
    )
  }

  afterEach(() => { vi.unstubAllGlobals() })

  it('shows the answers and the ranking they changed under the session list', async () => {
    stubFetch({
      resident_id: 'mrs-k',
      answers: [answer({ cause: 'evening_worsening' })],
      pattern_weights: { evening_worsening: 1.1 },
      pattern_names: NAMES,
    })

    const { container } = render(<ResidentDetail residentId="mrs-k" onBack={() => {}} />)

    const card = await screen.findByRole('region', { name: 'What nurses said' })
    await waitFor(() =>
      expect(card.textContent).toContain(`Confirmed · consistent with ${EVENING} · 1 Jan, 13:40`),
    )
    expect(card.textContent).toContain(`Ranking now favours: ${EVENING}`)

    const panels = [...container.querySelectorAll('.resident-panels > *')]
    const sessions = panels.findIndex((panel) => panel.querySelector('h2')?.textContent === 'Sessions')
    expect(panels.findIndex((panel) => panel.querySelector('.feedback-history'))).toBe(sessions + 1)
  })

  it('says so on the card when the feedback call fails, leaving the rest of the screen up', async () => {
    stubFetch('error')

    render(<ResidentDetail residentId="mrs-k" onBack={() => {}} />)

    expect(await screen.findByText("Couldn't load feedback")).toBeTruthy()
    expect(screen.getByRole('heading', { level: 1, name: 'Mrs. K' })).toBeTruthy()
  })
})
