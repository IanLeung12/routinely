import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { setCheckInApi } from './api.ts'
import { CheckInCard } from './CheckInCard.tsx'
import type { CheckIn } from './types.ts'

const SAFETY_PIN = '1954'
const DURESS_PIN = '7227'
const PERSON_ID = 'sam'

/** Same `accepted` whichever PIN matched (SPEC section 12): the fake never tells
 * the component which one it was, exactly like T450's real `/respond` will. */
function fakeApi(checkIn: CheckIn | null) {
  return {
    activeCheckIn: vi.fn().mockResolvedValue(checkIn),
    respond: vi.fn(async (_checkInId: string, pin: string) => ({
      accepted: pin === SAFETY_PIN || pin === DURESS_PIN,
    })),
  }
}

function buildCheckIn(overrides: Partial<CheckIn> = {}): CheckIn {
  return {
    id: 'checkin-1',
    person_id: PERSON_ID,
    status: 'pending',
    deadline: new Date(Date.now() + 120_000).toISOString(),
    ...overrides,
  }
}

function enterPin(pin: string) {
  for (const digit of pin) {
    fireEvent.click(screen.getByRole('button', { name: digit }))
  }
}

afterEach(() => {
  cleanup()
  setCheckInApi(null)
  vi.useRealTimers()
})

describe('CheckInCard', () => {
  it('renders nothing when the person has no active check-in', async () => {
    setCheckInApi(fakeApi(null))
    const { container } = render(<CheckInCard personId={PERSON_ID} />)

    await act(async () => {
      await Promise.resolve()
    })
    expect(container.innerHTML).toBe('')
  })

  it('shows for an active check-in and moves focus to the card', async () => {
    setCheckInApi(fakeApi(buildCheckIn()))
    render(<CheckInCard personId={PERSON_ID} />)

    const panel = await screen.findByRole('region', { name: 'Check-in' })
    expect(screen.getByRole('heading', { name: 'Quick check-in: are you okay?' })).toBeTruthy()
    expect(screen.getByRole('button', { name: "I'm okay" })).toBeTruthy()
    expect(document.activeElement).toBe(panel)
  })

  it('counts down and keeps counting while the PIN pad is open', async () => {
    setCheckInApi(fakeApi(buildCheckIn({ deadline: new Date(Date.now() + 90_000).toISOString() })))
    vi.useFakeTimers()
    render(<CheckInCard personId={PERSON_ID} />)

    await act(async () => {
      await Promise.resolve()
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
    setCheckInApi(fakeApi(buildCheckIn()))
    render(<CheckInCard personId={PERSON_ID} />)
    fireEvent.click(await screen.findByRole('button', { name: "I'm okay" }))

    enterPin('0000')

    expect(await screen.findByText('Try again')).toBeTruthy()
    expect(screen.getByRole('alert').textContent).toBe('Try again')
    expect(screen.getByRole('heading', { name: 'Quick check-in: are you okay?' })).toBeTruthy()
    expect(screen.queryByRole('heading', { name: "Thanks, you're checked in" })).toBeNull()
  })

  it('renders the same DOM for the safety PIN and the duress PIN', async () => {
    setCheckInApi(fakeApi(buildCheckIn({ id: 'checkin-safety' })))
    const safety = render(<CheckInCard personId={PERSON_ID} />)
    fireEvent.click(await screen.findByRole('button', { name: "I'm okay" }))
    enterPin(SAFETY_PIN)
    await screen.findByRole('heading', { name: "Thanks, you're checked in" })
    const safetyHtml = safety.container.innerHTML
    safety.unmount()

    setCheckInApi(fakeApi(buildCheckIn({ id: 'checkin-duress' })))
    const duress = render(<CheckInCard personId={PERSON_ID} />)
    fireEvent.click(await screen.findByRole('button', { name: "I'm okay" }))
    enterPin(DURESS_PIN)
    await screen.findByRole('heading', { name: "Thanks, you're checked in" })

    expect(duress.container.innerHTML).toBe(safetyHtml)
  })
})
