import { act, cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { LiveScreen } from './LiveScreen.tsx'
import type { LiveMessage } from './useLiveSession.ts'

/** The panel also loads the resident's baseline for the session summary's "usually"
 * line (`LiveSession.tsx`); stub it so the test never makes a real network call. */
vi.mock('../resident/api.ts', () => ({
  fetchResident: vi.fn().mockResolvedValue(null),
}))

/** Stands in for the real WebSocket, same as `LiveSession.test.tsx`: failing it drives
 * the live session into `mockLiveStream` without a server to talk to. */
class FakeWebSocket {
  static instances: FakeWebSocket[] = []
  url: string
  closed = false
  onmessage: ((event: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  onclose: (() => void) | null = null

  constructor(url: string) {
    this.url = url
    FakeWebSocket.instances.push(this)
  }

  close() {
    this.closed = true
  }

  emit(message: LiveMessage) {
    this.onmessage?.({ data: JSON.stringify(message) })
  }

  fail() {
    this.onerror?.()
    this.onclose?.()
  }

  static latest(): FakeWebSocket {
    const instance = FakeWebSocket.instances[FakeWebSocket.instances.length - 1]
    if (!instance) {
      throw new Error('no FakeWebSocket instance was created')
    }
    return instance
  }
}

const originalUrl = window.location.href

/** Tabs forward from wherever focus currently is until `target` is reached, so the
 * test doesn't hard-code how many stops apart two controls are. */
async function tabTo(user: ReturnType<typeof userEvent.setup>, target: HTMLElement) {
  for (let i = 0; i < 20 && document.activeElement !== target; i++) {
    await user.tab()
  }
  expect(document.activeElement).toBe(target)
}

beforeEach(() => {
  FakeWebSocket.instances = []
  vi.stubGlobal('WebSocket', FakeWebSocket)
  // `shouldAdvanceTime` lets the fake clock tick on its own while `user-event` awaits
  // between keystrokes; without it `user.tab()`/`user.keyboard()` never resolve.
  vi.useFakeTimers({ shouldAdvanceTime: true })
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.useRealTimers()
  window.history.replaceState(null, '', originalUrl)
})

describe('LiveScreen keyboard-only', () => {
  it('lets a nurse pick a routine, run the session and open its flagged alert with Tab/Enter only', async () => {
    const user = userEvent.setup({ delay: null })
    const onOpenAlert = vi.fn()
    render(<LiveScreen onOpenAlert={onOpenAlert} />)

    const teaButton = screen.getByRole('button', { name: 'Making tea' })
    const medsButton = screen.getByRole('button', { name: 'Medication with water' })

    await user.tab()
    expect(document.activeElement).toBe(teaButton)

    await user.tab()
    expect(document.activeElement).toBe(medsButton)

    await user.keyboard('{Enter}')
    expect(medsButton.getAttribute('aria-pressed')).toBe('true')
    expect(teaButton.getAttribute('aria-pressed')).toBe('false')

    // Picking the routine mounts a fresh live session with its own socket; fail it over
    // to the mock stream the way a dropped connection would, so the rest of the script
    // plays without a real server.
    act(() => {
      FakeWebSocket.latest().fail()
    })
    act(() => {
      vi.advanceTimersByTime(10_000)
    })

    const taskMap = screen.getByRole('list', { name: 'Task steps' })
    expect(within(taskMap).getAllByRole('listitem').length).toBeGreaterThan(0)
    expect(screen.getByText('Session summary')).toBeTruthy()
    expect(screen.getByRole('status').textContent).toContain('Flagged for review')

    const openAlertButton = screen.getByRole('button', { name: 'Open alert' })
    await tabTo(user, openAlertButton)

    await user.keyboard('{Enter}')
    expect(onOpenAlert).toHaveBeenCalledWith('mock-alert-1')
  })

  it('reaches the routine picker and task map controls with accessible names, keyboard-only', async () => {
    const user = userEvent.setup({ delay: null })
    render(<LiveScreen onOpenAlert={vi.fn()} />)

    expect(screen.getByRole('group', { name: 'Routine to watch' })).toBeTruthy()

    const medsButton = screen.getByRole('button', { name: 'Medication with water' })
    await tabTo(user, medsButton)
    await user.keyboard('{Enter}')

    act(() => {
      FakeWebSocket.latest().fail()
    })
    act(() => {
      vi.advanceTimersByTime(10_000)
    })

    expect(screen.getByRole('list', { name: 'Task steps' })).toBeTruthy()
    expect(screen.getByRole('list', { name: 'Task map legend' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Open alert' })).toBeTruthy()
  })
})
