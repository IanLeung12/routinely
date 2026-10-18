import { apiUrl } from '../config.ts'
import {
  mockBuiltInRoutines,
  mockDraftFromText,
  mockDraftFromVideo,
  mockSavedRoutine,
} from '../mock/routines.ts'
import type { RoutineDraftResult, RoutineSummary, SavedRoutine, TaskGraph } from './types.ts'

const SAVED_KEY = 'rw.routines.saved'

function normalizeGraph(graph: TaskGraph): TaskGraph {
  return {
    ...graph,
    steps: graph.steps.map(step => ({
      ...step,
      objects: step.objects ?? [],
      depends_on: step.depends_on ?? (step as typeof step & { deps?: string[] }).deps ?? [],
    })),
  }
}

function normalizeDraft(draft: RoutineDraftResult): RoutineDraftResult {
  return {
    ...draft,
    task_graph: normalizeGraph(draft.task_graph),
    needs_training: draft.needs_training ?? [],
    warnings: draft.warnings ?? [],
  }
}

function normalizeRoutine<T extends RoutineSummary>(routine: T): T {
  return {
    ...routine,
    needs_training: routine.needs_training ?? [],
    ...('task_graph' in routine
      ? { task_graph: normalizeGraph((routine as SavedRoutine).task_graph) }
      : {}),
  }
}

function readSaved(): SavedRoutine[] {
  try {
    const raw = localStorage.getItem(SAVED_KEY)
    if (raw === null) return []
    const parsed: unknown = JSON.parse(raw)
    return Array.isArray(parsed) ? (parsed as SavedRoutine[]).map(normalizeRoutine) : []
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

/** The message for a non-OK response: FastAPI's `{detail: string}` when there is one,
 * else a generic message naming the status. Never throws itself, so callers can await
 * it inside the branch that is about to throw. */
async function errorDetail(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json()
    if (body && typeof body === 'object' && typeof (body as { detail?: unknown }).detail === 'string') {
      return (body as { detail: string }).detail
    }
  } catch {
    // No JSON body to read a detail from.
  }
  return `the server could not handle that request (${response.status})`
}

/** Drafts a routine from a plain-language description (T437's `POST /routines/draft`,
 * `description` only). Falls back to a canned draft only when the API is unreachable;
 * a reachable API that refuses the request throws so the screen can show why. */
export async function draftFromText(description: string): Promise<RoutineDraftResult> {
  let response: Response
  try {
    const form = new FormData()
    form.append('description', description)
    response = await fetch(`${apiUrl}/routines/draft`, { method: 'POST', body: form })
  } catch {
    return mockDraftFromText(description)
  }
  if (!response.ok) throw new Error(await errorDetail(response))
  return normalizeDraft((await response.json()) as RoutineDraftResult)
}

/** Drafts a routine from a setup clip. `consent` must be true before this is called —
 * callers gate the control that triggers it, same as the API's 400 on a missing
 * `consent: true` (SPEC §8, §12: one clip, sent once, never stored). Falls back to a
 * canned draft only when the API is unreachable; a reachable API that refuses the clip
 * (400/413/422/502) throws with its `detail` instead of showing a fake draft. */
export async function draftFromVideo(file: File, consent: boolean): Promise<RoutineDraftResult> {
  if (!consent) throw new Error('Consent is required before a clip can be sent.')
  let response: Response
  try {
    const form = new FormData()
    form.append('video', file)
    form.append('consent', 'true')
    response = await fetch(`${apiUrl}/routines/draft`, { method: 'POST', body: form })
  } catch {
    return mockDraftFromVideo()
  }
  if (!response.ok) throw new Error(await errorDetail(response))
  return normalizeDraft((await response.json()) as RoutineDraftResult)
}

/** Built-ins (`tea`, `meds`) plus whatever has been saved, newest last. Falls back to
 * the built-ins plus whatever is saved locally when the API isn't reachable. */
export async function fetchRoutines(): Promise<RoutineSummary[]> {
  let response: Response
  try {
    response = await fetch(`${apiUrl}/routines`)
  } catch {
    return [...mockBuiltInRoutines, ...readSaved()]
  }
  if (!response.ok) throw new Error(await errorDetail(response))
  return ((await response.json()) as RoutineSummary[]).map(normalizeRoutine)
}

/** Saves a reviewed task graph (`POST /routines`). Falls back to `localStorage` only
 * when the API is unreachable; a reachable API that refuses the save (422 bad graph,
 * 409 built-in id or full library) throws instead of being written down as saved. */
export async function saveRoutine(graph: TaskGraph): Promise<SavedRoutine> {
  let response: Response
  try {
    response = await fetch(`${apiUrl}/routines`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        task_graph: {
          ...graph,
          steps: graph.steps.map(({ depends_on, ...step }) => ({ ...step, deps: depends_on })),
        },
      }),
    })
  } catch {
    const saved = mockSavedRoutine(graph)
    writeSaved([...readSaved(), saved])
    return saved
  }
  if (!response.ok) throw new Error(await errorDetail(response))
  return normalizeRoutine((await response.json()) as SavedRoutine)
}
