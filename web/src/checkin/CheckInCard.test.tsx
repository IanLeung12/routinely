import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { resetMockCheckIns, startMockCheckIn } from '../mock/checkins.ts'
import { CheckInCard } from './CheckInCard.tsx'

const SAFETY_PIN = '1954'
const DURESS_PIN = '7227'
const PERSON_ID = 'sam'
const ASK = 'Quick check-in: are you okay?'

/** Seeds one active check-in in the offline mock, the way T450's `/checkins/demo`
 * starts one for real. Same `accepted` whichever PIN matches (SPEC section 12). */
function seed(overrides: Partial<Parameters<typeof startMockCheckIn>[0]> = {}) {
  return startMockCheckIn({
    checkin_id: 'checkin-1',
    person_id: PERSON_ID,
    ask: ASK,
    seconds_left: 120,
    safetyPin: SAFETY_PIN,
    duressPin: DURESS_PIN,
    ...overrides,
  })
}

function enterPin(pin: string) {
  for (const digit of pin) {
    fireEvent.click(screen.getByRole('button', { name: digit }))
  }
}

beforeEach(() => {
  // checkin/api.ts falls back to the offline mock on a failed fetch; stub fetch
  // so that fallback is instant instead of a real connection attempt.
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')))
})

afterEach(() => {
  cleanup()
  resetMockCheckIns()
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

describe('CheckInCard', () => {
  it('renders nothing when the person has no active check-in', async () => {
    const { container } = render(<CheckInCard personId={PERSON_ID} />)

    await act(async () => {
      await Promise.resolve()
    })
    expect(container.innerHTML).toBe('')
  })

  it('shows for an active check-in and moves focus to the card', async () => {
    seed()
    render(<CheckInCard personId={PERSON_ID} />)

    const panel = await screen.findByRole('region', { name: 'Check-in' })
    expect(screen.getByRole('heading', { name: ASK })).toBeTruthy()
    expect(screen.getByRole('button', { name: "I'm okay" })).toBeTruthy()
    expect(document.activeElement).toBe(panel)
  })

  it('counts down and keeps counting while the PIN pad is open', async () => {
    seed({ seconds_left: 90 })
    vi.useFakeTimers()
    render(<CheckInCard personId={PERSON_ID} />)

    await act(async () => {
      await Promise.resolve()
    })
    expect(screen.getByText('1:30')).toBeTruthy()

    act(() => vi.advanceTimersByTime(30_000))
    expect(screen.getByText('1:00')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: "I'm okay" }))
    act(() => vi.advanceTimersByTime(30_000))
    expect(screen.getByText('0:30')).toBeTruthy()
  })

  it('says try again on a wrong PIN and leaves the check-in pending', async () => {
    seed()
    render(<CheckInCard personId={PERSON_ID} />)
    fireEvent.click(await screen.findByRole('button', { name: "I'm okay" }))

    enterPin('0000')

    expect(await screen.findByText('Try again')).toBeTruthy()
    expect(screen.getByRole('alert').textContent).toBe('Try again')
    expect(screen.getByRole('heading', { name: ASK })).toBeTruthy()
    expect(screen.queryByRole('heading', { name: "Thanks, you're checked in" })).toBeNull()
  })

  it('renders nothing (no unhandled rejection) when the active-check-in fetch 404s', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: 'UnknownPerson' }), { status: 404 })),
    )

    const { container } = render(<CheckInCard personId={PERSON_ID} />)
    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(container.innerHTML).toBe('')
  })

  it('shows a calm message instead of the PIN pad when the check-in already escalated (409)', async () => {
    seed()
    render(<CheckInCard personId={PERSON_ID} />)
    fireEvent.click(await screen.findByRole('button', { name: "I'm okay" }))
    await screen.findByRole('button', { name: SAFETY_PIN[0] })

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: 'NotWaiting' }), { status: 409 })),
    )

    enterPin(SAFETY_PIN)

    await screen.findByText("This check-in has already gone to your supporters")
    expect(screen.getByText("They'll be in touch.")).toBeTruthy()
    expect(screen.queryByRole('button', { name: SAFETY_PIN[0] })).toBeNull()
  })

  it('renders the same DOM for the safety PIN and the duress PIN', async () => {
    seed({ checkin_id: 'checkin-safety' })
    const safety = render(<CheckInCard personId={PERSON_ID} />)
    fireEvent.click(await screen.findByRole('button', { name: "I'm okay" }))
    enterPin(SAFETY_PIN)
    await screen.findByRole('heading', { name: "Thanks, you're checked in" })
    const safetyHtml = safety.container.innerHTML
    safety.unmount()
    resetMockCheckIns()

    seed({ checkin_id: 'checkin-duress' })
    const duress = render(<CheckInCard personId={PERSON_ID} />)
    fireEvent.click(await screen.findByRole('button', { name: "I'm okay" }))
    enterPin(DURESS_PIN)
    await screen.findByRole('heading', { name: "Thanks, you're checked in" })

    expect(duress.container.innerHTML).toBe(safetyHtml)
  })
})
