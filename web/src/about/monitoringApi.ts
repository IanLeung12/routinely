import { apiUrl } from '../config.ts'
import type { MonitoringChange } from '../contracts.ts'

export type { MonitoringChange }

/** Rooms currently paused (SPEC §12), from GET /monitoring. */
export async function fetchPausedRooms(): Promise<string[]> {
  const response = await fetch(`${apiUrl}/monitoring`)
  if (!response.ok) {
    throw new Error(`fetchPausedRooms failed: ${response.status}`)
  }
  const body = (await response.json()) as { paused_rooms: string[] }
  return body.paused_rooms
}

/** Pause or resume monitoring for one room (SPEC §12). Fires `monitoring-changed` on
 * `window` after a successful PUT, so a live panel already open for this room can react
 * right away instead of waiting for a remount or "Check again" (T275). */
export async function setRoomMonitoring(room: string, on: boolean): Promise<void> {
  const response = await fetch(`${apiUrl}/rooms/${encodeURIComponent(room)}/monitoring`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ on }),
  })
  if (!response.ok) {
    throw new Error(`setRoomMonitoring failed: ${response.status}`)
  }
  window.dispatchEvent(new CustomEvent('monitoring-changed', { detail: { room, paused: !on } }))
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
