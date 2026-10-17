import type { Replay, ReplayMarker, ReplaySummary } from '../contracts.ts'
import { mockReplays as evidenceReplays } from './replay.ts'

function replay(personId: string, suffix: string, day: number, type?: ReplayMarker['type']): Replay {
  const sessionId = `${personId}-${suffix}`
  return {
    session_id: sessionId,
    person_id: personId,
    task_id: 'make-tea',
    started_at: `2026-01-0${day}T09:00:00Z`,
    duration_s: 12,
    error_count: type ? 1 : 0,
    error_types: type ? [type] : [],
    normal: !type,
    markers: type ? [{ error_id: `${sessionId}-error`, type, step_id: 'pour-water', t_start: 10, t_end: 12 }] : [],
    frames: evidenceReplays['mrs-k-change-1'].today.map(frame => ({ ...frame, session_id: sessionId })),
  }
}

/** Offline library: skeletons only, with one clean comparison session. */
export const mockReplays: Replay[] = [
  replay('mrs-k', 'omission', 4, 'omission'),
  replay('mrs-k', 'sequence', 3, 'sequence'),
  replay('mrs-k', 'repeat', 2, 'perseveration'),
  replay('mr-d', 'omission', 2, 'omission'),
  replay('mrs-k', 'normal', 1),
]

export function replaySummary({ frames: _frames, markers: _markers, ...summary }: Replay): ReplaySummary {
  return summary
}

