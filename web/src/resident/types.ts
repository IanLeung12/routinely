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
export type Baseline = { mean: number; std: number; threshold: number }

export type Resident = ResidentSummary & {
  scores: ScorePoint[]
  sessions: ResidentSession[]
  care_records: CareRecord[]
  baseline: Baseline
}
