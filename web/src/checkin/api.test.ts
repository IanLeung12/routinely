import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiUrl } from '../config.ts'
import { resetMockCheckIns, startMockCheckIn } from '../mock/checkins.ts'
import { fetchMyCheckin } from './api.ts'
import type { CheckInStatus, PersonCheckIn } from './types.ts'

const PERSON = 'sam'
const ASK = 'Can you check in?'

/** One entry of what `GET /checkins/active?person=` answers with (`person_view`). */
function personView(
  checkin_id: string,
  state: CheckInStatus,
  seconds_left: number | null,
): PersonCheckIn {
  return { checkin_id, person_id: PERSON, state, ask: ASK, seconds_left }
}

function answers(checkins: PersonCheckIn[]) {
  const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ checkins }) })
  vi.stubGlobal('fetch', fetch)
  return fetch
}

afterEach(() => {
  vi.unstubAllGlobals()
  resetMockCheckIns()
})

describe("the person's own check-in", () => {
  it('asks as the person alone, the one audience the route allows', async () => {
    const fetch = answers([personView('checkin-1', 'pending', 20)])

    expect((await fetchMyCheckin(PERSON))?.checkin_id).toBe('checkin-1')
    expect(fetch).toHaveBeenCalledWith(`${apiUrl}/checkins/active?person=sam`, undefined)
  })

  it('shows the live question, not an alarm that already went out (T460)', async () => {
    // What the repro leaves behind: a check-in that ran out of time and is stuck at
    // 0:00 on the person's list, and the question they are being asked now.
    answers([personView('checkin-old', 'alarm', null), personView('checkin-new', 'pending', 20)])

    const shown = await fetchMyCheckin(PERSON)

    expect(shown?.checkin_id).toBe('checkin-new')
    expect(shown?.seconds_left).toBe(20)
  })

  it('falls back to the newest of what is left when there is no question', async () => {
    answers([personView('checkin-old', 'alarm', null), personView('checkin-newer', 'escalated', 9)])

    expect((await fetchMyCheckin(PERSON))?.checkin_id).toBe('checkin-newer')
  })

  it('is nothing at all when the person has no open check-in', async () => {
    answers([])

    expect(await fetchMyCheckin(PERSON)).toBeNull()
  })

  it('uses the offline mock when the connection fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    startMockCheckIn({
      checkin_id: 'checkin-mock',
      person_id: PERSON,
      ask: ASK,
      seconds_left: 120,
      safetyPin: '1234',
      duressPin: '9111',
    })

    expect((await fetchMyCheckin(PERSON))?.checkin_id).toBe('checkin-mock')
  })

  it('surfaces an error from a service that answered, rather than showing the mock', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }))

    await expect(fetchMyCheckin(PERSON)).rejects.toThrow('500')
  })
})
