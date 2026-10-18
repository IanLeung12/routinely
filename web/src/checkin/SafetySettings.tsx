import { useEffect, useState } from 'react'
import { Button } from '../ui/Button.tsx'
import { Card } from '../ui/Card.tsx'
import { fetchSafetySettings, saveSafetySettings } from './api.ts'
import type { SafetySettingsData, SafetySupporter } from './types.ts'
import './alarm.css'

export function SafetySettings({ personId, onBack }: { personId: string; onBack: () => void }) {
  const [settings, setSettings] = useState<SafetySettingsData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [busy, setBusy] = useState(false)
  const [safetyPin, setSafetyPin] = useState('')
  const [duressPin, setDuressPin] = useState('')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    fetchSafetySettings(personId).then(result => {
      if (!cancelled) {
        setSettings(result)
        setSafetyPin('')
        setDuressPin('')
      }
    }).catch(() => { if (!cancelled) setError('Safety settings could not load. Please retry.') })
    return () => { cancelled = true }
  }, [personId, attempt])

  function move(index: number, direction: number) {
    if (!settings) return
    const supporters = [...settings.supporters]
    const target = index + direction
    ;[supporters[index], supporters[target]] = [supporters[target], supporters[index]]
    setSettings({ ...settings, supporters })
    setSaved(false)
  }

  function permission(index: number, field: 'location' | 'alert_details' | 'replay', value: boolean) {
    if (!settings) return
    setSettings({ ...settings, supporters: settings.supporters.map((supporter, i) => i === index ? { ...supporter, [field]: value } : supporter) })
    setSaved(false)
  }

  async function save() {
    if (!settings) return
    if (safetyPin && duressPin && safetyPin === duressPin) {
      setError('Choose different safety and duress PINs.')
      return
    }
    setBusy(true)
    setError(null)
    setSaved(false)
    try {
      const result = await saveSafetySettings(personId, {
        ...settings,
        ...(safetyPin ? { safety_pin: safetyPin } : {}),
        ...(duressPin ? { duress_pin: duressPin } : {}),
      })
      setSettings(result)
      setSafetyPin('')
      setDuressPin('')
      setSaved(true)
    } catch {
      setError('Safety settings were not saved. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="safety-settings">
      <Button onClick={onBack}>Back</Button>
      <h2>Safety settings</h2>
      <p>Check in first, then alarm your supporters in order. Demo alarms do not call or send messages.</p>
      {error && <p role="alert">{error}</p>}
      {!settings ? error ? <Button onClick={() => { setError(null); setAttempt(value => value + 1) }}>Retry</Button> : <p role="status">Loading safety settings…</p> : (
        <Card>
          <form onSubmit={event => { event.preventDefault(); void save() }}>
            <fieldset disabled={busy}>
              <legend>Check-in windows</legend>
              <label>Check-in window (seconds)
                <input type="number" min="1" required value={settings.checkin_window} onChange={event => { setSaved(false); setSettings({ ...settings, checkin_window: Number(event.target.value) }) }} />
              </label>
              <label>Acknowledgement window (seconds)
                <input type="number" min="1" required value={settings.ack_window} onChange={event => { setSaved(false); setSettings({ ...settings, ack_window: Number(event.target.value) }) }} />
              </label>
            </fieldset>
            <fieldset disabled={busy}>
              <legend>Supporters, in alarm order</legend>
              {settings.supporters.length === 0 ? <p>No supporters linked. Invite someone from your routine to receive alarms.</p> : (
                <ol className="safety-settings__supporters">
                  {settings.supporters.map((supporter: SafetySupporter, index) => (
                    <li key={supporter.id}>
                      <strong>{supporter.name}</strong>
                      <div className="safety-settings__order">
                        <Button disabled={index === 0} aria-label={`Move ${supporter.name} up`} onClick={() => move(index, -1)}>Move up</Button>
                        <Button disabled={index === settings.supporters.length - 1} aria-label={`Move ${supporter.name} down`} onClick={() => move(index, 1)}>Move down</Button>
                      </div>
                      <div className="safety-settings__permissions">
                        {([['location', 'Simulated location'], ['alert_details', 'Alert details'], ['replay', 'Replay']] as const).map(([field, label]) => (
                          <label key={field}><input type="checkbox" checked={supporter[field]} onChange={event => permission(index, field, event.target.checked)} />{label} for {supporter.name}</label>
                        ))}
                      </div>
                    </li>
                  ))}
                </ol>
              )}
            </fieldset>
            <fieldset disabled={busy}>
              <legend>Set or replace PINs</legend>
              <p>Existing PINs are never shown. Leave a field blank to keep its PIN.</p>
              <label>New safety PIN<input type="password" inputMode="numeric" autoComplete="new-password" pattern="[0-9]{4,8}" minLength={4} maxLength={8} value={safetyPin} onChange={event => { setSaved(false); setSafetyPin(event.target.value) }} /></label>
              <label>New duress PIN<input type="password" inputMode="numeric" autoComplete="new-password" pattern="[0-9]{4,8}" minLength={4} maxLength={8} value={duressPin} onChange={event => { setSaved(false); setDuressPin(event.target.value) }} /></label>
              <p>A duress PIN looks like a normal check-in to you and sends a silent help request to your supporters.</p>
            </fieldset>
            <Button type="submit" variant="primary" disabled={busy}>{busy ? 'Saving…' : 'Save safety settings'}</Button>
            {saved && <p role="status">Safety settings saved. PINs are hidden.</p>}
          </form>
        </Card>
      )}
    </section>
  )
}
