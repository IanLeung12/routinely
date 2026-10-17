import { apiUrl } from '../config.ts'
import type { Alert, CaptureFrame } from '../contracts.ts'
import { mockReplays } from '../mock/replay.ts'

/** The skeleton replay behind one alert's first error, plus the ghost layer: the
 * matching window from a normal session (SPEC section 5, MVP 5; section 9, screen 4). */
export type EvidenceReplay = {
  today: CaptureFrame[]
  normal: CaptureFrame[]
  /** The first error's start, in session seconds: where the replay should open. */
  t_start: number
}

async function replayWindow(path: string, t_start: number, t_end: number): Promise<CaptureFrame[] | null> {
  const response = await fetch(`${apiUrl}${path}?t_start=${t_start}&t_end=${t_end}`)
  if (!response.ok) return null
  const body = await response.json() as { frames: CaptureFrame[] }
  return body.frames
}

/** The replay evidence for the alert's first error (SPEC section 10 step 5):
 * skeleton frames from that session alongside the resident's normal routine over
 * the same window, from `GET /sessions/{id}/replay` and
 * `GET /residents/{id}/normal_replay` (`routine_watch.api`). Falls back to local
 * mock frames while the API is unreachable, like the other `api.ts` modules.
 * Returns null when its first error or a matching replay can't be found. */
export async function fetchReplay(alert: Alert): Promise<EvidenceReplay | null> {
  const error = alert.errors[0]
  if (!error) return null

  const { session_id, t_start, t_end } = error
  try {
    const [today, normal] = await Promise.all([
      replayWindow(`/sessions/${encodeURIComponent(session_id)}/replay`, t_start, t_end),
      replayWindow(`/residents/${encodeURIComponent(alert.resident_id)}/normal_replay`, t_start, t_end),
    ])
    if (today && normal) return { today, normal, t_start }
  } catch { /* Fall back to mock frames while the API is unreachable. */ }

  const mock = mockReplays[alert.alert_id]
  return mock ? { ...mock, t_start } : null
}
