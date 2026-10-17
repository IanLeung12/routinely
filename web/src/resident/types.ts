import type { ErrorType } from '../contracts.ts'
import type { ResidentSummary } from '../overview/types.ts'

/** Resident detail (SPEC section 9, screen 2): the shape `GET /residents/{id}` serves,
 * which is the unit-overview summary plus this resident's sessions, care records and
 * their own baseline. */
export type ScorePoint = { ts: string; score: number }

/** Error counts for one session, keyed by the error types in SPEC section 7. */
export type SessionErrors = Partial<Record<ErrorType, number>>

export type ResidentSession = {
  resident_id: string
  ts: string
  task: string
  errors: SessionErrors
  /** Slips the resident fixed straight away: a weaker signal, not a full error. */
  self_corrected: number
  duration_s: number
  /** A second person was in frame, so the session is excluded from the baseline. */
  assisted: boolean
}

/** Context a nurse reads next to the chart, not something the pipeline detects. */
export type CareRecordKind = 'temperature' | 'fluid_intake' | 'med_change'

export type CareRecord = {
  resident_id: string
  ts: string
  kind: CareRecordKind
  value: number | string
  note: string
}

/** This resident's own normal, and the score a session has to pass to count towards a flag. */
export type Baseline = {
  mean: number
  std: number
  threshold: number
  /** How long one of their sessions usually runs and how many errors it usually has,
   * averaged by the pipeline over the early window their baseline is anchored to
   * (`routine_watch.demo`) - not their whole history, which the change being flagged
   * would drag up along with it. Absent when they have no early sessions of their own. */
  usual_duration_s?: number
  usual_errors?: number
}

export type Resident = ResidentSummary & {
  scores: ScorePoint[]
  sessions: ResidentSession[]
  care_records: CareRecord[]
  baseline: Baseline
}

/** What this resident's nurses have said and the pattern ranking it changed
 * (`GET /residents/{id}/feedback`, SPEC Nice to have 8): one `FeedbackAnswer` row per
 * answered alert (answering one again replaces its row), the confidence multipliers
 * those answers add up to - anything missing is unweighted, i.e. 1.0 - and how the
 * pipeline's library names every pattern id they mention, so the card never keeps its
 * own copy of the library.
 *
 * Generated from the pipeline's contracts (`web/src/contracts.ts`) and re-exported
 * here with the rest of the resident screen's shapes, so a field added on either side
 * alone fails the dashboard's build. */
export type { FeedbackAnswer, ResidentFeedback } from '../contracts.ts'
