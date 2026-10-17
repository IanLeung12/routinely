import { useEffect, useState } from 'react'
import { apiUrl } from '../config.ts'
import type { CaptureFrame, StepEvent, TaskError } from '../contracts.ts'
import { mockLiveStream } from './mockLiveStream.ts'

/** Mirrors the pipeline's per-step state (SPEC section 9, screen 3): steps turn green as
 * they're done, flash red for an omission or amber for a repeat/sequence error. */
export type StepState = 'pending' | 'done' | 'omission' | 'repeat' | 'sequence'

/** One step of the session's task graph, for the task map (SPEC section 10). */
export type LiveStep = { id: string; label: string; optional: boolean }

/** The T029 WebSocket protocol, mirroring `contracts/live_message.schema.json`:
 * `pipeline/tests/test_live_contract.py` fails if this union and the schema's `oneOf`
 * stop listing the same messages. */
export type LiveMessage =
  | { type: 'session_start'; session_id: string; task_id: string; steps: LiveStep[] }
  | { type: 'frame'; frame: CaptureFrame }
  | { type: 'step'; event: StepEvent }
  | { type: 'step_state'; states: Record<string, StepState> }
  | { type: 'error'; error: TaskError }
  | { type: 'session_end'; score: number; flag: boolean; alert_id: string | null; errors?: TaskError[] }
  /** Monitoring is off for this resident's room (SPEC section 12): the API sends this
   * instead of a session and closes. */
  | { type: 'paused'; room: string }

export type LiveSessionEnded = { score: number; flag: boolean; alert_id: string | null }

/** `routine_watch.live_camera.CAMERA_UNAVAILABLE`: the close code `/ws/live?source=camera`
 * sends when no camera on this machine could be read (T356), with no message sent first.
 * Distinct from a dropped connection: falling back to mock data would look like a camera
 * is live when there is none, so this gets its own state instead (T394). */
const CAMERA_UNAVAILABLE_CLOSE_CODE = 4503

/** This machine's camera, as `/ws/live?source=camera` takes it: which device (`index`,
 * 0 being the laptop's own) and which task graph to read it against (`task`, a
 * `pipeline/src/routine_watch/tasks/<task>.yaml`). `scripts/camera.sh` starts the stack
 * and prints the dashboard URL that turns this on; without it the screen plays a
 * recorded scenario, which is the demo's own path and the fallback for a camera that
 * fails (SPEC section 10). */
export type LiveCamera = { index: number; task: string }

export type LiveSessionState = {
  steps: LiveStep[]
  frame: CaptureFrame | null
  states: Record<string, StepState>
  errors: TaskError[]
  /** First step event's `t_start` to the latest one's `t_end`, for the end-of-session
   * summary's duration: `session_end` carries no duration of its own. */
  stepSpan: { start: number; end: number } | null
  ended: LiveSessionEnded | null
  /** The room whose monitoring is paused, when the API answered with `paused` instead
   * of a session. Nothing was watched, so the screen explains the pause rather than
   * showing an empty task map. */
  paused: { room: string } | null
  /** Whether any frame so far carried an object box. The recogniser reads steps from
   * hands on objects, so a camera running without the local detector's weights
   * (`DETECTOR_WEIGHTS`) streams skeletons and hands and never a step: the screen says
   * it is waiting for the detector rather than looking stuck (T356). */
  objectsSeen: boolean
  source: 'live' | 'mock'
  /** Set when the socket closed with `CAMERA_UNAVAILABLE_CLOSE_CODE`: this machine's
   * camera could not be opened at all. Shown instead of falling back to mock data,
   * which would misleadingly look like a live session is running (T394). */
  cameraUnavailable: boolean
}

function initialState(source: 'live' | 'mock'): LiveSessionState {
  return {
    steps: [],
    frame: null,
    states: {},
    errors: [],
    stepSpan: null,
    ended: null,
    paused: null,
    objectsSeen: false,
    source,
    cameraUnavailable: false,
  }
}

/** The socket for what the screen is watching, which is also the session's identity: a
 * recorded scenario at `speed`, or a camera and the task graph to read it against. */
function liveSessionUrl(scenario: string, speed: number, camera: LiveCamera | null): string {
  const url = new URL(apiUrl)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  url.pathname = '/ws/live'
  url.search = camera
    ? `?source=camera&camera=${camera.index}&task=${encodeURIComponent(camera.task)}`
    : `?scenario=${encodeURIComponent(scenario)}&speed=${speed}`
  return url.toString()
}

function applyMessage(state: LiveSessionState, message: LiveMessage, source: 'live' | 'mock'): LiveSessionState {
  switch (message.type) {
    case 'session_start':
      return { ...state, steps: message.steps, source }
    case 'frame':
      return {
        ...state,
        frame: message.frame,
        objectsSeen: state.objectsSeen || message.frame.objects.length > 0,
        source,
      }
    case 'step':
      return {
        ...state,
        stepSpan: state.stepSpan
          ? {
              start: Math.min(state.stepSpan.start, message.event.t_start),
              end: Math.max(state.stepSpan.end, message.event.t_end),
            }
          : { start: message.event.t_start, end: message.event.t_end },
        source,
      }
    case 'step_state':
      return { ...state, states: { ...state.states, ...message.states }, source }
    case 'error':
      return { ...state, errors: [...state.errors, message.error], source }
    case 'paused':
      return { ...state, paused: { room: message.room }, source }
    case 'session_end':
      return {
        ...state,
        errors: message.errors ?? state.errors,
        ended: { score: message.score, flag: message.flag, alert_id: message.alert_id },
        source,
      }
    default:
      return state
  }
}

/** Live session screen data (SPEC section 9, screen 3; section 10, demo step 3). Opens the
 * T029 WebSocket for `scenario`, or for `camera` when the screen is pointed at this
 * machine's camera instead (T356) - the API sends the same messages either way, so
 * nothing below this line knows which it is watching. A connect error or a close before
 * any message arrives replays `mockLiveStream` instead, so the screen works before T029
 * lands, when the API is down, and when there is no camera to open. A `paused` message is
 * an answer, not a failure: monitoring is off for the room, so the state keeps `paused`
 * and never falls back to mock data, which would show a session nobody is watching.
 * `retry` lets the paused screen reconnect once a nurse turns the room's monitoring back
 * on, instead of needing a full page reload (T266). */
export function useLiveSession(
  scenario: string,
  speed = 1,
  camera: LiveCamera | null = null,
): LiveSessionState & { retry: () => void } {
  const url = liveSessionUrl(scenario, speed, camera)
  const [renderedFor, setRenderedFor] = useState(url)
  const [state, setState] = useState<LiveSessionState>(() => initialState('live'))
  const [attempt, setAttempt] = useState(0)

  /** A different socket means a different session - another scenario, another speed, the
   * camera instead of a recording - so reset during render rather than in the effect
   * below, so switching sessions doesn't flash the old one's last frame for an extra
   * commit. See react.dev, "Adjusting state when a prop changes". */
  if (url !== renderedFor) {
    setRenderedFor(url)
    setState(initialState('live'))
  }

  function retry() {
    setState(initialState('live'))
    setAttempt((previous) => previous + 1)
  }

  useEffect(() => {
    let cancelled = false
    let receivedData = false
    let paused = false
    let stopMock: (() => void) | null = null

    function fallBackToMock() {
      if (cancelled || paused || stopMock) {
        return
      }
      setState(initialState('mock'))
      stopMock = mockLiveStream(speed, (message) => {
        if (!cancelled) {
          setState((prev) => applyMessage(prev, message, 'mock'))
        }
      })
    }

    const socket = new WebSocket(url)

    socket.onmessage = (event) => {
      receivedData = true
      try {
        const message = JSON.parse(event.data as string) as LiveMessage
        if (message.type === 'paused') {
          paused = true
        }
        setState((prev) => applyMessage(prev, message, 'live'))
      } catch {
        // Malformed message from the pipeline: ignore it, keep the connection open.
      }
    }
    socket.onerror = () => {
      if (!receivedData) {
        fallBackToMock()
      }
    }
    socket.onclose = (event?: { code?: number }) => {
      if (receivedData) {
        return
      }
      if (event?.code === CAMERA_UNAVAILABLE_CLOSE_CODE) {
        setState((prev) => ({ ...prev, cameraUnavailable: true }))
        return
      }
      fallBackToMock()
    }

    return () => {
      cancelled = true
      socket.close()
      stopMock?.()
    }
  }, [url, speed, attempt])

  return { ...state, retry }
}

export default useLiveSession
