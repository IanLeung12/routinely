import type {
  Baseline,
  CareRecord,
  CareRecordKind,
  Resident,
  ResidentSession,
  SessionErrors,
} from '../resident/types.ts'
import { mockResidents } from './residents.ts'

/** The demo's slow-drift resident; other residents have no mock drift assessment. */
export function mockResidentDrift(residentId: string) {
  return residentId === 'mr-chen'
    ? { resident_id: residentId, slope_per_day: 0.7, days: 7, trending: true }
    : null
}

/** Shown when the API is unreachable, so the resident detail screen still has
 * something to demo (SPEC section 8: most normal, one spike, one drift). Mirrors the
 * shape of `GET /residents/{id}`: sessions, care records and the resident's baseline.
 *
 * Scores and baselines are derived from the session errors with the same weights and
 * threshold rule as the pipeline (SPEC section 7), so the chart, the session list and
 * the flag threshold on this screen agree with each other. */

/** routine_watch.scoring.WEIGHTS. Omission and substitution weigh most, hesitation least. */
const WEIGHTS: Record<string, number> = {
  omission: 3,
  substitution: 3,
  sequence: 2,
  perseveration: 2,
  abandonment: 2,
  hesitation: 1,
}

const SELF_CORRECTED_WEIGHT = 0.5

/** routine_watch.change_detection.build_baseline: mean + 2 standard deviations, with a
 * floor on the deviation so a resident with a very flat history isn't flagged by noise. */
const THRESHOLD_K = 2
const MIN_STD = 0.5

type SessionRow = {
  ts: string
  errors: SessionErrors
  duration_s: number
  self_corrected?: number
  assisted?: boolean
}

type CareRow = { ts: string; kind: CareRecordKind; value: number | string; note?: string }

/** Mrs. K is the demo resident: a flat fortnight, then two bad sessions in one morning
 * and evening, which is what a change flag needs (SPEC section 7). */
const SESSIONS: Record<string, SessionRow[]> = {
  'mrs-k': [
    { ts: '2025-12-25T08:10:00+00:00', errors: {}, duration_s: 132 },
    { ts: '2025-12-25T18:05:00+00:00', errors: {}, duration_s: 141 },
    { ts: '2025-12-26T08:22:00+00:00', errors: { hesitation: 1 }, duration_s: 168 },
    { ts: '2025-12-27T08:05:00+00:00', errors: {}, duration_s: 127 },
    { ts: '2025-12-27T18:15:00+00:00', errors: {}, duration_s: 139, self_corrected: 1 },
    { ts: '2025-12-28T08:18:00+00:00', errors: {}, duration_s: 134 },
    { ts: '2025-12-29T08:02:00+00:00', errors: {}, duration_s: 145 },
    { ts: '2025-12-29T18:20:00+00:00', errors: { hesitation: 1 }, duration_s: 158 },
    { ts: '2025-12-30T08:12:00+00:00', errors: {}, duration_s: 130 },
    { ts: '2025-12-31T08:25:00+00:00', errors: {}, duration_s: 136 },
    { ts: '2025-12-31T18:08:00+00:00', errors: {}, duration_s: 142, self_corrected: 1 },
    {
      ts: '2026-01-01T08:12:00+00:00',
      errors: { omission: 1, perseveration: 1 },
      duration_s: 226,
    },
    {
      ts: '2026-01-01T18:02:00+00:00',
      errors: { omission: 1, hesitation: 2 },
      duration_s: 241,
    },
  ],
  'mr-chen': [
    { ts: '2025-12-26T08:05:00+00:00', errors: {}, duration_s: 128 },
    { ts: '2025-12-27T08:12:00+00:00', errors: { hesitation: 1 }, duration_s: 152 },
    { ts: '2025-12-28T08:20:00+00:00', errors: {}, duration_s: 134, self_corrected: 1 },
    { ts: '2025-12-29T08:02:00+00:00', errors: { hesitation: 1 }, duration_s: 147 },
    { ts: '2025-12-29T18:10:00+00:00', errors: { sequence: 1 }, duration_s: 163 },
    { ts: '2025-12-30T08:15:00+00:00', errors: { hesitation: 2 }, duration_s: 171 },
    {
      ts: '2025-12-31T08:08:00+00:00',
      errors: { sequence: 1, hesitation: 1 },
      duration_s: 184,
    },
    {
      ts: '2026-01-01T08:18:00+00:00',
      errors: { omission: 1, sequence: 1, hesitation: 1 },
      duration_s: 212,
    },
  ],
  'mrs-ahmed': [
    { ts: '2025-12-28T08:05:00+00:00', errors: {}, duration_s: 121 },
    { ts: '2025-12-29T08:10:00+00:00', errors: {}, duration_s: 118 },
    { ts: '2025-12-30T08:02:00+00:00', errors: { hesitation: 1 }, duration_s: 139 },
    { ts: '2025-12-31T08:08:00+00:00', errors: {}, duration_s: 124, self_corrected: 1 },
    { ts: '2026-01-01T08:04:00+00:00', errors: {}, duration_s: 120 },
  ],
  'mr-silva': [
    { ts: '2025-12-28T08:15:00+00:00', errors: {}, duration_s: 133 },
    { ts: '2025-12-29T08:06:00+00:00', errors: { hesitation: 1 }, duration_s: 151 },
    { ts: '2025-12-30T08:11:00+00:00', errors: {}, duration_s: 129 },
    {
      ts: '2025-12-31T08:09:00+00:00',
      errors: { omission: 1 },
      duration_s: 147,
      assisted: true,
    },
    { ts: '2026-01-01T08:03:00+00:00', errors: {}, duration_s: 131 },
  ],
}

const CARE_RECORDS: Record<string, CareRow[]> = {
  'mrs-k': [
    { ts: '2025-12-30T08:00:00+00:00', kind: 'temperature', value: 36.8 },
    {
      ts: '2025-12-30T09:00:00+00:00',
      kind: 'med_change',
      value: 'amoxicillin',
      note: 'new antibiotic started',
    },
    { ts: '2025-12-30T20:00:00+00:00', kind: 'fluid_intake', value: 1450 },
    { ts: '2025-12-31T08:00:00+00:00', kind: 'temperature', value: 37.1 },
    { ts: '2025-12-31T20:00:00+00:00', kind: 'fluid_intake', value: 1250 },
    { ts: '2026-01-01T08:00:00+00:00', kind: 'temperature', value: 38.1 },
    { ts: '2026-01-01T20:00:00+00:00', kind: 'fluid_intake', value: 700 },
  ],
  'mr-chen': [
    {
      ts: '2025-12-27T09:00:00+00:00',
      kind: 'med_change',
      value: 'zopiclone',
      note: 'night sedation started',
    },
    { ts: '2025-12-31T08:00:00+00:00', kind: 'temperature', value: 36.6 },
    { ts: '2026-01-01T08:00:00+00:00', kind: 'temperature', value: 36.9 },
    { ts: '2026-01-01T20:00:00+00:00', kind: 'fluid_intake', value: 1400 },
  ],
  'mrs-ahmed': [
    { ts: '2025-12-31T08:00:00+00:00', kind: 'temperature', value: 36.5 },
    { ts: '2026-01-01T08:00:00+00:00', kind: 'temperature', value: 36.7 },
    { ts: '2026-01-01T20:00:00+00:00', kind: 'fluid_intake', value: 1600 },
  ],
  'mr-silva': [
    { ts: '2025-12-31T08:00:00+00:00', kind: 'temperature', value: 36.8 },
    { ts: '2026-01-01T08:00:00+00:00', kind: 'temperature', value: 36.6 },
    { ts: '2026-01-01T20:00:00+00:00', kind: 'fluid_intake', value: 1500 },
  ],
}

function sessionScore(session: ResidentSession): number {
  if (session.assisted) {
    return 0
  }
  const errors = Object.entries(session.errors).reduce(
    (total, [type, count]) => total + (WEIGHTS[type] ?? 0) * (count ?? 0),
    0,
  )
  return errors + SELF_CORRECTED_WEIGHT * session.self_corrected
}

function buildBaseline(scores: number[]): Baseline {
  const mean = scores.reduce((total, score) => total + score, 0) / (scores.length || 1)
  const variance =
    scores.reduce((total, score) => total + (score - mean) ** 2, 0) / (scores.length || 1)
  const std = Math.sqrt(variance)
  return { mean, std, threshold: mean + THRESHOLD_K * Math.max(std, MIN_STD) }
}

/** The mock resident behind `fetchResident`, or null when no mock resident has that id. */
export function mockResidentDetail(residentId: string): Resident | null {
  const summary = mockResidents.find((resident) => resident.id === residentId)
  const rows = SESSIONS[residentId]
  if (summary === undefined || rows === undefined) {
    return null
  }

  const sessions: ResidentSession[] = rows.map((row) => ({
    resident_id: residentId,
    ts: row.ts,
    task: 'tea',
    errors: row.errors,
    self_corrected: row.self_corrected ?? 0,
    duration_s: row.duration_s,
    assisted: row.assisted ?? false,
  }))
  const careRecords: CareRecord[] = (CARE_RECORDS[residentId] ?? []).map((row) => ({
    resident_id: residentId,
    ts: row.ts,
    kind: row.kind,
    value: row.value,
    note: row.note ?? '',
  }))
  const scores = sessions.map((session) => ({ ts: session.ts, score: sessionScore(session) }))

  return {
    id: summary.id,
    name: summary.name,
    room: summary.room,
    status: summary.status,
    scores,
    sessions,
    care_records: careRecords,
    baseline: buildBaseline(scores.map((point) => point.score)),
  }
}
