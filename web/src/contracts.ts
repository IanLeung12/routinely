// Generated from pipeline/src/routine_watch/contracts.py by
// `uv run python -m routine_watch.contracts`. Do not edit by hand.
//
// What flows between the pipeline stages and into the dashboard (SPEC sections 6, 7
// and 16), plus the route payloads the dashboard reads through these types rather
// than a copy of its own. Skeletons, boxes and timestamps only: no raw frames
// anywhere.
//
// Times inside a session (t, t_start, t_end) are seconds since the session started.
// Wall-clock times (started_at, created_at) are ISO 8601 strings.

/**
 * A change flagged for a human to review (SPEC section 7). Routinely flags a change and shows
 * the evidence behind it. It never diagnoses.
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
  /**
   * The patterns this change is consistent with, best first (at most 3). Empty means a change
   * was detected with no clear pattern.
   */
  patterns?: PatternMatch[]
  /** Null until a nurse confirms it or calls it a false alarm. */
  feedback?: AlertFeedback | null
  /**
   * Errors and sessions per part of the day over the two weeks before the alert, one entry per
   * bucket: the visible evidence behind an evening-only pattern (SPEC section 7.5). Read off
   * the resident's own session history by the route that serves the alert
   * (`routine_watch.api_alerts`), so it is null on a stored record and on a resident with no
   * sessions in that window.
   */
  errors_by_time_of_day?: TimeOfDayErrors[] | null
}

/** What the care team said about an alert. Logged, and it moves the threshold. */
export type AlertFeedback = {
  verdict: FeedbackVerdict
  /** Who answered. */
  by: string
  at: string
  note?: string | null
  /**
   * The optional answer to "what was it?" (SPEC section 5, MVP 8): a pattern_id from the
   * pattern library, 'other' for a cause the library has no pattern for, or null when nobody
   * said.
   */
  cause?: string | null
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

/**
 * One answer a nurse gave on one of this resident's alerts (SPEC MVP 8).
 * `routine_watch.feedback.FeedbackStore.history`'s row: one per alert, because answering an
 * alert again replaces its answer rather than piling a second one on top. Not `AlertFeedback`,
 * which is the verdict as the alert itself carries it: this is the same answer read from the
 * resident's side, with the alert it was about named and the `by` nobody logs in to set left
 * off.
 */
export type FeedbackAnswer = {
  /** The alert this answer was given on. */
  alert_id: string
  verdict: FeedbackVerdict
  /**
   * The answer to "what was it?" (SPEC section 5, MVP 8): a pattern_id from the pattern
   * library, 'other' for a cause the library has no pattern for, or null when nobody said.
   * Always sent, often null.
   */
  cause: string | null
  /** When the nurse answered (wall clock). */
  at: string
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

/**
 * The shift handoff (`GET /handoff`, SPEC section 9). What the nurse coming on shift missed:
 * one row per resident for the window, rows worth a look first, quiet ones listed too so the
 * unit is visibly looked at rather than silently skipped. `paused` is every room nobody was
 * watching.
 */
export type Handoff = {
  /** How far back the window reaches. */
  window_hours: number
  /** Every resident, the ones needing review first. */
  residents: HandoffResident[]
  /** Rooms whose monitoring is paused right now. */
  paused?: PausedRoom[]
  /** Plain language, written from the window's own numbers (`Explainer`). */
  summary: string
}

/**
 * One resident's line of the shift handoff (SPEC section 9). `flags` counts the sessions inside
 * the window that scored above this resident's own threshold, which is the evidence a flag
 * rests on rather than the flag itself: one bad session never alerts (SPEC section 7).
 * `pending_review` counts the alerts raised for them that nobody has given a verdict on yet.
 * `previous_flags` is the same count for the window before this one, so a nurse coming on shift
 * can read whether this resident is getting better or worse rather than only a number.
 * `unclear_sessions` counts what the window could *not* read: sessions in this resident's room
 * the capture was too unclear to score, which are left out of the scored history altogether
 * (SPEC section 12, T342) and so would otherwise make a blocked or badly lit camera read as a
 * quiet room. It is about the camera's view, never about the resident. `previous_flags` and
 * `unclear_sessions` default to 0 for the same reason `monitoring_paused` does: they were added
 * after the payload shipped, so an older or trimmed handoff still validates (T292, T311) and a
 * dashboard reading it knows "no comparison sent" from "none last shift".
 */
export type HandoffResident = {
  resident_id: string
  name: string
  /**
   * The resident's room, so a handed-over line says where to go (SPEC section 9) and the
   * printed or pasted handoff is usable on its own.
   */
  room: string
  /** Sessions in the window above this resident's bar. */
  flags: number
  /**
   * The same count for the window just before this one (`[now - 2 x hours, now - hours)`),
   * measured against the same bar, so a row can say more, fewer or the same as last shift. A
   * count, never a verdict.
   */
  previous_flags?: number
  /** Alerts in the window with no verdict yet. */
  pending_review: number
  /**
   * Sessions in this resident's room the capture was too unclear to score in the window (SPEC
   * section 12). They are in nobody's history, so without this a camera that cannot see reads
   * as a quiet room. A count about the camera view, never about the resident.
   */
  unclear_sessions?: number
  /**
   * Their error score is on a slow rise. Read over their whole history, not this window: a
   * drift takes weeks to show (SPEC section 7.5).
   */
  trending: boolean
  /**
   * Their room's monitoring is paused (SPEC section 12), so a quiet row means nobody was
   * looking rather than nothing happened.
   */
  monitoring_paused?: boolean
}

/** One MediaPipe landmark, normalised to the frame: x and y in 0..1, z relative. */
export type Landmark = {
  x: number
  y: number
  z: number
  /** Pose landmarks only; hand landmarks do not report it. */
  visibility?: number | null
}

/**
 * One logged change to a room's switch (SPEC section 12). A pause or a resume, with who made it
 * and when: `routine_watch.monitoring` appends one of these every time the switch really moves,
 * so a camera going quiet is accountable rather than silent. A tap that leaves the room as it
 * was is not a change and is not logged.
 */
export type MonitoringChange = {
  /** False is a pause, true a resume. */
  on: boolean
  /**
   * Who made the change. The MVP has no nurse logins, so every change is one anonymous nurse's.
   */
  by: string
  /** When the change was made (wall clock). */
  at: string
}

/**
 * The ghost layer beside `SessionReplay` (`GET /residents/{id}/normal_replay`). The same window
 * from one of this resident's normal sessions, for the evidence view to lay their usual routine
 * under the session being reviewed (SPEC section 9, screen 4). Asked about the resident rather
 * than a session, because the point is what they normally do and not one attempt; the frames
 * come back under a normal session's own id (`routine_watch.evidence`), never the reviewed
 * session's.
 */
export type NormalReplay = {
  resident_id: string
  /**
   * The window's frames from a normal session, oldest first. Skeletons, boxes and timestamps
   * only, like `SessionReplay.frames`.
   */
  frames: CaptureFrame[]
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

/**
 * Classes the local detector reports (SPEC section 6.1). Making tea first, then taking
 * medication with water (SPEC nice-to-have 4), then making a protein shake (Ian's own routine),
 * then the two classes every task shares. A task graph says which of these count for which
 * step, so a new task adds classes here and a `tasks/<name>.yaml` file and nothing else. A
 * class the running weights were not trained on is simply never reported, and
 * `routine_watch.detector.label_for` drops a class it does not know, so the two lists may land
 * one training run apart.
 */
export const OBJECT_LABEL_VALUES = [
  'kettle',
  'cup',
  'teabag',
  'spoon',
  'milk',
  'sugar',
  'pill_bottle',
  'pill_organiser',
  'glass',
  'water_jug',
  'shaker',
  'protein_tub',
  'scoop',
  'hand',
  'pouring',
] as const
export type ObjectLabel = (typeof OBJECT_LABEL_VALUES)[number]

/**
 * One entry of the pattern library (`GET /patterns`, SPEC section 7.5). The library held as
 * data (`routine_watch.patterns_library.LIBRARY`) as the route reads it out: what the rule
 * looks for and how much each signal counts, the time profile it follows, what to rule out, how
 * soon somebody should look, and where the pattern comes from. A cited rules library anybody
 * can audit, and nothing about a resident - the scored answer for one change is `PatternMatch`.
 * The scoring machinery stays behind the route: which signals a pattern is defined by, the
 * care-record context that raises or lowers it, its confidence ceiling.
 * `routine_watch.patterns` owns all of that, so a reader gets the rule rather than the
 * arithmetic.
 */
export type PatternLibraryEntry = {
  /** The pattern in the library, e.g. 'sudden_change'. */
  pattern_id: string
  /** How the pattern is shown to a nurse. */
  name: string
  /**
   * Signal name -> weight: what the rule looks for and how much each signal counts. The names
   * are `routine_watch.patterns.SIGNALS`.
   */
  signals: Record<string, number>
  time_profile: PatternTimeProfile
  /**
   * What to rule out: a shared SuggestedCheck where one fits, otherwise the pattern's own
   * wording, exactly as `PatternMatch.checks` carries it.
   */
  checks: (SuggestedCheck | string)[]
  urgency: PatternUrgency
  /**
   * Where the pattern comes from: a SPEC section, a clinical screen, a citation. Never empty -
   * an uncited rule is not a pattern (SPEC section 7.5).
   */
  source: string
}

/**
 * One pattern a flagged change is consistent with (SPEC section 7.5). A flag says *something*
 * changed; these say what kind of change it looks like, so the care team knows what to rule out
 * first. Scored by deterministic rules over features the pipeline already has
 * (`routine_watch.patterns`) against a library of patterns held as data
 * (`routine_watch.patterns_library`), so the wording is always "consistent with ... - consider
 * ruling out ...", and an empty list is a real answer: a change was detected with no clear
 * pattern.
 */
export type PatternMatch = {
  /** The pattern in the library, e.g. 'sudden_change'. */
  pattern_id: string
  /** How the pattern is shown to a nurse. */
  name: string
  confidence: number
  urgency: PatternUrgency
  /**
   * Plain-language lines read off the features, e.g. 'omissions up to 1.0 a session from 0.0'.
   */
  evidence: string[]
  /**
   * What to rule out, from the library: a shared SuggestedCheck where one fits, otherwise the
   * pattern's own wording.
   */
  checks: (SuggestedCheck | string)[]
}

/**
 * How long a change of this kind takes to show up (SPEC section 7.5).
 * `routine_watch.patterns_library.TimeProfile` as `GET /patterns` serves it: a step change over
 * days and a drift over weeks are different patterns, so the window a change has been building
 * for is part of what the library says to look for.
 */
export type PatternTimeProfile = {
  /**
   * The onset window in days, earliest first: how long a change of this kind is expected to
   * have been building.
   */
  onset_days: [number, number]
  /** How far outside the onset window still counts for anything. */
  tolerance_days: number
  /**
   * The phrase a nurse reads, kept next to the numbers it describes, e.g. 'a step change within
   * 1-3 days'.
   */
  note: string
}

/** How soon a pattern wants a human to look (SPEC section 7.5). */
export const PATTERN_URGENCY_VALUES = ['routine', 'next_round', 'same_shift', 'urgent'] as const
export type PatternUrgency = (typeof PATTERN_URGENCY_VALUES)[number]

/** A room a nurse has paused, and whose it is (SPEC section 12). */
export type PausedRoom = {
  room: string
  resident_id: string
  name: string
}

/**
 * A person's replay library (`GET /people/{person_id}/replays`, SPEC section 17). Every attempt
 * of theirs that had an error and is still inside the retention window, newest first, plus the
 * one normal session kept beside them: SPEC section 17's "compare with the person's normal"
 * needs something to compare against, and a clean session is kept for that and not listed as
 * one of the attempts to review.
 */
export type PersonReplays = {
  person_id: string
  /**
   * Their sessions that had at least one error, newest first, after any `type` and `since`
   * filter.
   */
  replays: ReplaySummary[]
  /**
   * Their most recent session with no errors, to compare the others against. Null until they
   * have had one.
   */
  normal: ReplaySummary | null
}

/** One person's body skeleton. */
export type Pose = {
  /** The 33 MediaPipe pose landmarks, in MediaPipe's own order. */
  landmarks: Landmark[]
  score?: number | null
}

/**
 * One kept replay in full (`GET /replays/{session_id}`, SPEC sections 17 and 8). The skeleton
 * of an attempt that went wrong, kept so a person and their supervisors can look back and judge
 * for themselves: poses, hand landmarks, object boxes and timestamps, thinned to about ten a
 * second, and never video. `markers` are its errors, so the viewer can jump between them.
 */
export type Replay = {
  session_id: string
  /**
   * Whose session it was. `Session.resident_id` under the name SPEC section 17 gives it: a
   * person watches their own routine, supervisors look with them.
   */
  person_id: string
  task_id: string
  started_at: string
  /** How long the attempt took, in seconds. */
  duration_s: number
  /** Errors found in the session, self-corrected ones included. */
  error_count: number
  /** Which kinds of error it had, each named once, in the order they happened. */
  error_types: ErrorType[]
  /**
   * This is the person's most recent session with no errors at all, kept as the comparison to
   * look at the others against rather than because anything went wrong.
   */
  normal?: boolean
  /** The session's errors, oldest first: where to jump to in `frames`. */
  markers: ReplayMarker[]
  /**
   * The session's frames, oldest first. Skeletons, boxes and timestamps only: the image each
   * was read from was dropped when it was processed.
   */
  frames: CaptureFrame[]
}

/**
 * One error inside a stored replay: what a viewer jumps to (SPEC section 17). The error's own
 * window in session time, so whoever is looking back at the attempt goes straight to the moment
 * rather than watching the whole thing. It carries the `error_id`, type, step and times of the
 * `TaskError` it was made from, so the marker and the alert's error list name the same moment;
 * the frames it points into are the replay's own.
 */
export type ReplayMarker = {
  error_id: string
  type: ErrorType
  /** The step the error is about. Null only when no single step applies. */
  step_id?: string | null
  /** Seconds since the session started. */
  t_start: number
  t_end: number
  /** The person put it right themselves: still worth seeing, not a full error. */
  self_corrected?: boolean
}

/**
 * One kept replay, as a row of a person's replay library (SPEC section 17). What `GET
 * /people/{person_id}/replays` lists: enough to pick an attempt to look at - when it was, how
 * long it took, how many errors and of which kinds - without carrying a single frame. The
 * frames and the markers come one session at a time (`Replay`).
 */
export type ReplaySummary = {
  session_id: string
  /**
   * Whose session it was. `Session.resident_id` under the name SPEC section 17 gives it: a
   * person watches their own routine, supervisors look with them.
   */
  person_id: string
  task_id: string
  started_at: string
  /** How long the attempt took, in seconds. */
  duration_s: number
  /** Errors found in the session, self-corrected ones included. */
  error_count: number
  /** Which kinds of error it had, each named once, in the order they happened. */
  error_types: ErrorType[]
  /**
   * This is the person's most recent session with no errors at all, kept as the comparison to
   * look at the others against rather than because anything went wrong.
   */
  normal?: boolean
}

/**
 * One resident's slow trend (`GET /residents/{id}/drift`, SPEC section 8). What the drift card
 * on the resident screen draws: how fast this resident's daily error score is rising, over how
 * many days of their own history, read with a robust slope so one bad day cannot tilt it
 * (`routine_watch.drift`). A slow drift is flagged for review on its own terms, separately from
 * a sudden change (SPEC section 7.5); `trending` is the whole judgement, and it is about the
 * trend, never about the resident.
 */
export type ResidentDrift = {
  resident_id: string
  /** Daily error score gained per day. Negative means improving. */
  slope_per_day: number
  /**
   * Days this resident has sessions on. Counted, not spanned: a gap cannot satisfy the minimum
   * history a trend needs.
   */
  days: number
  /**
   * A rise worth a look: enough days of history and a slope above `routine_watch.drift.drift`'s
   * minimum. False is a real answer, not 'unknown'.
   */
  trending: boolean
}

/**
 * What this resident's nurses have said (`GET /residents/{id}/feedback`). The record behind the
 * feedback loop (SPEC Nice to have 8), which until this route only showed up in how her next
 * alert was ranked: every answer on her alerts newest first, the pattern weights those answers
 * add up to, and the name the library shows each pattern id named here under, so the card
 * reading this never keeps its own copy of the library. All three are always sent and all three
 * can be empty - nobody having answered yet is a real answer, not a gap.
 */
export type ResidentFeedback = {
  resident_id: string
  /** One row per answered alert, newest first. Empty until a nurse answers. */
  answers: FeedbackAnswer[]
  /**
   * Pattern id -> confidence multiplier, one entry per pattern her nurses have answered about
   * (`routine_watch.feedback.FeedbackStore.pattern_weights`). A pattern missing here is
   * unweighted, which is read as 1.0.
   */
  pattern_weights: Record<string, number>
  /**
   * Pattern id -> how the pattern library shows it, for every id named above that the library
   * knows. 'other' is a real answer with no pattern to name, so it has no entry here.
   */
  pattern_names: Record<string, string>
}

/**
 * The chip on a resident's overview row (SPEC section 9, screen 1): nothing to say, worth a
 * look, or a change flagged for review.
 */
export const RESIDENT_STATUS_VALUES = ['normal', 'watch', 'flagged'] as const
export type ResidentStatus = (typeof RESIDENT_STATUS_VALUES)[number]

/**
 * One row of the unit overview (`GET /residents`, SPEC section 9, screen 1). Six fields and no
 * history: the resident, their status chip, the pattern their change is consistent with and the
 * sparkline. `routine_watch.api._SUMMARY_FIELDS` is this list, because the row is this much of
 * the resident below.
 */
export type ResidentSummary = {
  id: string
  name: string
  room: string
  status: ResidentStatus
  /**
   * Null for a normal resident, and for a change no pattern fits: an empty answer is a real one
   * (SPEC section 7.5).
   */
  top_pattern: TopPattern | null
  /** One point per session, oldest first. */
  scores: ScorePoint[]
}

/** One point of a resident's sparkline: a session's score, and when it ran. */
export type ScorePoint = {
  /** When the session started (wall clock). */
  ts: string
  /** Weighted sum of that session's errors. */
  score: number
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

/**
 * One window of one session's skeleton replay (`GET /sessions/{id}/replay`). What "open
 * evidence" plays beside an alert (SPEC section 8): the capture frames around the moment an
 * error happened - poses, hand landmarks, object boxes and their timestamps, never video. The
 * window asked for is padded, clipped to the session and thinned to the requested frame rate
 * (`routine_watch.evidence`), so what comes back is whatever frames fall inside it rather than
 * the window itself.
 */
export type SessionReplay = {
  /**
   * The session asked about. Every frame carries it too, so a player holding frames alone still
   * knows what it is showing.
   */
  session_id: string
  /**
   * The window's frames, oldest first. Skeletons, boxes and timestamps only: the image each was
   * read from was dropped when it was processed.
   */
  frames: CaptureFrame[]
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

/**
 * Which part of a day a session started in (SPEC section 7.5). The three parts a nurse reads
 * off a shift rather than clock hours, so "errors only late in the day" is something an alert
 * can show rather than only say: morning before noon, afternoon until 17:00, evening from 17:00
 * on.
 */
export const TIME_OF_DAY_VALUES = ['morning', 'afternoon', 'evening'] as const
export type TimeOfDay = (typeof TIME_OF_DAY_VALUES)[number]

/**
 * One part of the day, counted over the two weeks behind an alert (SPEC section 7.5).
 * `sessions` is how many sessions this resident started in that part of the day and `errors`
 * how many errors those sessions had between them, so a reader can tell "three bad evenings"
 * from "one evening, three errors". Both are counts over this resident's own history, not
 * rates: the strip is evidence a nurse reads, and the rate is already in the pattern's own
 * evidence lines.
 */
export type TimeOfDayErrors = {
  bucket: TimeOfDay
  /** Sessions started in this part of the day, assisted ones left out. */
  sessions: number
  /**
   * Errors in those sessions, self-corrected slips left out - the same count the session score
   * and this resident's normal are built from (SPEC section 7).
   */
  errors: number
}

/**
 * The pattern chip on a resident's row (SPEC section 9, screen 1). The best-scoring
 * `PatternMatch` for this resident's change, cut down to what a row shows: what it is
 * consistent with and how soon somebody should look.
 */
export type TopPattern = {
  /** The pattern in the library, e.g. 'sudden_change'. */
  pattern_id: string
  /** How the pattern is shown to a nurse. */
  name: string
  urgency: PatternUrgency
}
