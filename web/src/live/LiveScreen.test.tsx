import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LiveScreen } from './LiveScreen.tsx'
import type { LiveSessionProps } from './LiveSession.tsx'

/** The real session opens a WebSocket and plays a scenario; none of that is under test
 * here. The stub only reports the scenario it was handed and lets a test fire the two
 * callbacks the screen has to forward. */
vi.mock('./LiveSession.tsx', () => ({
  LiveSession: ({ scenario, onOpenAlert, onSessionEnd }: LiveSessionProps) => (
    <div data-testid="live-session" data-scenario={scenario}>
      <button type="button" onClick={() => onOpenAlert?.('alert-1')}>
        stub open alert
      </button>
      <button
        type="button"
        onClick={() => onSessionEnd?.({ score: 3, flag: true, alert_id: 'alert-1' })}
      >
        stub end session
      </button>
    </div>
  ),
}))

function scenarioOf(): string | null {
  return screen.getByTestId('live-session').getAttribute('data-scenario')
}

function pressed(name: string): string | null {
  return screen.getByRole('button', { name }).getAttribute('aria-pressed')
}

afterEach(cleanup)

describe('LiveScreen', () => {
  it('plays the tea scenario by default, with tea marked as the active option', () => {
    render(<LiveScreen />)

    expect(scenarioOf()).toBe('tea_skip_teabag_pour_twice')
    expect(pressed('Making tea')).toBe('true')
    expect(pressed('Medication with water')).toBe('false')
  })

  it('switches to the medication scenario when that option is clicked', () => {
    render(<LiveScreen />)
    fireEvent.click(screen.getByRole('button', { name: 'Medication with water' }))

    expect(scenarioOf()).toBe('meds_skip_water')
    expect(pressed('Medication with water')).toBe('true')
    expect(pressed('Making tea')).toBe('false')
  })

  it('switches back to tea', () => {
    render(<LiveScreen />)
    fireEvent.click(screen.getByRole('button', { name: 'Medication with water' }))
    fireEvent.click(screen.getByRole('button', { name: 'Making tea' }))

    expect(scenarioOf()).toBe('tea_skip_teabag_pour_twice')
    expect(pressed('Making tea')).toBe('true')
  })

  it('restarts the session on a switch instead of reusing the running one', () => {
    render(<LiveScreen />)
    const before = screen.getByTestId('live-session')

    fireEvent.click(screen.getByRole('button', { name: 'Medication with water' }))

    // A `key` on the session means React throws the old one away; without it the same
    // node would survive with the running session's task map and end-of-session state.
    expect(screen.getByTestId('live-session')).not.toBe(before)
    expect(before.isConnected).toBe(false)
  })

  it('forwards the session callbacks the dashboard needs', () => {
    const onOpenAlert = vi.fn()
    const onSessionEnd = vi.fn()
    render(<LiveScreen onOpenAlert={onOpenAlert} onSessionEnd={onSessionEnd} />)

    fireEvent.click(screen.getByRole('button', { name: 'stub open alert' }))
    fireEvent.click(screen.getByRole('button', { name: 'stub end session' }))

    expect(onOpenAlert).toHaveBeenCalledWith('alert-1')
    expect(onSessionEnd).toHaveBeenCalledWith({ score: 3, flag: true, alert_id: 'alert-1' })
  })

  it('labels the picker as a group', () => {
    render(<LiveScreen />)

    expect(screen.getByRole('group', { name: 'Routine to watch' })).toBeTruthy()
  })
})
