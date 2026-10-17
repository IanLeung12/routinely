// Generated from pipeline/src/routine_watch/contracts.py by
// `uv run python -m routine_watch.contracts`. Do not edit by hand.
//
// What flows between the pipeline stages and into the dashboard (SPEC sections 6, 7
// and 16). Skeletons, boxes and timestamps only: no raw frames anywhere.
//
// Times inside a session (t, t_start, t_end) are seconds since the session started.
// Wall-clock times (started_at, created_at) are ISO 8601 strings.

/**
 * A change flagged for a human to review (SPEC section 7). Routine Watch flags a change and
 * shows the evidence behind it. It never diagnoses.
 */
export type Alert = {
  alert_id: string
  resident_id: string
  created_at: string
  kind: AlertKind
  /** The sessions behind the flag. A single bad session never alerts. */
  session_ids: string[]
  errors: TaskError[]
  baseline: BaselineComparison
  /** Plain language, written from the detected evidence only. */
  summary: string
  suggested_checks: SuggestedCheck[]
  /** Null until a nurse confirms it or calls it a false alarm. */
  feedback?: AlertFeedback | null
}

/** What the care team said about an alert. Logged, and it moves the threshold. */
export type AlertFeedback = {
  verdict: FeedbackVerdict
  /** Who answered. */
  by: string
  at: string
  note?: string | null
}

/** How urgent the flag is: two bad sessions in 24-48 h, or a slow upward drift. */
export const ALERT_KIND_VALUES = ['change_flag', 'trend'] as const
export type AlertKind = (typeof ALERT_KIND_VALUES)[number]

/** This resident's own history against what just happened (SPEC section 7). */
export type BaselineComparison = {
  task_id: string
  metric: BaselineMetric
  observed: number
  baseline_mean: number
  baseline_sd: number
  /** Days of history the baseline is built from. */
  baseline_days: number
  /** This resident's current threshold, tuned by feedback. */
  threshold: number
}

/** What a baseline comparison measures. */
export const BASELINE_METRIC_VALUES = [
  'error_score',
  'errors_per_day',
  'step_duration_s',
  'step_gap_s',
] as const
export type BaselineMetric = (typeof BASELINE_METRIC_VALUES)[number]

/** An axis-aligned box, normalised to the frame: top-left to bottom-right, 0..1. */
export type BoundingBox = {
  x1: number
  y1: number
  x2: number
  y2: number
}

/**
 * The single per-frame JSONL record (SPEC section 16). The live camera, the pre-recorded
 * fallback, tests and scenarios all feed the pipeline through this one format. The frame itself
 * is dropped after processing.
 */
export type CaptureFrame = {
  /** routine_watch.capture.FRAME_SCHEMA_VERSION when the record was written. */
  schema_version?: number
  session_id: string
  /** Frame counter within the session, from 0. */
  seq: number
  /** Seconds since the session started. */
  t: number
  source: CaptureSource
  /** One per person in frame. Two or more means somebody is assisting. */
  poses: Pose[]
  hands: HandLandmarks[]
  objects: ObjectDetection[]
}

/** Where a capture frame came from. All three produce the same record. */
export const CAPTURE_SOURCE_VALUES = ['camera', 'video', 'synthetic'] as const
export type CaptureSource = (typeof CAPTURE_SOURCE_VALUES)[number]

/** The everyday-action error types in SPEC section 7. */
export const ERROR_TYPE_VALUES = [
  'omission',
  'sequence',
  'perseveration',
  'substitution',
  'hesitation',
  'abandonment',
] as const
export type ErrorType = (typeof ERROR_TYPE_VALUES)[number]

/** What a piece of evidence points at. Never a video clip (SPEC section 8). */
export const EVIDENCE_KIND_VALUES = ['step_event', 'skeleton_replay'] as const
export type EvidenceKind = (typeof EVIDENCE_KIND_VALUES)[number]

/**
 * A pointer to evidence already stored: a step event, or a span of the skeleton replay. Never a
 * video clip (SPEC section 8).
 */
export type EvidenceRef = {
  kind: EvidenceKind
  t_start: number
  t_end: number
  /** Set when kind is step_event: the StepEvent it refers to. */
  event_id?: string | null
}

/** The nurse's answer to an alert, which tunes this resident's threshold. */
export const FEEDBACK_VERDICT_VALUES = ['confirmed', 'false_alarm'] as const
export type FeedbackVerdict = (typeof FEEDBACK_VERDICT_VALUES)[number]

/** One hand. Steps are hand-object interactions (SPEC section 16). */
export type HandLandmarks = {
  handedness: Handedness
  score: number
  /** The 21 MediaPipe hand landmarks, in MediaPipe's own order. */
  landmarks: Landmark[]
}

/** Which hand MediaPipe thinks it is looking at. */
export const HANDEDNESS_VALUES = ['left', 'right'] as const
export type Handedness = (typeof HANDEDNESS_VALUES)[number]

/** One MediaPipe landmark, normalised to the frame: x and y in 0..1, z relative. */
export type Landmark = {
  x: number
  y: number
  z: number
  /** Pose landmarks only; hand landmarks do not report it. */
  visibility?: number | null
}

/**
 * One object box in one frame, from the local detector (SPEC section 6.1). The detector always
 * runs locally from downloaded weights, never hosted inference.
 */
export type ObjectDetection = {
  label: ObjectLabel
  confidence: number
  box: BoundingBox
  /** Stable across frames while the tracker holds the object. */
  track_id?: string | null
}

/** Classes the local detector was trained on (SPEC section 6.1). */
export const OBJECT_LABEL_VALUES = [
  'kettle',
  'cup',
  'teabag',
  'spoon',
  'milk',
  'sugar',
  'hand',
  'pouring',
] as const
export type ObjectLabel = (typeof OBJECT_LABEL_VALUES)[number]

/** One person's body skeleton. */
export type Pose = {
  /** The 33 MediaPipe pose landmarks, in MediaPipe's own order. */
  landmarks: Landmark[]
  score?: number | null
}

/** One attempt at one task by one resident (SPEC section 6.3). */
export type Session = {
  session_id: string
  resident_id: string
  /** The task graph that was being followed, e.g. 'make_tea'. */
  task_id: string
  started_at: string
  /** Null while the session is live. */
  ended_at?: string | null
  /** A second person was in frame. Excluded from the baseline. */
  assisted?: boolean
  /** Weighted sum of this session's errors. Null until the session ends. */
  score?: number | null
}

/** A step of the task, seen happening between two times (SPEC section 6.2). */
export type StepEvent = {
  event_id: string
  session_id: string
  /** The step in the task graph, e.g. 'teabag_in_cup'. */
  step_id: string
  /** Objects the step was done with. */
  objects: ObjectLabel[]
  t_start: number
  t_end: number
  confidence: number
  source: StepSource
  /** Low confidence and the verifier could not resolve it. Never an error. */
  unclear?: boolean
}

/** What decided a step happened: the state rules, or the Gemini verifier. */
export const STEP_SOURCE_VALUES = ['rule', 'verifier'] as const
export type StepSource = (typeof STEP_SOURCE_VALUES)[number]

/** Checks an alert may suggest to the care team (SPEC section 6.4). */
export const SUGGESTED_CHECK_VALUES = [
  'infection_or_uti',
  'hydration',
  'medication_review',
  'cam_screen',
] as const
export type SuggestedCheck = (typeof SUGGESTED_CHECK_VALUES)[number]

/** One everyday-action error found in a session (SPEC section 7). */
export type TaskError = {
  error_id: string
  session_id: string
  type: ErrorType
  /** The step the error is about. Null only when no single step applies. */
  step_id?: string | null
  /** Seconds since the session started. */
  t_start: number
  t_end: number
  evidence: EvidenceRef[]
  /** The resident fixed it straight away: a weaker signal, not a full error. */
  self_corrected?: boolean
}
