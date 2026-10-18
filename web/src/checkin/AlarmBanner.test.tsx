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
  checkin_id: 'checkin-mrs-k-20261017T120000Z',
  person_id: 'mrs-k',
  person_name: 'Mrs. K',
  state: 'alarm',
  ask: 'Is everyone okay?',
  duress: false,
  silent: false,
  started_at: new Date(Date.now() - 120000).toISOString(),
  deadline: new Date().toISOString(),
  seconds_left: 0,
  for_supporter: 'ana',
  supporter: 'ana',
  notified: ['ana'],
  acknowledged_by: null,
  resolved_by: null,
  resolved_reason: null,
  device_online: true,
  alert_id: 'alert-1',
  events: [{ event: 'alarmed', at: '2026-10-17T12:02:00Z', actor: 'server', state: 'alarm', detail: 'ana' }],
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
  vi.mocked(api.acknowledgeCheckin).mockResolvedValue({ ...alarm, state: 'acknowledged', acknowledged_by: 'ana' })
  vi.mocked(api.resolveCheckin).mockResolvedValue({
    ...alarm,
    state: 'resolved',
    resolved_by: 'ana',
    resolved_reason: 'helped',
    events: [...(alarm.events ?? []), { event: 'resolved', at: '2026-10-17T12:03:00Z', actor: 'ana', state: 'resolved', detail: 'helped' }],
  })
  vi.stubGlobal('AudioContext', undefined)
})
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.clearAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers() })

describe('supervisor alarm', () => {
  it('shows the alarm, sends the chosen resolution, and clears the alarm while preserving its timeline', async () => {
    render(<AlarmBanner people={people} supporter="ana" />)
    expect(await screen.findByRole('heading', { name: "Mrs. K hasn't checked in (2 min)" })).toBeTruthy()
    expect(api.fetchActiveCheckins).toHaveBeenCalledWith('ana')
    expect(screen.queryByText(/location/i)).toBeNull()
    fireEvent.change(screen.getByLabelText('Resolution reason'), { target: { value: 'false_alarm' } })
    fireEvent.click(screen.getByRole('button', { name: 'Resolve' }))
    expect(await screen.findByText('Mrs. K: check-in resolved')).toBeTruthy()
    expect(screen.queryByRole('alert')).toBeNull()
    expect(screen.getByText('Resolved by ana: helped')).toBeTruthy()
    expect(api.resolveCheckin).toHaveBeenCalledWith('checkin-mrs-k-20261017T120000Z', 'ana', 'false_alarm')
  })

  it('shows duress as a silent help request and displays location only when supplied', async () => {
    vi.mocked(api.fetchActiveCheckins).mockResolvedValue([{ ...alarm, duress: true, location: 'Simulated room 2' }])
    render(<AlarmBanner people={people} supporter="ana" />)
    expect(await screen.findByText('Mrs. K: silent help request')).toBeTruthy()
    expect(screen.getByText('Shared location: Simulated room 2')).toBeTruthy()
  })

  it('does not show pending or safe check-ins as alarms', async () => {
    vi.mocked(api.fetchActiveCheckins).mockResolvedValue([{ ...alarm, state: 'pending' }, { ...alarm, checkin_id: 'safe', state: 'ok' }])
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
    expect(api.acknowledgeCheckin).toHaveBeenCalledWith('checkin-mrs-k-20261017T120000Z', 'ana')
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
    vi.mocked(api.fetchActiveCheckins).mockResolvedValueOnce([{ ...alarm, state: 'escalated' }])
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
      checkin_window_s: 120, ack_window_s: 120, safety_pin: '1234', duress_pin: '5678',
      supporters: [{ id: 'ana', name: 'Ana', relationship: 'nurse', share: { location: false, alert_details: true, replay: false } }],
    })
    const active = await actual.fetchActiveCheckins('ana')
    expect(active).toHaveLength(1)
    expect(active[0]).not.toHaveProperty('location')
    const saved = await actual.fetchSafetySettings('mrs-k')
    expect(saved).not.toHaveProperty('safety_pin')
    expect(saved).not.toHaveProperty('duress_pin')
    expect(saved.safety_pin_set).toBe(true)
    const acknowledged = await actual.acknowledgeCheckin(alarm.checkin_id, 'ana')
    expect(acknowledged.state).toBe('acknowledged')
    expect(acknowledged).not.toHaveProperty('location')
    const resolved = await actual.resolveCheckin(alarm.checkin_id, 'ana', 'helped')
    expect(resolved.state).toBe('resolved')
    expect(resolved).not.toHaveProperty('location')
    expect(await actual.fetchActiveCheckins('ana')).toEqual([])
    actual.setMockCheckins([])
  })

  it('surfaces a reachable service refusal instead of substituting demo success', async () => {
    const actual = await vi.importActual<typeof api>('./api.ts')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 403 }))
    await expect(actual.fetchActiveCheckins('ana')).rejects.toThrow('Safety service returned 403')
    await expect(actual.resolveCheckin(alarm.checkin_id, 'ana', 'helped')).rejects.toThrow('Safety service returned 403')
  })
})

describe('wire shapes match the real backend (T457)', () => {
  const supporterView = {
    checkin_id: 'checkin-mrs-k-20261017T120000Z',
    person_id: 'mrs-k',
    person_name: 'Mrs. K',
    state: 'alarm',
    ask: 'Is everyone okay?',
    duress: false,
    silent: false,
    started_at: '2026-10-17T12:00:00Z',
    deadline: '2026-10-17T12:02:00Z',
    seconds_left: 45,
    for_supporter: 'nurse-ana',
    supporter: 'nurse-ana',
    notified: ['nurse-ana'],
    acknowledged_by: null,
    resolved_by: null,
    resolved_reason: null,
    device_online: true,
    location: 'Room 204, care home',
    location_simulated: true,
    alert_id: 'alert-1',
    events: [],
  }

  it('asks /checkins/active with only ?supporter= and unwraps { checkins: [...] }', async () => {
    const actual = await vi.importActual<typeof api>('./api.ts')
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ checkins: [supporterView] }) })
    vi.stubGlobal('fetch', fetchMock)
    const result = await actual.fetchActiveCheckins('nurse-ana')
    expect(result).toEqual([supporterView])
    const requested = new URL(fetchMock.mock.calls[0][0] as string)
    expect(requested.searchParams.get('supporter')).toBe('nurse-ana')
    expect(requested.searchParams.has('person')).toBe(false)
  })

  it('unwraps { checkin: ... } from ack and resolve', async () => {
    const actual = await vi.importActual<typeof api>('./api.ts')
    const acked = { ...supporterView, state: 'acknowledged', acknowledged_by: 'nurse-ana', deadline: null, seconds_left: null }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ checkin: acked }) }))
    expect(await actual.acknowledgeCheckin('checkin-mrs-k-20261017T120000Z', 'nurse-ana')).toEqual(acked)

    const resolved = { ...acked, state: 'resolved', resolved_by: 'nurse-ana', resolved_reason: 'helped' }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ checkin: resolved }) }))
    expect(await actual.resolveCheckin('checkin-mrs-k-20261017T120000Z', 'nurse-ana', 'helped')).toEqual(resolved)
  })

  it('reads settings_payload with no wrapper and PUTs a body with no forbidden fields', async () => {
    const actual = await vi.importActual<typeof api>('./api.ts')
    const settingsPayload = {
      person_id: 'mrs-k',
      name: 'Mrs. K',
      checkin_window_s: 20,
      ack_window_s: 15,
      location: 'Room 204, care home',
      location_simulated: true,
      supporters: [{ id: 'nurse-ana', name: 'Nurse Ana', relationship: 'nurse', share: { location: true, alert_details: true, replay: true } }],
      safety_pin_set: true,
      duress_pin_set: true,
    }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => settingsPayload }))
    expect(await actual.fetchSafetySettings('mrs-k')).toEqual(settingsPayload)

    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => settingsPayload })
    vi.stubGlobal('fetch', fetchMock)
    await actual.saveSafetySettings('mrs-k', { checkin_window_s: 20, ack_window_s: 15, supporters: settingsPayload.supporters })
    const body = JSON.parse((fetchMock.mock.calls[0][1] as RequestInit).body as string)
    expect(Object.keys(body).sort()).toEqual(['ack_window_s', 'checkin_window_s', 'supporters'])
  })
})
