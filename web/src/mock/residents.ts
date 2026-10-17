import type { ResidentSummary } from '../overview/types.ts'

/** Shown when the API is unreachable, so the dashboard still has something to demo
 * (SPEC section 8: most normal, one spike, one drift). Mirrors the shape of the demo
 * residents the pipeline serves from `GET /residents`. */
export const mockResidents: ResidentSummary[] = [
  {
    id: 'mrs-k',
    name: 'Mrs. K',
    room: '204',
    status: 'flagged',
    top_pattern: { pattern_id: 'sudden_change', name: 'Sudden change (delirium pattern)', urgency: 'same_shift' },
    consent: { given_by: 'Substitute decision-maker (daughter)', on: '2026-09-28' },
    scores: [
      { ts: '2025-12-29T09:00:00+00:00', score: 0.12 },
      { ts: '2025-12-30T09:00:00+00:00', score: 0.15 },
      { ts: '2025-12-31T09:00:00+00:00', score: 0.14 },
      { ts: '2026-01-01T09:00:00+00:00', score: 0.78 },
    ],
  },
  {
    id: 'mr-chen',
    name: 'Mr. Chen',
    room: '211',
    status: 'watch',
    top_pattern: { pattern_id: 'slow_drift', name: 'Slow drift (cognitive decline pattern)', urgency: 'routine' },
    consent: { given_by: 'Resident', on: '2026-08-14' },
    scores: [
      { ts: '2025-12-29T09:00:00+00:00', score: 0.1 },
      { ts: '2025-12-30T09:00:00+00:00', score: 0.18 },
      { ts: '2025-12-31T09:00:00+00:00', score: 0.27 },
      { ts: '2026-01-01T09:00:00+00:00', score: 0.41 },
    ],
  },
  {
    id: 'mrs-ahmed',
    name: 'Mrs. Ahmed',
    room: '108',
    status: 'normal',
    top_pattern: null,
    consent: { given_by: 'Substitute decision-maker (son)', on: '2026-07-02' },
    scores: [
      { ts: '2025-12-29T09:00:00+00:00', score: 0.08 },
      { ts: '2025-12-30T09:00:00+00:00', score: 0.11 },
      { ts: '2025-12-31T09:00:00+00:00', score: 0.09 },
      { ts: '2026-01-01T09:00:00+00:00', score: 0.1 },
    ],
  },
  {
    id: 'mr-silva',
    name: 'Mr. Silva',
    room: '117',
    status: 'normal',
    top_pattern: null,
    scores: [
      { ts: '2025-12-29T09:00:00+00:00', score: 0.13 },
      { ts: '2025-12-30T09:00:00+00:00', score: 0.1 },
      { ts: '2025-12-31T09:00:00+00:00', score: 0.12 },
      { ts: '2026-01-01T09:00:00+00:00', score: 0.11 },
    ],
  },
  {
    id: 'mr-nguyen',
    name: 'Mr. Nguyen',
    room: '126',
    status: 'watch',
    top_pattern: {
      pattern_id: 'evening_worsening',
      name: 'Evening-only worsening (sundowning pattern)',
      urgency: 'routine',
    },
    scores: [
      { ts: '2025-12-31T08:00:00+00:00', score: 0 },
      { ts: '2025-12-31T18:00:00+00:00', score: 5 },
      { ts: '2026-01-01T08:00:00+00:00', score: 0 },
      { ts: '2026-01-01T18:00:00+00:00', score: 5 },
    ],
  },
  {
    id: 'mrs-patel',
    name: 'Mrs. Patel',
    room: '132',
    status: 'watch',
    top_pattern: { pattern_id: 'motor_slowing', name: 'Motor slowing / medication effect', urgency: 'next_round' },
    scores: [
      { ts: '2025-12-29T08:00:00+00:00', score: 0 },
      { ts: '2025-12-30T08:00:00+00:00', score: 1 },
      { ts: '2025-12-31T08:00:00+00:00', score: 0 },
      { ts: '2026-01-01T08:00:00+00:00', score: 1 },
    ],
  },
]
