import { apiUrl } from '../config.ts'
import { mockActiveCheckIn, mockRespond } from '../mock/checkins.ts'
import { supervisorsOf } from '../people/api.ts'
import type { CheckIn, PersonCheckIn, ResolutionReason, SafetySettingsData, SafetySettingsInput } from './types.ts'

const checkins = new Map<string, CheckIn>()
const settings = new Map<string, SafetySettingsData>()

/** Allows the shared offline demo/test harness to supply a scenario. */
export function setMockCheckins(scenario: CheckIn[]): void {
  checkins.clear()
  for (const checkin of scenario) checkins.set(checkin.checkin_id, structuredClone(checkin))
}

function sharingFor(person: string, supporter: string): { location: boolean; alert_details: boolean; replay: boolean } | undefined {
  const configured = settings.get(person)
  if (configured) return configured.supporters.find(entry => entry.id === supporter)?.share
  return supervisorsOf(person).some(entry => entry.id === supporter)
    ? { location: false, alert_details: false, replay: false }
    : undefined
}

/** `record` as `supporter` may see it: whatever they were not given stays entirely
 * absent, the way the real `supporter_view` leaves it out rather than blanking it. */
function sharedCheckin(record: CheckIn, supporter: string): CheckIn {
  const share = sharingFor(record.person_id, supporter)
  const { location, location_simulated, alert_id, events, replays_url, ...base } = record
  const view: CheckIn = { ...base }
  if (share?.location && location !== undefined) {
    view.location = location
    view.location_simulated = location_simulated
  }
  if (share?.alert_details) {
    view.alert_id = alert_id
    view.events = events
  }
  if (share?.replay && replays_url !== undefined) view.replays_url = replays_url
  return view
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

/** The supervisor's own feed (SPEC section 18): `?supporter=` alone - the real route
 * 422s if `person` is sent alongside it, because a payload that depends on who is
 * asking cannot guess. Answers wrapped as `{ checkins: [...] }`, one entry per
 * check-in that has actually reached this supporter. */
export function fetchActiveCheckins(supporter: string): Promise<CheckIn[]> {
  const query = new URLSearchParams({ supporter })
  return request<{ checkins: CheckIn[] }>(`/checkins/active?${query}`, undefined, () => ({
    checkins: [...checkins.values()]
      .filter(c => c.state !== 'ok' && c.state !== 'resolved' && c.notified.includes(supporter) && sharingFor(c.person_id, supporter))
      .map(checkin => sharedCheckin(checkin, supporter)),
  })).then(result => result.checkins)
}

function transition(id: string, state: 'acknowledged' | 'resolved', actor: string, reason?: ResolutionReason): CheckIn {
  const previous = checkins.get(id)
  if (!previous) throw new Error('Check-in is no longer available')
  if (!sharingFor(previous.person_id, actor)) throw new Error('Supporter is not linked')
  const next: CheckIn = {
    ...previous,
    state,
    supporter: actor,
    acknowledged_by: state === 'acknowledged' ? actor : previous.acknowledged_by,
    resolved_by: state === 'resolved' ? actor : previous.resolved_by,
    resolved_reason: state === 'resolved' ? reason ?? null : previous.resolved_reason,
    events: [
      ...(previous.events ?? []),
      { event: state, at: new Date().toISOString(), actor, state, detail: reason ?? null },
    ],
  }
  checkins.set(id, next)
  return sharedCheckin(next, actor)
}

export function acknowledgeCheckin(id: string, supporter: string): Promise<CheckIn> {
  return request<{ checkin: CheckIn }>(`/checkins/${encodeURIComponent(id)}/ack`, json({ supporter }), () => ({
    checkin: transition(id, 'acknowledged', supporter),
  })).then(result => result.checkin)
}

export function resolveCheckin(id: string, by: string, reason: ResolutionReason): Promise<CheckIn> {
  return request<{ checkin: CheckIn }>(`/checkins/${encodeURIComponent(id)}/resolve`, json({ by, reason }), () => ({
    checkin: transition(id, 'resolved', by, reason),
  })).then(result => result.checkin)
}

function defaultSafetySettings(person: string): SafetySettingsData {
  return {
    person_id: person,
    name: '',
    checkin_window_s: 120,
    ack_window_s: 120,
    location: '',
    location_simulated: true,
    supporters: supervisorsOf(person).map(({ id, name, relationship }) => ({
      id,
      name,
      relationship,
      share: { location: false, alert_details: false, replay: false },
    })),
    safety_pin_set: false,
    duress_pin_set: false,
  }
}

export function fetchSafetySettings(person: string): Promise<SafetySettingsData> {
  return request(`/people/${encodeURIComponent(person)}/safety`, undefined, () => settings.get(person) ?? defaultSafetySettings(person))
}

export function saveSafetySettings(person: string, input: SafetySettingsInput): Promise<SafetySettingsData> {
  return request(`/people/${encodeURIComponent(person)}/safety`, json(input, 'PUT'), () => {
    const current = settings.get(person) ?? defaultSafetySettings(person)
    const { safety_pin, duress_pin, ...changes } = input
    const result: SafetySettingsData = {
      ...current,
      ...changes,
      safety_pin_set: Boolean(safety_pin) || current.safety_pin_set,
      duress_pin_set: Boolean(duress_pin) || current.duress_pin_set,
    }
    settings.set(person, result)
    return result
  })
}

/** The person's own screen (SPEC section 18, T451): `?person=` alone, never paired
 * with `?supporter=` - the real route 422s if both or neither are given, because a
 * payload that depends on who is asking cannot guess. Answers wrapped as
 * `{ checkins: [...] }`; at most one is ever open for a person at a time. */
export function fetchMyCheckin(person: string): Promise<PersonCheckIn | null> {
  const query = new URLSearchParams({ person })
  return request<{ checkins: PersonCheckIn[] } | PersonCheckIn[] | PersonCheckIn | null>(
    `/checkins/active?${query}`,
    undefined,
    () => {
      const checkin = mockActiveCheckIn(person)
      return checkin ? [checkin] : []
    },
  ).then(result => {
    if (result === null) return null
    const list = Array.isArray(result) ? result : 'checkins' in result ? result.checkins : [result]
    return list[0] ?? null
  })
}

/** The person checking in (SPEC section 18, T451). The safety PIN and the duress
 * PIN answer with the exact same `{ accepted: true }`, byte for byte - a wrong PIN
 * is a 401, not a failed connection, so it never falls through to the mock and the
 * countdown just keeps running. */
export async function respondToCheckin(checkinId: string, pin: string): Promise<{ accepted: boolean }> {
  let response: Response
  try {
    response = await fetch(`${apiUrl}/checkins/${encodeURIComponent(checkinId)}/respond`, json({ pin }))
  } catch {
    return mockRespond(checkinId, pin)
  }
  if (response.status === 401) return { accepted: false }
  if (!response.ok) throw new Error(`Safety service returned ${response.status}`)
  return { accepted: true }
}
