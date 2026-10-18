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
 * builder. This is `Routine.summary()` in `pipeline/src/routine_watch/routine_builder.py`
 * exactly: enough to list and pick a routine, and **no task graph** - only
 * `GET /routines/{id}` and `POST /routines` send that. */
export type RoutineSummary = {
  /** What the API addresses the routine by: a built-in's file name (`tea`), or the
   * graph's own id for one saved from the builder. */
  id: string
  title: string
  /** The graph's own id (`make_tea`), which for a built-in is not `id`. */
  task_id: string
  built_in: boolean
  source: 'built_in' | 'text' | 'video'
  step_count: number
  needs_training: string[]
}

/** One routine in full, as `GET /routines/{id}` and `POST /routines` answer
 * (`Routine.detail()`): a summary row plus the graph itself. */
export type SavedRoutine = RoutineSummary & {
  task_graph: TaskGraph
}
