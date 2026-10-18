import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AlarmBanner } from './AlarmBanner.tsx'
import * as api from './api.ts'
import { createAlarmSound } from './alarmSound.ts'
import type { CheckIn } from './types.ts'

vi.mock('./api.ts', () => ({
  fetchActiveCheckins: vi.fn(),
  acknowledgeCheckin: vi.fn(),
  resolveCheckin: vi.fn(),
}))

const people = [{ id: 'mrs-k', name: 'Mrs. K' }]
const alarm: CheckIn = {
  id: 'check-1', person_id: 'mrs-k', status: 'alarm',
  created_at: new Date(Date.now() - 120000).toISOString(), deadline: new Date().toISOString(),
  events: [{ event: 'alarm', at: '2026-10-17T12:02:00Z' }],
}

function installAudio(blocked = false) {
  const oscillators: { start: ReturnType<typeof vi.fn>; stop: ReturnType<typeof vi.fn>; disconnect: ReturnType<typeof vi.fn> }[] = []
  const close = vi.fn().mockResolvedValue(undefined)
  class FakeAudioContext {
    state = blocked ? 'suspended' : 'running'
    currentTime = 0
    destination = {}
    close = close
    resume = vi.fn(() => blocked ? Promise.reject(new Error('Autoplay blocked')) : Promise.resolve())
    createOscillator() {
      const oscillator = { frequency: { value: 0 }, connect: vi.fn(), disconnect: vi.fn(), start: vi.fn(), stop: vi.fn(), onended: null }
      oscillators.push(oscillator)
      return oscillator
    }
    createGain() {
      return { gain: { setValueAtTime: vi.fn(), linearRampToValueAtTime: vi.fn() }, connect: vi.fn(), disconnect: vi.fn() }
    }
  }
  vi.stubGlobal('AudioContext', FakeAudioContext)
  return { oscillators, close }
}

beforeEach(() => {
  vi.mocked(api.fetchActiveCheckins).mockResolvedValue([alarm])
  vi.mocked(api.acknowledgeCheckin).mockResolvedValue({ ...alarm, status: 'acknowledged' })
  vi.mocked(api.resolveCheckin).mockResolvedValue({ ...alarm, status: 'resolved', events: [...alarm.events, { event: 'resolved', at: '2026-10-17T12:03:00Z', actor: 'ana', reason: 'helped' }] })
  vi.stubGlobal('AudioContext', undefined)
})
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.clearAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers() })

describe('supervisor alarm', () => {
  it('shows the alarm, sends the chosen resolution, and clears the alarm while preserving its timeline', async () => {
    render(<AlarmBanner people={people} supporter="ana" />)
    expect(await screen.findByRole('heading', { name: "Mrs. K hasn't checked in (2 min)" })).toBeTruthy()
    expect(api.fetchActiveCheckins).toHaveBeenCalledWith('mrs-k', 'ana')
    expect(screen.queryByText(/location/i)).toBeNull()
    fireEvent.change(screen.getByLabelText('Resolution reason'), { target: { value: 'false_alarm' } })
    fireEvent.click(screen.getByRole('button', { name: 'Resolve' }))
    expect(await screen.findByText('Mrs. K: check-in resolved')).toBeTruthy()
    expect(screen.queryByRole('alert')).toBeNull()
    expect(screen.getByText('Resolved by ana: helped')).toBeTruthy()
    expect(api.resolveCheckin).toHaveBeenCalledWith('check-1', 'ana', 'false_alarm')
  })

  it('shows duress as a silent help request and displays location only when supplied', async () => {
    vi.mocked(api.fetchActiveCheckins).mockResolvedValue([{ ...alarm, duress: true, location: 'Simulated room 2' }])
    render(<AlarmBanner people={people} supporter="ana" />)
    expect(await screen.findByText('Mrs. K: silent help request')).toBeTruthy()
    expect(screen.getByText('Shared location: Simulated room 2')).toBeTruthy()
  })

  it('does not show pending or safe check-ins as alarms', async () => {
    vi.mocked(api.fetchActiveCheckins).mockResolvedValue([{ ...alarm, status: 'pending' }, { ...alarm, id: 'safe', status: 'ok' }])
    render(<AlarmBanner people={people} supporter="ana" />)
    await waitFor(() => expect(screen.queryByText('Loading safety alarms…')).toBeNull())
    expect(screen.queryByRole('alert')).toBeNull()
    expect(screen.queryByRole('button')).toBeNull()
  })

  it('acknowledges without dismissing and stops the sound', async () => {
    const audio = installAudio()
    render(<AlarmBanner people={people} supporter="ana" />)
    fireEvent.click(await screen.findByRole('button', { name: "I'm on it" }))
    expect(await screen.findByText(/Acknowledged — someone is on it/)).toBeTruthy()
    expect(screen.getByRole('alert')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Resolve' })).toBeTruthy()
    expect(api.acknowledgeCheckin).toHaveBeenCalledWith('check-1', 'ana')
    await waitFor(() => expect(audio.close).toHaveBeenCalled())
  })

  it('keeps the alarm after a failed response', async () => {
    vi.mocked(api.resolveCheckin).mockRejectedValueOnce(new Error('offline'))
    render(<AlarmBanner people={people} supporter="ana" />)
    fireEvent.click(await screen.findByRole('button', { name: 'Resolve' }))
    expect(await screen.findByText(/Your response was not saved/)).toBeTruthy()
    expect(screen.getByRole('alert')).toBeTruthy()
  })

  it('offers Enable sound when autoplay is blocked, and starts on a user gesture', async () => {
    installAudio(true)
    render(<AlarmBanner people={people} supporter="ana" />)
    expect(await screen.findByRole('button', { name: 'Enable sound' })).toBeTruthy()
    await waitFor(() => expect(screen.getByText(/Sound needs your permission/)).toBeTruthy())
    const audio = installAudio()
    fireEvent.click(screen.getByRole('button', { name: 'Enable sound' }))
    await waitFor(() => expect(audio.oscillators.length).toBe(1))
    fireEvent.click(screen.getByRole('button', { name: 'Mute alarm' }))
    await waitFor(() => expect(audio.close).toHaveBeenCalled())
    expect(screen.getByRole('alert')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Unmute alarm' }))
    await waitFor(() => expect(audio.oscillators.length).toBe(2))
  })

  it('polls for escalation and retains an existing alarm if refreshing fails', async () => {
    vi.useFakeTimers()
    await act(async () => { render(<AlarmBanner people={people} supporter="ana" />) })
    vi.mocked(api.fetchActiveCheckins).mockResolvedValueOnce([{ ...alarm, status: 'escalated' }])
    await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
    expect(screen.getByText('Alarm escalated. Is everyone okay?')).toBeTruthy()
    vi.mocked(api.fetchActiveCheckins).mockRejectedValueOnce(new Error('offline'))
    await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
    expect(screen.getByText(/Safety alarms could not refresh/)).toBeTruthy()
    expect(screen.getByRole('alert')).toBeTruthy()
  })

  it('keeps the banner across screen rerenders and stops audio on unmount', async () => {
    const audio = installAudio()
    const view = render(<AlarmBanner people={people} supporter="ana" />)
    await screen.findByRole('alert')
    await waitFor(() => expect(audio.oscillators.length).toBe(1))
    view.rerender(<AlarmBanner people={[...people]} supporter="ana" />)
    expect(screen.getByRole('alert')).toBeTruthy()
    view.unmount()
    expect(audio.close).toHaveBeenCalled()
  })

  it('immediately removes alarms for people no longer supported even when the service is offline', async () => {
    const audio = installAudio()
    const view = render(<AlarmBanner people={people} supporter="ana" />)
    await screen.findByRole('alert')
    await waitFor(() => expect(audio.oscillators.length).toBe(1))
    vi.mocked(api.fetchActiveCheckins).mockRejectedValue(new Error('offline'))
    view.rerender(<AlarmBanner people={[]} supporter="ana" />)
    expect(screen.queryByRole('alert')).toBeNull()
    await waitFor(() => expect(audio.close).toHaveBeenCalled())
  })

  it('does not reopen a resolved alarm when a subsequent poll returns a stale alarm', async () => {
    vi.useFakeTimers()
    await act(async () => { render(<AlarmBanner people={people} supporter="ana" />) })
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Resolve' })) })
    expect(screen.queryByRole('alert')).toBeNull()
    await act(async () => { await vi.advanceTimersByTimeAsync(2000) })
    expect(screen.queryByRole('alert')).toBeNull()
    expect(screen.getByText('Mrs. K: check-in resolved')).toBeTruthy()
  })
})

describe('Web Audio tone', () => {
  it('repeats pulses and stops all oscillators and timers', async () => {
    vi.useFakeTimers()
    const audio = installAudio()
    const sound = createAlarmSound()
    expect(await sound.start()).toBe(true)
    await vi.advanceTimersByTimeAsync(3000)
    expect(audio.oscillators.length).toBe(3)
    sound.stop()
    expect(audio.oscillators.every(oscillator => oscillator.stop.mock.calls.length === 2)).toBe(true)
    expect(audio.close).toHaveBeenCalledOnce()
    await vi.advanceTimersByTimeAsync(3000)
    expect(audio.oscillators.length).toBe(3)
  })

  it('cannot start a late tone after stopped while the browser is resuming', async () => {
    const audio = installAudio()
    const sound = createAlarmSound()
    const starting = sound.start()
    sound.stop()
    expect(await starting).toBe(false)
    expect(audio.oscillators).toHaveLength(0)
  })
})

describe('shared check-in API boundary', () => {
  it('uses the offline scenario for fetch, acknowledge and resolve and never returns write-only PINs', async () => {
    const actual = await vi.importActual<typeof api>('./api.ts')
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')))
    actual.setMockCheckins([{ ...alarm, location: 'Private room' }])
    await actual.saveSafetySettings('mrs-k', {
      checkin_window: 120, ack_window: 120, safety_pin: '1234', duress_pin: '5678',
      supporters: [{ id: 'ana', name: 'Ana', location: false, alert_details: true, replay: false }],
    })
    const active = await actual.fetchActiveCheckins('mrs-k', 'ana')
    expect(active).toHaveLength(1)
    expect(active[0]).not.toHaveProperty('location')
    const saved = await actual.fetchSafetySettings('mrs-k')
    expect(saved).not.toHaveProperty('safety_pin')
    expect(saved).not.toHaveProperty('duress_pin')
    expect(saved.safety_pin_set).toBe(true)
    const acknowledged = await actual.acknowledgeCheckin(alarm.id, 'ana')
    expect(acknowledged.status).toBe('acknowledged')
    expect(acknowledged).not.toHaveProperty('location')
    const resolved = await actual.resolveCheckin(alarm.id, 'ana', 'helped')
    expect(resolved.status).toBe('resolved')
    expect(resolved).not.toHaveProperty('location')
    expect(await actual.fetchActiveCheckins('mrs-k', 'ana')).toEqual([])
    actual.setMockCheckins([])
  })

  it('surfaces a reachable service refusal instead of substituting demo success', async () => {
    const actual = await vi.importActual<typeof api>('./api.ts')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 403 }))
    await expect(actual.fetchActiveCheckins('mrs-k', 'ana')).rejects.toThrow('Safety service returned 403')
    await expect(actual.resolveCheckin(alarm.id, 'ana', 'helped')).rejects.toThrow('Safety service returned 403')
  })
})
