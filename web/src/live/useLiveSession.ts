import { useEffect, useState } from 'react'
import { apiUrl } from '../config.ts'
import type { CaptureFrame, StepEvent, TaskError } from '../contracts.ts'
import { mockLiveStream } from './mockLiveStream.ts'

/** Mirrors the pipeline's per-step state (SPEC section 9, screen 3): steps turn green as
 * they're done, flash red for an omission or amber for a repeat/sequence error. */
export type StepState = 'pending' | 'done' | 'omission' | 'repeat' | 'sequence'

/** One step of the session's task graph, for the task map (SPEC section 10). */
export type LiveStep = { id: string; label: string; optional: boolean }

/** The T029 WebSocket protocol, verbatim. */
export type LiveMessage =
  | { type: 'session_start'; session_id: string; task_id: string; steps: LiveStep[] }
  | { type: 'frame'; frame: CaptureFrame }
  | { type: 'step'; event: StepEvent }
  | { type: 'step_state'; states: Record<string, StepState> }
  | { type: 'error'; error: TaskError }
  | { type: 'session_end'; score: number; flag: boolean; alert_id: string | null; errors?: TaskError[] }
  /** Monitoring is off for this resident's room (SPEC section 12): the API sends this
   * instead of a session and closes. Web-side only; the pipeline's `contracts/` cover
   * session messages, not this one. */
  | { type: 'paused'; room: string }

export type LiveSessionEnded = { score: number; flag: boolean; alert_id: string | null }

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
  source: 'live' | 'mock'
}

function initialState(source: 'live' | 'mock'): LiveSessionState {
  return { steps: [], frame: null, states: {}, errors: [], stepSpan: null, ended: null, paused: null, source }
}

function liveSessionUrl(scenario: string, speed: number): string {
  const url = new URL(apiUrl)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  url.pathname = '/ws/live'
  url.search = `?scenario=${encodeURIComponent(scenario)}&speed=${speed}`
  return url.toString()
}

function applyMessage(state: LiveSessionState, message: LiveMessage, source: 'live' | 'mock'): LiveSessionState {
  switch (message.type) {
    case 'session_start':
      return { ...state, steps: message.steps, source }
    case 'frame':
      return { ...state, frame: message.frame, source }
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
 * T029 WebSocket for `scenario`; a connect error or a close before any message arrives
 * replays `mockLiveStream` instead, so the screen works before T029 lands and when the
 * API is down. A `paused` message is an answer, not a failure: monitoring is off for the
 * room, so the state keeps `paused` and never falls back to mock data, which would show a
 * session nobody is watching. */
export function useLiveSession(scenario: string, speed = 1): LiveSessionState {
  const sessionKey = `${scenario}:${speed}`
  const [renderedFor, setRenderedFor] = useState(sessionKey)
  const [state, setState] = useState<LiveSessionState>(() => initialState('live'))

  /** `scenario`/`speed` changing means a different session: reset during render rather
   * than in the effect below, so switching sessions doesn't flash the old one's last
   * frame for an extra commit. See react.dev, "Adjusting state when a prop changes". */
  if (sessionKey !== renderedFor) {
    setRenderedFor(sessionKey)
    setState(initialState('live'))
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

    const socket = new WebSocket(liveSessionUrl(scenario, speed))

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
    socket.onclose = () => {
      if (!receivedData) {
        fallBackToMock()
      }
    }

    return () => {
      cancelled = true
      socket.close()
      stopMock?.()
    }
  }, [scenario, speed])

  return state
}

export default useLiveSession
