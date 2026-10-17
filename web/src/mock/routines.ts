import type { RoutineDraftResult, SavedRoutine, TaskGraph } from '../routines/types.ts'

/** Detector classes the pipeline already knows (`tasks/tea.yaml`, `tasks/meds.yaml`),
 * so the offline drafts below can show a believable "needs training" note for the
 * ones a real detector wouldn't. */
const KNOWN_OBJECTS = new Set([
  'kettle', 'cup', 'teabag', 'milk', 'sugar', 'spoon',
  'glass', 'water_jug', 'pill_organiser', 'pill_bottle',
])

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}

function needsTrainingFor(graph: TaskGraph): string[] {
  const objects = new Set<string>()
  for (const step of graph.steps) {
    for (const object of step.objects) {
      if (!KNOWN_OBJECTS.has(object)) objects.add(object)
    }
  }
  return [...objects]
}

function draftResult(graph: TaskGraph): RoutineDraftResult {
  return {
    draft: { steps: clone(graph.steps) },
    task_graph: clone(graph),
    needs_training: needsTrainingFor(graph),
    warnings: [],
  }
}

const TEA_GRAPH: TaskGraph = {
  id: 'make_tea',
  title: 'Make tea',
  steps: [
    { id: 'fill_kettle', label: 'Fill the kettle', objects: ['kettle'], depends_on: [], optional: false, once_only: true },
    { id: 'boil', label: 'Boil the kettle', objects: ['kettle'], depends_on: ['fill_kettle'], optional: false, once_only: true },
    { id: 'get_cup', label: 'Get a cup', objects: ['cup'], depends_on: [], optional: false, once_only: true },
    { id: 'teabag_in_cup', label: 'Put the teabag in the cup', objects: ['teabag', 'cup'], depends_on: ['get_cup'], optional: false, once_only: true },
    { id: 'pour', label: 'Pour the water', objects: ['kettle', 'cup'], depends_on: ['boil', 'teabag_in_cup'], optional: false, once_only: true },
    { id: 'milk', label: 'Add milk', objects: ['milk', 'cup'], depends_on: ['pour'], optional: true, once_only: true },
    { id: 'sugar', label: 'Add sugar', objects: ['sugar', 'spoon'], depends_on: ['pour'], optional: true, once_only: true },
    { id: 'stir', label: 'Stir', objects: ['spoon', 'cup'], depends_on: ['pour'], optional: false, once_only: false },
    { id: 'remove_teabag', label: 'Take the teabag out', objects: ['teabag', 'spoon'], depends_on: ['pour'], optional: false, once_only: true },
  ],
}

const MEDS_GRAPH: TaskGraph = {
  id: 'take_meds',
  title: 'Take medication with water',
  steps: [
    { id: 'get_glass', label: 'Get a glass', objects: ['glass'], depends_on: [], optional: false, once_only: true },
    { id: 'fill_glass', label: 'Fill the glass with water', objects: ['water_jug', 'glass'], depends_on: ['get_glass'], optional: false, once_only: true },
    { id: 'open_organiser', label: 'Open the pill organiser', objects: ['pill_organiser', 'pill_bottle'], depends_on: [], optional: false, once_only: true },
    { id: 'take_pill', label: 'Take the pill out', objects: ['pill_organiser', 'pill_bottle'], depends_on: ['open_organiser'], optional: false, once_only: true },
    { id: 'drink_water', label: 'Drink the water', objects: ['glass'], depends_on: ['take_pill', 'fill_glass'], optional: false, once_only: false },
    { id: 'close_organiser', label: 'Close the organiser', objects: ['pill_organiser', 'pill_bottle'], depends_on: ['take_pill'], optional: true, once_only: true },
  ],
}

/** Offline/demo draft (T437's canned-fixture rule): brushing teeth, with two objects
 * ("toothbrush", "toothpaste") a stock detector wouldn't know, so the builder's
 * "needs training" note has something believable to show. */
const BRUSH_TEETH_GRAPH: TaskGraph = {
  id: 'brush_teeth',
  title: 'Brush teeth',
  steps: [
    { id: 'get_toothbrush', label: 'Get the toothbrush', objects: ['toothbrush'], depends_on: [], optional: false, once_only: true },
    { id: 'add_toothpaste', label: 'Put toothpaste on the brush', objects: ['toothpaste', 'toothbrush'], depends_on: ['get_toothbrush'], optional: false, once_only: true },
    { id: 'brush', label: 'Brush', objects: ['toothbrush'], depends_on: ['add_toothpaste'], optional: false, once_only: false },
    { id: 'rinse_mouth', label: 'Rinse and spit', objects: ['cup'], depends_on: ['brush'], optional: false, once_only: false },
    { id: 'rinse_brush', label: 'Rinse the toothbrush', objects: ['toothbrush'], depends_on: ['brush'], optional: true, once_only: true },
  ],
}

const MAKE_TOAST_GRAPH: TaskGraph = {
  id: 'make_toast',
  title: 'Make toast',
  steps: [
    { id: 'get_bread', label: 'Get a slice of bread', objects: ['bread'], depends_on: [], optional: false, once_only: true },
    { id: 'toast', label: 'Put the bread in the toaster', objects: ['bread', 'toaster'], depends_on: ['get_bread'], optional: false, once_only: true },
    { id: 'get_plate', label: 'Get a plate', objects: ['plate'], depends_on: [], optional: false, once_only: true },
    { id: 'plate_toast', label: 'Put the toast on the plate', objects: ['toaster', 'plate'], depends_on: ['toast', 'get_plate'], optional: false, once_only: true },
    { id: 'butter', label: 'Add butter', objects: ['butter', 'plate'], depends_on: ['plate_toast'], optional: true, once_only: true },
  ],
}

export const mockBuiltInRoutines: SavedRoutine[] = [
  { id: TEA_GRAPH.id, title: TEA_GRAPH.title, task_graph: clone(TEA_GRAPH), built_in: true },
  { id: MEDS_GRAPH.id, title: MEDS_GRAPH.title, task_graph: clone(MEDS_GRAPH), built_in: true },
]

/** Picks a canned draft by keyword, same rule as `pipeline/tests/fixtures/routine_builder/`,
 * so the demo works on the offline try-out link with no Gemini key. "Brush teeth" is the
 * default: a believable draft even for a description that matches nothing. */
export function mockDraftFromText(description: string): RoutineDraftResult {
  const text = description.toLowerCase()
  if (text.includes('toast')) return draftResult(MAKE_TOAST_GRAPH)
  if (text.includes('tea')) return draftResult(TEA_GRAPH)
  if (text.includes('med') || text.includes('pill')) return draftResult(MEDS_GRAPH)
  return draftResult(BRUSH_TEETH_GRAPH)
}

export function mockDraftFromVideo(): RoutineDraftResult {
  return draftResult(BRUSH_TEETH_GRAPH)
}
