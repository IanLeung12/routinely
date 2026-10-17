import { apiUrl } from '../config.ts'
import { mockBuiltInRoutines, mockDraftFromText, mockDraftFromVideo } from '../mock/routines.ts'
import type { RoutineDraftResult, SavedRoutine, TaskGraph } from './types.ts'

const SAVED_KEY = 'rw.routines.saved'

function readSaved(): SavedRoutine[] {
  try {
    const raw = localStorage.getItem(SAVED_KEY)
    if (raw === null) return []
    const parsed: unknown = JSON.parse(raw)
    return Array.isArray(parsed) ? (parsed as SavedRoutine[]) : []
  } catch {
    return []
  }
}

function writeSaved(routines: SavedRoutine[]): void {
  try {
    localStorage.setItem(SAVED_KEY, JSON.stringify(routines))
  } catch {
    // Storage unavailable: the save still shows up for the rest of this visit.
  }
}

/** Drafts a routine from a plain-language description (T437's `POST /routines/draft`,
 * `description` only). Falls back to a canned draft offline, same as the other
 * screens' `fetch...WithSource` helpers. */
export async function draftFromText(description: string): Promise<RoutineDraftResult> {
  try {
    const form = new FormData()
    form.append('description', description)
    const response = await fetch(`${apiUrl}/routines/draft`, { method: 'POST', body: form })
    if (response.ok) return (await response.json()) as RoutineDraftResult
  } catch {
    // Offline: fall through to the mock draft below.
  }
  return mockDraftFromText(description)
}

/** Drafts a routine from a setup clip. `consent` must be true before this is called —
 * callers gate the control that triggers it, same as the API's 400 on a missing
 * `consent: true` (SPEC §8, §12: one clip, sent once, never stored). */
export async function draftFromVideo(file: File, consent: boolean): Promise<RoutineDraftResult> {
  if (!consent) throw new Error('Consent is required before a clip can be sent.')
  try {
    const form = new FormData()
    form.append('video', file)
    form.append('consent', 'true')
    const response = await fetch(`${apiUrl}/routines/draft`, { method: 'POST', body: form })
    if (response.ok) return (await response.json()) as RoutineDraftResult
  } catch {
    // Offline: fall through to the mock draft below.
  }
  return mockDraftFromVideo()
}

/** Built-ins (`tea`, `meds`) plus whatever has been saved, newest last. Falls back to
 * the built-ins plus whatever is saved locally when the API isn't reachable. */
export async function fetchRoutines(): Promise<SavedRoutine[]> {
  try {
    const response = await fetch(`${apiUrl}/routines`)
    if (response.ok) return (await response.json()) as SavedRoutine[]
  } catch {
    // Offline: fall through to the mock list below.
  }
  return [...mockBuiltInRoutines, ...readSaved()]
}

/** Saves a reviewed task graph (`POST /routines`). Falls back to `localStorage` so the
 * routine still shows up in `fetchRoutines()` for the rest of this visit when the API
 * isn't reachable. */
export async function saveRoutine(graph: TaskGraph): Promise<SavedRoutine> {
  try {
    const response = await fetch(`${apiUrl}/routines`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_graph: graph }),
    })
    if (response.ok) return (await response.json()) as SavedRoutine
  } catch {
    // Offline: fall through to the local save below.
  }
  const saved: SavedRoutine = { id: graph.id, title: graph.title, task_graph: graph, built_in: false }
  writeSaved([...readSaved(), saved])
  return saved
}
