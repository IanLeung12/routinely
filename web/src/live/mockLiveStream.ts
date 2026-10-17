import type { CaptureFrame } from '../contracts.ts'
import type { LiveMessage } from './useLiveSession.ts'

/** The `make_tea` task graph (`pipeline/src/routine_watch/tasks/tea.yaml`), for the
 * task-map layout. Fetching this from the API is a later task; for now the dashboard
 * only ever shows this one task. */
export const MOCK_STEPS = [
  { id: 'fill_kettle', label: 'Fill the kettle' },
  { id: 'boil', label: 'Boil the kettle' },
  { id: 'get_cup', label: 'Get a cup' },
  { id: 'teabag_in_cup', label: 'Put the teabag in the cup' },
  { id: 'pour', label: 'Pour the water' },
  { id: 'milk', label: 'Add milk' },
  { id: 'sugar', label: 'Add sugar' },
  { id: 'stir', label: 'Stir' },
  { id: 'remove_teabag', label: 'Take the teabag out' },
]

const MOCK_SESSION_ID = 'mock-session'

function frame(seq: number, t: number): CaptureFrame {
  return { session_id: MOCK_SESSION_ID, seq, t, source: 'synthetic', poses: [], hands: [], objects: [] }
}

/** A short `tea_skip_teabag_pour_twice`-like script (SPEC section 10 demo step 3): the
 * teabag never goes in the cup (omission) and the water gets poured twice (perseveration,
 * shown on the task map as a repeat). Played by `mockLiveStream` on timers. */
const SCRIPT: { delayMs: number; message: LiveMessage }[] = [
  { delayMs: 200, message: { type: 'frame', frame: frame(0, 2) } },
  {
    delayMs: 200,
    message: {
      type: 'step',
      event: {
        event_id: 'mock-fill-kettle',
        session_id: MOCK_SESSION_ID,
        step_id: 'fill_kettle',
        objects: ['kettle'],
        t_start: 1,
        t_end: 2,
        confidence: 0.95,
        source: 'rule',
      },
    },
  },
  { delayMs: 50, message: { type: 'step_state', states: { fill_kettle: 'done' } } },
  {
    delayMs: 300,
    message: {
      type: 'step',
      event: {
        event_id: 'mock-boil',
        session_id: MOCK_SESSION_ID,
        step_id: 'boil',
        objects: ['kettle'],
        t_start: 9,
        t_end: 10,
        confidence: 0.92,
        source: 'rule',
      },
    },
  },
  { delayMs: 50, message: { type: 'step_state', states: { boil: 'done' } } },
  {
    delayMs: 300,
    message: {
      type: 'step',
      event: {
        event_id: 'mock-get-cup',
        session_id: MOCK_SESSION_ID,
        step_id: 'get_cup',
        objects: ['cup'],
        t_start: 11,
        t_end: 12,
        confidence: 0.97,
        source: 'rule',
      },
    },
  },
  { delayMs: 50, message: { type: 'step_state', states: { get_cup: 'done' } } },
  { delayMs: 300, message: { type: 'frame', frame: frame(1, 20) } },
  {
    delayMs: 100,
    message: {
      type: 'step',
      event: {
        event_id: 'mock-pour-1',
        session_id: MOCK_SESSION_ID,
        step_id: 'pour',
        objects: ['kettle', 'cup'],
        t_start: 19,
        t_end: 20,
        confidence: 0.9,
        source: 'rule',
      },
    },
  },
  { delayMs: 50, message: { type: 'step_state', states: { pour: 'done' } } },
  {
    delayMs: 300,
    message: {
      type: 'step',
      event: {
        event_id: 'mock-stir',
        session_id: MOCK_SESSION_ID,
        step_id: 'stir',
        objects: ['spoon', 'cup'],
        t_start: 24,
        t_end: 25,
        confidence: 0.88,
        source: 'rule',
      },
    },
  },
  { delayMs: 50, message: { type: 'step_state', states: { stir: 'done' } } },
  {
    delayMs: 300,
    message: {
      type: 'step',
      event: {
        event_id: 'mock-pour-2',
        session_id: MOCK_SESSION_ID,
        step_id: 'pour',
        objects: ['kettle', 'cup'],
        t_start: 29,
        t_end: 30,
        confidence: 0.9,
        source: 'rule',
      },
    },
  },
  {
    delayMs: 50,
    message: {
      type: 'error',
      error: {
        error_id: 'mock-error-perseveration',
        session_id: MOCK_SESSION_ID,
        type: 'perseveration',
        step_id: 'pour',
        t_start: 30,
        t_end: 30,
        evidence: [{ kind: 'step_event', t_start: 29, t_end: 30, event_id: 'mock-pour-2' }],
      },
    },
  },
  { delayMs: 50, message: { type: 'step_state', states: { pour: 'repeat' } } },
  {
    delayMs: 300,
    message: {
      type: 'step',
      event: {
        event_id: 'mock-remove-teabag',
        session_id: MOCK_SESSION_ID,
        step_id: 'remove_teabag',
        objects: ['teabag', 'spoon'],
        t_start: 34,
        t_end: 35,
        confidence: 0.85,
        source: 'rule',
      },
    },
  },
  { delayMs: 50, message: { type: 'step_state', states: { remove_teabag: 'done' } } },
  {
    delayMs: 300,
    message: {
      type: 'error',
      error: {
        error_id: 'mock-error-omission',
        session_id: MOCK_SESSION_ID,
        type: 'omission',
        step_id: 'teabag_in_cup',
        t_start: 40,
        t_end: 40,
        evidence: [{ kind: 'skeleton_replay', t_start: 0, t_end: 40 }],
      },
    },
  },
  { delayMs: 50, message: { type: 'step_state', states: { teabag_in_cup: 'omission' } } },
  { delayMs: 300, message: { type: 'session_end', score: 6.5, flag: true, alert_id: 'mock-alert-1' } },
]

/** Plays `SCRIPT` on timers, scaled by `speed` (the same knob the live WebSocket's
 * `speed` query param uses). Returns a function that cancels the remaining timers. */
export function mockLiveStream(speed: number, onMessage: (message: LiveMessage) => void): () => void {
  let elapsed = 0
  const handles = SCRIPT.map(({ delayMs, message }) => {
    elapsed += delayMs / speed
    return setTimeout(() => onMessage(message), elapsed)
  })
  return () => handles.forEach(clearTimeout)
}

export default mockLiveStream
