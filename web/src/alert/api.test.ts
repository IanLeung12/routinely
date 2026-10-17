import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiUrl } from '../config.ts'
import { mockAlerts } from '../mock/alerts.ts'
import { fetchAlert, fetchAlerts, postFeedback } from './api.ts'

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
  mockAlerts[0].feedback = null
})

describe('alerts API', () => {
  it('fetches alerts and an individual alert from the API', async () => {
    const alert = { ...mockAlerts[0], alert_id: 'live-alert' }
    const fetch = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => [alert] })
      .mockResolvedValueOnce({ ok: true, json: async () => alert })
    vi.stubGlobal('fetch', fetch)

    expect(await fetchAlerts()).toEqual([alert])
    expect(await fetchAlert('live-alert')).toEqual(alert)
    expect(fetch).toHaveBeenNthCalledWith(1, `${apiUrl}/alerts`)
    expect(fetch).toHaveBeenNthCalledWith(2, `${apiUrl}/alerts/live-alert`)
  })

  it.each(['rejection', 'non-ok'])('falls back on GET %s', async failure => {
    vi.stubGlobal('fetch', failure === 'rejection'
      ? vi.fn().mockRejectedValue(new Error('offline'))
      : vi.fn().mockResolvedValue({ ok: false, status: 500 }))

    expect(await fetchAlerts()).toBe(mockAlerts)
    expect(await fetchAlert(mockAlerts[0].alert_id)).toBe(mockAlerts[0])
    expect(await fetchAlert('missing')).toBeNull()
  })

  it('returns null for a 404 even if the mock contains the alert', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 404 }))
    expect(await fetchAlert(mockAlerts[0].alert_id)).toBeNull()
  })

  it('posts JSON feedback and returns the server alert', async () => {
    const updated = { ...mockAlerts[0], summary: 'Server response' }
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => updated })
    vi.stubGlobal('fetch', fetch)

    expect(await postFeedback('alert/1', 'confirmed', 'Reviewed')).toBe(updated)
    expect(fetch).toHaveBeenCalledWith(`${apiUrl}/alerts/alert%2F1/feedback`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ verdict: 'confirmed', note: 'Reviewed' }),
    })
  })

  it('sends the picked cause, and null once it is cleared', async () => {
    const updated = { ...mockAlerts[0], summary: 'Server response' }
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => updated })
    vi.stubGlobal('fetch', fetch)

    await postFeedback('alert-1', 'confirmed', undefined, 'sudden_change')
    expect(fetch).toHaveBeenLastCalledWith(`${apiUrl}/alerts/alert-1/feedback`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ verdict: 'confirmed', cause: 'sudden_change' }),
    })

    await postFeedback('alert-1', 'confirmed', undefined, null)
    expect(fetch).toHaveBeenLastCalledWith(`${apiUrl}/alerts/alert-1/feedback`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ verdict: 'confirmed', cause: null }),
    })
  })

  it.each([404, 422, 500])('rejects HTTP %s without mutating local alerts', async status => {
    const before = structuredClone(mockAlerts)
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status }))

    await expect(postFeedback(mockAlerts[0].alert_id, 'confirmed'))
      .rejects.toThrow(`Feedback not saved (${status})`)
    expect(mockAlerts).toEqual(before)
  })

  it('records feedback locally on a network error', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-10-17T10:00:00Z'))
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))

    const alert = await postFeedback(mockAlerts[0].alert_id, 'false_alarm', 'Assisted')
    expect(alert.feedback).toEqual({
      verdict: 'false_alarm', by: 'nurse', at: '2026-10-17T10:00:00.000Z', note: 'Assisted',
    })
    expect((await fetchAlert(alert.alert_id))?.feedback).toEqual(alert.feedback)
  })

  it('rejects feedback for unknown offline alerts', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    await expect(postFeedback('missing', 'confirmed')).rejects.toThrow('Unknown alert: missing')
  })
})
