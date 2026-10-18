import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { resetMockCheckIns, startMockCheckIn } from '../mock/checkins.ts'
import { personNote, personStatus } from '../person/personNotes.ts'
import { setPersonRoutineApi } from '../person/routine/api.ts'
import { mockPersonRoutine, mockSteadyRoutine } from '../person/routine/mockRoutine.ts'
import { acceptInvite, createInvite, currentPerson, setPeopleApi, supervisorsOf } from './api.ts'
import { MyRoutine } from './MyRoutine.tsx'

// The live session (sockets, camera, task map) is `live/`'s own territory and has
// its own tests; here it only needs to prove it was asked for, with the props
// MyRoutine.tsx wires to it.
vi.mock('../live/LiveScreen.tsx', () => ({
  LiveScreen: ({
    onOpenAlert,
    onSessionEnd,
  }: {
    onOpenAlert?: (alertId: string) => void
    onSessionEnd?: () => void
  }) => (
    <div data-testid="live-screen">
      <button type="button" onClick={() => onOpenAlert?.('alert-1')}>
        Open alert (mock)
      </button>
      <button type="button" onClick={() => onSessionEnd?.()}>
        End session (mock)
      </button>
    </div>
  ),
}))

// MyRoutine.tsx loads these behind React.lazy so a supervisor's first paint never
// carries them. Pay the dynamic-import/transform cost here, once, instead of in the
// first test's findByRole, which otherwise races the 1s default timeout.
beforeAll(async () => {
  await import('../person/routine/RoutineSections.tsx')
  await import('../checkin/CheckInCard.tsx')
})

beforeEach(() => {
  localStorage.clear()
  setPeopleApi(null)
  setPersonRoutineApi(null)
  // checkin/api.ts falls back to the mock on a failed fetch, exactly like
  // alert/api.ts; stub it so that fallback is instant instead of a real,
  // slow connection attempt to an API nothing here is running.
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')))
})

afterEach(() => {
  cleanup()
  setPersonRoutineApi(null)
  resetMockCheckIns()
  vi.unstubAllGlobals()
})

/** Links the demo's supervisor to the person using the app, the way the invite flow does. */
function linkASupervisor() {
  acceptInvite(createInvite(currentPerson().id).code)
}

/** Renders the screen and waits for the week behind it, which loads on demand so a
 * supervisor's first paint never carries it (`MyRoutine.tsx`). */
async function renderRoutine(
  props: { onChange?: () => void; onOpenAlert?: (alertId: string) => void } = {},
) {
  render(<MyRoutine {...props} />)
  await screen.findByRole('heading', { name: 'How this week looks' })
}

/** Nothing on the person's own screen may name a condition or raise an alarm
 * (SPEC section 17). "Nurse" is allowed: it is who one of the supervisors is. */
const banned = /diagnos|patient|resident|delirium|dementia|stroke|danger|warning|emergency|urgent|alarm/i

describe('MyRoutine', () => {
  it('says nobody else can see this when the person is watching themselves', async () => {
    await renderRoutine()

    expect(screen.getByRole('heading', { name: 'My routine' })).toBeTruthy()
    expect(screen.getByText(/Nobody else can see this/)).toBeTruthy()
    expect(screen.getByText('Only you can see this.')).toBeTruthy()
  })

  it('lists who can see this, and takes one off again', async () => {
    linkASupervisor()
    const onChange = vi.fn()
    await renderRoutine({ onChange })

    expect(screen.getByText('Nurse Ana')).toBeTruthy()
    expect(screen.getByText('Nurse Ana sees exactly what you see here.')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Remove Nurse Ana' }))

    expect(screen.queryByText('Nurse Ana')).toBeNull()
    expect(screen.getByText(/Nobody else can see this/)).toBeTruthy()
    expect(supervisorsOf(currentPerson().id)).toEqual([])
    expect(onChange).toHaveBeenCalled()
  })

  it('hands out a code and a link for someone to watch over them', async () => {
    await renderRoutine()

    fireEvent.click(screen.getByRole('button', { name: 'Invite someone' }))

    const { code } = createInvite(currentPerson().id)
    expect(screen.getByText(code)).toBeTruthy()
    expect(screen.getByText(/Or send them this link/).textContent).toContain(code)
  })

  it('copies the invite link, and says so when it cannot', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    await renderRoutine()
    fireEvent.click(screen.getByRole('button', { name: 'Invite someone' }))

    fireEvent.click(screen.getByRole('button', { name: 'Copy link' }))

    const { link } = createInvite(currentPerson().id)
    expect(writeText).toHaveBeenCalledWith(link)
    expect(await screen.findByText('Link copied')).toBeTruthy()

    vi.stubGlobal('navigator', { clipboard: {} })
    fireEvent.click(screen.getByRole('button', { name: 'Copy link' }))
    expect(await screen.findByText('Copy not available')).toBeTruthy()
  })

  it('tells the person nothing is shared with anyone they have not added', async () => {
    await renderRoutine()

    expect(screen.getByText(/Nothing is shared with anyone you have not added yourself/)).toBeTruthy()
  })

  it('opens on their status, their week, their sessions and their privacy', async () => {
    await renderRoutine()

    expect(screen.getByText(personStatus(mockPersonRoutine.status))).toBeTruthy()
    expect(screen.getByRole('img', { name: /Minutes your routine took each day/ })).toBeTruthy()
    expect(screen.getAllByText('Making tea').length).toBeGreaterThan(0)
    expect(screen.getByRole('heading', { name: 'Recent sessions' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Who can see this' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Your privacy' })).toBeTruthy()
  })

  it('writes the flagged change as a note to themselves, not as an alert', async () => {
    await renderRoutine()

    for (const match of mockPersonRoutine.patterns) {
      expect(screen.getByRole('heading', { name: personNote(match).title })).toBeTruthy()
    }
    expect(screen.getByText(personNote(mockPersonRoutine.patterns[0]).body)).toBeTruthy()
    // Nobody is linked yet, so there is nobody to tell.
    expect(screen.queryByRole('button', { name: /^Tell/ })).toBeNull()
    expect(screen.getByText(/Nobody else can see your routine yet/)).toBeTruthy()
  })

  it('offers to tell the person watching over them once there is one', async () => {
    linkASupervisor()
    await renderRoutine()

    const note = personNote(mockPersonRoutine.patterns[0], 'Nurse Ana')
    expect(screen.getByText(note.body)).toBeTruthy()

    // One button per note: telling them about one change doesn't tell them the rest.
    const tell = screen.getAllByRole('button', { name: 'Tell Nurse Ana' })
    expect(tell.length).toBe(mockPersonRoutine.patterns.length)
    fireEvent.click(tell[0])

    expect(screen.getByText('Shared with Nurse Ana.')).toBeTruthy()
    expect(
      screen.getByText('Nurse Ana sees this the next time they open Routinely.'),
    ).toBeTruthy()
    expect(screen.getAllByRole('button', { name: 'Tell Nurse Ana' }).length).toBe(
      mockPersonRoutine.patterns.length - 1,
    )
  })

  it('has no note at all in a week that looked like their usual', async () => {
    setPersonRoutineApi({ routineFor: () => mockSteadyRoutine })
    await renderRoutine()

    expect(screen.getByText(personStatus('normal'))).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Worth a mention' })).toBeNull()
    expect(screen.getAllByText('Like your usual').length).toBeGreaterThan(0)
  })

  it('pauses and resumes the watching from the keyboard alone', async () => {
    const user = userEvent.setup()
    await renderRoutine()

    // The mocked live session's own two buttons come first in tab order.
    await user.tab()
    await user.tab()
    await user.tab()
    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Invite someone' }))

    await user.tab()
    const pause = screen.getByRole('button', { name: 'Pause watching' })
    expect(document.activeElement).toBe(pause)

    await user.keyboard('{Enter}')
    const resume = screen.getByRole('button', { name: 'Resume watching' })
    expect(document.activeElement).toBe(resume)
    expect(resume.getAttribute('aria-pressed')).toBe('true')
    expect(
      screen.getByText('Watching is paused. Nothing is recorded until you resume.'),
    ).toBeTruthy()

    await user.keyboard('{Enter}')
    expect(screen.getByRole('button', { name: 'Pause watching' }).getAttribute('aria-pressed'))
      .toBe('false')
  })

  it('shows the check-in card when the person has an active check-in', async () => {
    startMockCheckIn({
      checkin_id: 'checkin-1',
      person_id: currentPerson().id,
      ask: 'Quick check-in: are you okay?',
      seconds_left: 60,
      safetyPin: '1954',
      duressPin: '7227',
    })
    await renderRoutine()

    expect(await screen.findByRole('heading', { name: 'Quick check-in: are you okay?' })).toBeTruthy()
  })

  it('shows no check-in card when nothing is active', async () => {
    await renderRoutine()

    expect(screen.queryByRole('heading', { name: 'Quick check-in: are you okay?' })).toBeNull()
  })

  it('shows the live session, for watching yourself only', async () => {
    await renderRoutine()

    expect(screen.getByRole('heading', { name: 'Your session' })).toBeTruthy()
    expect(
      screen.getByText("Start making tea when you're ready; only your skeleton is used."),
    ).toBeTruthy()
    expect(screen.getByTestId('live-screen')).toBeTruthy()
  })

  it('opens the alert the live session asks for', async () => {
    const onOpenAlert = vi.fn()
    await renderRoutine({ onOpenAlert })

    fireEvent.click(screen.getByRole('button', { name: 'Open alert (mock)' }))

    expect(onOpenAlert).toHaveBeenCalledWith('alert-1')
  })

  it('never names a condition or raises an alarm, linked or alone', async () => {
    await renderRoutine()
    expect(document.body.textContent ?? '').not.toMatch(banned)

    cleanup()
    linkASupervisor()
    await renderRoutine()
    expect(document.body.textContent ?? '').not.toMatch(banned)
  })
})
