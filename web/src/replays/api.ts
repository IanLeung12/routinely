import { apiUrl } from '../config.ts'
import type { PersonReplays, Replay } from '../contracts.ts'
import { mockReplays, replaySummary } from '../mock/replays.ts'

const deleted = new Set<string>()

export async function fetchPersonReplays(personId: string): Promise<PersonReplays> {
  try {
    const response = await fetch(`${apiUrl}/people/${encodeURIComponent(personId)}/replays`)
    if (response.ok) return await response.json() as PersonReplays
  } catch { /* Fall back to the offline library while the API is unreachable. */ }
  const replays = mockReplays.filter(replay => replay.person_id === personId && !deleted.has(replay.session_id))
  const normal = replays.find(replay => replay.normal)
  return { person_id: personId, replays: replays.filter(replay => !replay.normal).map(replaySummary), normal: normal ? replaySummary(normal) : null }
}

export async function fetchReplay(replayId: string): Promise<Replay> {
  try {
    const response = await fetch(`${apiUrl}/replays/${encodeURIComponent(replayId)}`)
    if (response.ok) return await response.json() as Replay
  } catch { /* Fall back to skeleton frames while the API is unreachable. */ }
  const replay = mockReplays.find(replay => replay.session_id === replayId && !deleted.has(replayId))
  if (!replay) throw new Error('Replay not found')
  return replay
}

export async function deleteReplay(replayId: string): Promise<void> {
  try {
    const response = await fetch(`${apiUrl}/replays/${encodeURIComponent(replayId)}`, { method: 'DELETE' })
    if (response.ok) {
      deleted.add(replayId)
      return
    }
  } catch { /* Apply deletion to the offline library while the API is unreachable. */ }
  if (!mockReplays.some(replay => replay.session_id === replayId) || deleted.has(replayId)) throw new Error('Replay not found')
  deleted.add(replayId)
}
