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
