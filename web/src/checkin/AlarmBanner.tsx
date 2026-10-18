import { useEffect, useRef, useState } from 'react'
import { Button } from '../ui/Button.tsx'
import { acknowledgeCheckin, fetchActiveCheckins, resolveCheckin } from './api.ts'
import { createAlarmSound } from './alarmSound.ts'
import { EscalationTimeline } from './EscalationTimeline.tsx'
import type { CheckIn, ResolutionReason } from './types.ts'
import './alarm.css'

type Person = { id: string; name: string }

/** Lives in the shell, outside screen routing, so navigation cannot dismiss it. */
export function AlarmBanner({ people, supporter }: { people: Person[]; supporter: string }) {
  const [checkins, setCheckins] = useState<CheckIn[]>([])
  const [error, setError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<string | null>(null)
  const [reasons, setReasons] = useState<Record<string, ResolutionReason>>({})
  const [muted, setMuted] = useState(false)
  const [soundEnabled, setSoundEnabled] = useState(false)
  const [now, setNow] = useState(() => Date.now())
  const [sound] = useState(createAlarmSound)
  const revision = useRef(0)

  useEffect(() => {
    let cancelled = false
    let timer: ReturnType<typeof setTimeout>
    async function refresh() {
      const startedAt = revision.current
      try {
        const result = await fetchActiveCheckins(supporter)
        if (!cancelled && startedAt === revision.current) {
          setCheckins(previous => [
            ...result.map(item => {
              const confirmed = previous.find(entry => entry.checkin_id === item.checkin_id)
              // A stale poll cannot undo a confirmed action. Retain only its
              // state/events; shared fields always come from the new payload.
              if (confirmed && confirmed.state !== item.state && (confirmed.state === 'resolved' || (confirmed.state === 'acknowledged' && item.state !== 'resolved'))) {
                return { ...item, state: confirmed.state, events: confirmed.events }
              }
              return item
            }),
            ...previous.filter(item => item.state === 'resolved' && !result.some(next => next.checkin_id === item.checkin_id)),
          ])
          setError(null)
        }
      } catch {
        if (!cancelled) setError('Safety alarms could not refresh. Existing alarms remain visible. Retrying…')
      } finally {
        if (!cancelled) {
          setLoading(false)
          setNow(Date.now())
          timer = setTimeout(refresh, 1000)
        }
      }
    }
    void refresh()
    return () => { cancelled = true; clearTimeout(timer) }
  }, [supporter])

  const permitted = checkins.filter(item => people.some(person => person.id === item.person_id))
  const alarming = permitted.some(item => item.state === 'alarm' || item.state === 'escalated')
  useEffect(() => {
    let cancelled = false
    if (!alarming || muted) {
      sound.stop()
    } else {
      void sound.start().then(enabled => { if (!cancelled) setSoundEnabled(enabled) })
    }
    return () => { cancelled = true; sound.stop() }
  }, [alarming, muted, sound])

  async function enableSound() {
    setMuted(false)
    setSoundEnabled(await sound.start())
  }

  async function act(item: CheckIn, action: 'ack' | 'resolve') {
    setBusy(item.checkin_id)
    setActionError(null)
    revision.current += 1
    try {
      const updated = action === 'ack'
        ? await acknowledgeCheckin(item.checkin_id, supporter)
        : await resolveCheckin(item.checkin_id, supporter, reasons[item.checkin_id] ?? 'helped')
      setCheckins(previous => previous.map(entry => entry.checkin_id === item.checkin_id ? updated : entry))
    } catch {
      setActionError('Your response was not saved. Please try again; the alarm remains active.')
    } finally {
      revision.current += 1
      setBusy(null)
    }
  }

  const visible = permitted.filter(item => ['alarm', 'escalated', 'acknowledged', 'resolved'].includes(item.state))
  return (
    <div className="supervisor-alarms">
      {loading && <p role="status">Loading safety alarms…</p>}
      {error && <p role="status">{error}</p>}
      {actionError && <p role="status">{actionError}</p>}
      {alarming && (
        <div className="alarm-banner__sound">
          {!soundEnabled && !muted && <Button onClick={() => void enableSound()}>Enable sound</Button>}
          <Button aria-pressed={muted} onClick={() => setMuted(value => !value)}>{muted ? 'Unmute alarm' : 'Mute alarm'}</Button>
          {!soundEnabled && !muted && <span>Sound needs your permission. The alarm stays visible.</span>}
        </div>
      )}
      {visible.map(item => {
        const name = item.person_name || people.find(person => person.id === item.person_id)?.name || 'Someone you support'
        const resolved = item.state === 'resolved'
        const acknowledged = item.state === 'acknowledged'
        const minutes = Math.max(0, Math.floor((now - Date.parse(item.started_at)) / 60000))
        return (
          <section className={`alarm-banner${resolved ? ' alarm-banner--resolved' : ''}`} key={item.checkin_id} aria-label={`${name} safety check-in`}>
            <div role={resolved ? 'status' : 'alert'}>
              <h2>{resolved ? `${name}: check-in resolved` : item.duress ? `${name}: silent help request` : `${name} hasn't checked in (${minutes} min)`}</h2>
              {!resolved && <p>{acknowledged ? "Acknowledged — someone is on it. Resolve when everyone is okay." : item.state === 'escalated' ? 'Alarm escalated. Is everyone okay?' : 'Safety alarm. Is everyone okay?'}</p>}
            </div>
            {item.location && <p>Shared location: {item.location}</p>}
            {!resolved && (
              <div className="alarm-banner__actions">
                {!acknowledged && <Button variant="primary" disabled={busy !== null} onClick={() => void act(item, 'ack')}>I'm on it</Button>}
                <label>Resolution reason
                  <select value={reasons[item.checkin_id] ?? 'helped'} onChange={event => setReasons(previous => ({ ...previous, [item.checkin_id]: event.target.value as ResolutionReason }))}>
                    <option value="false_alarm">False alarm</option>
                    <option value="helped">Helped</option>
                    <option value="other">Other</option>
                  </select>
                </label>
                <Button disabled={busy !== null} onClick={() => void act(item, 'resolve')}>{busy === item.checkin_id ? 'Saving…' : 'Resolve'}</Button>
              </div>
            )}
            {item.events && <EscalationTimeline events={item.events} />}
          </section>
        )
      })}
    </div>
  )
}
