import { apiUrl } from '../config.ts'
import { supervisorsOf } from '../people/api.ts'
import type { CheckIn, ResolutionReason, SafetySettingsData, SafetySettingsInput } from './types.ts'

const checkins = new Map<string, CheckIn>()
const settings = new Map<string, SafetySettingsData>()

/** Allows the shared offline demo/test harness to supply a scenario. */
export function setMockCheckins(scenario: CheckIn[]): void {
  checkins.clear()
  for (const checkin of scenario) checkins.set(checkin.id, structuredClone(checkin))
}

function sharingFor(person: string, supporter: string) {
  const configured = settings.get(person)
  return configured
    ? configured.supporters.find(entry => entry.id === supporter)
    : supervisorsOf(person).some(entry => entry.id === supporter) ? { location: false } : undefined
}

function sharedCheckin(checkin: CheckIn, supporter: string): CheckIn {
  const { location, ...publicCheckin } = checkin
  return sharingFor(checkin.person_id, supporter)?.location && location ? { ...publicCheckin, location } : publicCheckin
}

/** Only a failed connection uses the fake. HTTP failures remain visible. */
async function request<T>(path: string, init: RequestInit | undefined, fake: () => T): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${apiUrl}${path}`, init)
  } catch {
    return fake()
  }
  if (!response.ok) throw new Error(`Safety service returned ${response.status}`)
  return response.json() as Promise<T>
}

function json(body: unknown, method = 'POST'): RequestInit {
  return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
}

export function fetchActiveCheckins(person: string, supporter: string): Promise<CheckIn[]> {
  const query = new URLSearchParams({ person, supporter })
  return request<CheckIn[] | CheckIn | null>(`/checkins/active?${query}`, undefined, () => {
    if (!sharingFor(person, supporter)) return []
    return [...checkins.values()]
      .filter(c => c.person_id === person && c.status !== 'resolved' && c.status !== 'ok')
      .map(checkin => sharedCheckin(checkin, supporter))
  })
    .then(result => result === null ? [] : Array.isArray(result) ? result : [result])
}

function transition(id: string, status: 'acknowledged' | 'resolved', actor: string, reason?: ResolutionReason): CheckIn {
  const previous = checkins.get(id)
  if (!previous) throw new Error('Check-in is no longer available')
  if (!sharingFor(previous.person_id, actor)) throw new Error('Supporter is not linked')
  const next = { ...previous, status, events: [...previous.events, { event: status, at: new Date().toISOString(), actor, reason }] }
  checkins.set(id, next)
  return sharedCheckin(next, actor)
}

export function acknowledgeCheckin(id: string, supporter: string): Promise<CheckIn> {
  return request(`/checkins/${encodeURIComponent(id)}/ack`, json({ supporter }), () => transition(id, 'acknowledged', supporter))
}

export function resolveCheckin(id: string, by: string, reason: ResolutionReason): Promise<CheckIn> {
  return request(`/checkins/${encodeURIComponent(id)}/resolve`, json({ by, reason }), () => transition(id, 'resolved', by, reason))
}

export function fetchSafetySettings(person: string): Promise<SafetySettingsData> {
  return request(`/people/${encodeURIComponent(person)}/safety`, undefined, () => settings.get(person) ?? {
    checkin_window: 120,
    ack_window: 120,
    supporters: supervisorsOf(person).map(({ id, name }) => ({ id, name, location: false, alert_details: true, replay: false })),
    safety_pin_set: false,
    duress_pin_set: false,
  })
}

export function saveSafetySettings(person: string, input: SafetySettingsInput): Promise<SafetySettingsData> {
  return request(`/people/${encodeURIComponent(person)}/safety`, json(input, 'PUT'), () => {
    const { safety_pin, duress_pin, ...publicSettings } = input
    const result = {
      ...publicSettings,
      safety_pin_set: Boolean(safety_pin) || publicSettings.safety_pin_set,
      duress_pin_set: Boolean(duress_pin) || publicSettings.duress_pin_set,
    }
    settings.set(person, result)
    return result
  })
}
