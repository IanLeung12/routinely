import { apiUrl } from '../config.ts'

/** Rooms currently paused (SPEC §12), from GET /monitoring. */
export async function fetchPausedRooms(): Promise<string[]> {
  const response = await fetch(`${apiUrl}/monitoring`)
  if (!response.ok) {
    throw new Error(`fetchPausedRooms failed: ${response.status}`)
  }
  const body = (await response.json()) as { paused_rooms: string[] }
  return body.paused_rooms
}

/** Pause or resume monitoring for one room (SPEC §12). */
export async function setRoomMonitoring(room: string, on: boolean): Promise<void> {
  const response = await fetch(`${apiUrl}/rooms/${encodeURIComponent(room)}/monitoring`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ on }),
  })
  if (!response.ok) {
    throw new Error(`setRoomMonitoring failed: ${response.status}`)
  }
}

/** One logged change to a room's monitoring switch (SPEC §12): `on` false is a pause,
 * true a resume, `by` whoever made it and `at` an ISO 8601 timestamp. */
export type MonitoringChange = {
  on: boolean
  by: string
  at: string
}

/** This room's recent monitoring changes, newest first, from
 * GET /rooms/{room}/monitoring/history (SPEC §12): the audit trail under the switch. */
export async function fetchMonitoringHistory(room: string): Promise<MonitoringChange[]> {
  const response = await fetch(`${apiUrl}/rooms/${encodeURIComponent(room)}/monitoring/history`)
  if (!response.ok) {
    throw new Error(`fetchMonitoringHistory failed: ${response.status}`)
  }
  const body = (await response.json()) as { history?: MonitoringChange[] }
  // A body without a history is a room with no changes to show, not a broken screen:
  // the trail sits inside the resident detail and must never take it down.
  return body.history ?? []
}
