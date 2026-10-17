/** The routine builder's data (T437's interface): a drafted or saved task graph in
 * the same shape as `tasks/tea.yaml`, so the task map, error classifier and scoring
 * that already read `tea`/`meds` can read a built one too. */

export type RoutineStep = {
  id: string
  label: string
  objects: string[]
  depends_on: string[]
  optional: boolean
  once_only: boolean
}

export type TaskGraph = {
  id: string
  title: string
  steps: RoutineStep[]
}

/** `POST /routines/draft`'s answer: the drafted graph, plus what the detector would
 * need to learn before it could score it. */
export type RoutineDraftResult = {
  draft: { steps: RoutineStep[] }
  task_graph: TaskGraph
  needs_training: string[]
  warnings: string[]
}

/** One row of `GET /routines`: a built-in (`tea`, `meds`) or a routine saved from the
 * builder. */
export type SavedRoutine = {
  id: string
  title: string
  task_graph: TaskGraph
  built_in: boolean
}
