import { apiUrl } from '../config.ts'
import type { PersonReplays, Replay } from '../contracts.ts'
import { mockReplays, replaySummary } from '../mock/replays.ts'

const deleted = new Set<string>()

export async function fetchPersonReplays(personId: string): Promise<PersonReplays> {
  let response: Response
  try {
    response = await fetch(`${apiUrl}/people/${encodeURIComponent(personId)}/replays`)
  } catch {
    // Fall back to the offline library only while the API is unreachable.
    const replays = mockReplays.filter(replay => replay.person_id === personId && !deleted.has(replay.session_id))
    const normal = replays.find(replay => replay.normal)
    return { person_id: personId, replays: replays.filter(replay => !replay.normal).map(replaySummary), normal: normal ? replaySummary(normal) : null }
  }
  if (!response.ok) throw new Error('Could not fetch replays')
  return await response.json() as PersonReplays
}

export async function fetchReplay(replayId: string): Promise<Replay> {
  let response: Response
  try {
    response = await fetch(`${apiUrl}/replays/${encodeURIComponent(replayId)}`)
  } catch {
    // Fall back to skeleton frames only while the API is unreachable.
    const replay = mockReplays.find(replay => replay.session_id === replayId && !deleted.has(replayId))
    if (!replay) throw new Error('Replay not found')
    return replay
  }
  if (response.status === 404) throw new Error('Replay not found')
  if (!response.ok) throw new Error('Could not fetch replay')
  return await response.json() as Replay
}

export async function deleteReplay(replayId: string): Promise<void> {
  let response: Response
  try {
    response = await fetch(`${apiUrl}/replays/${encodeURIComponent(replayId)}`, { method: 'DELETE' })
  } catch {
    // Apply deletion to the offline library only while the API is unreachable.
    if (!mockReplays.some(replay => replay.session_id === replayId) || deleted.has(replayId)) throw new Error('Replay not found')
    deleted.add(replayId)
    return
  }
  if (response.status === 404) throw new Error('Replay not found')
  if (!response.ok) throw new Error('Could not delete replay')
  deleted.add(replayId)
}
