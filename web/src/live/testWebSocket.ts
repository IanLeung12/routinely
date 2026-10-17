import { vi } from 'vitest'
import type { CaptureFrame, ObjectDetection, StepEvent, TaskError } from '../contracts.ts'
import type { LiveMessage, LiveStep } from './useLiveSession.ts'

/** Stands in for a real WebSocket (SPEC section 9, screen 3): tests drive it by calling
 * `emit`/`fail` on the latest instance instead of opening a real socket. */
export class FakeWebSocket {
  static instances: FakeWebSocket[] = []
  url: string
  closed = false
  onmessage: ((event: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  onclose: (() => void) | null = null

  constructor(url: string) {
    this.url = url
    FakeWebSocket.instances.push(this)
  }

  close() {
    this.closed = true
  }

  emit(message: LiveMessage) {
    this.onmessage?.({ data: JSON.stringify(message) })
  }

  fail() {
    this.onerror?.()
    this.onclose?.()
  }

  static latest(): FakeWebSocket {
    const instance = FakeWebSocket.instances[FakeWebSocket.instances.length - 1]
    if (!instance) {
      throw new Error('no FakeWebSocket instance was created')
    }
    return instance
  }
}

/** Stubs `global.WebSocket` with `FakeWebSocket` and resets its instance list. Call
 * from `beforeEach`; `vi.unstubAllGlobals()` in `afterEach` undoes the stub. */
export function installFakeWebSocket(): void {
  FakeWebSocket.instances = []
  vi.stubGlobal('WebSocket', FakeWebSocket)
}

/** A `session_start` message, defaulting the session/task ids tests don't care about
 * so each call only has to spell out the steps (and whatever id it does care about). */
export function sessionStart(
  steps: LiveStep[],
  overrides: Partial<{ session_id: string; task_id: string }> = {},
): LiveMessage {
  return { type: 'session_start', session_id: 'live-session', task_id: 'tea', steps, ...overrides }
}

/** An `error` message wrapping a `TaskError`, defaulting the fields most tests leave
 * alone (id, session, evidence) so a call only spells out what distinguishes it. */
export function errorMessage(overrides: Partial<TaskError> = {}): LiveMessage {
  return {
    type: 'error',
    error: {
      error_id: 'live-error-1',
      session_id: 'live-session',
      type: 'omission',
      step_id: '',
      t_start: 0,
      t_end: 0,
      evidence: [],
      ...overrides,
    },
  }
}

/** A `step` message wrapping a `StepEvent`, defaulting the fields most tests leave
 * alone so a call only spells out what distinguishes it. */
export function stepMessage(overrides: Partial<StepEvent> = {}): LiveMessage {
  return {
    type: 'step',
    event: {
      event_id: 'e1',
      session_id: 'live-session',
      step_id: '',
      objects: [],
      t_start: 0,
      t_end: 0,
      confidence: 0.9,
      source: 'rule',
      ...overrides,
    },
  }
}

/** A `frame` message wrapping a capture record: nobody and nothing in it by default, the
 * way a camera looks before anyone walks in (landmarks, boxes and a timestamp - never an
 * image, SPEC section 8), so a call only spells out what it is about. */
export function frameMessage(overrides: Partial<CaptureFrame> = {}): LiveMessage {
  return {
    type: 'frame',
    frame: {
      session_id: 'live-session',
      seq: 0,
      t: 0,
      source: 'camera',
      poses: [],
      hands: [],
      objects: [],
      ...overrides,
    },
  }
}

/** One object the detector found, for a frame that has something in view. */
export function detection(overrides: Partial<ObjectDetection> = {}): ObjectDetection {
  return { label: 'cup', confidence: 0.9, box: { x1: 0.4, y1: 0.4, x2: 0.5, y2: 0.5 }, ...overrides }
}
