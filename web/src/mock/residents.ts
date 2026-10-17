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
    scores: [
      { ts: '2025-12-29T09:00:00+00:00', score: 0.13 },
      { ts: '2025-12-30T09:00:00+00:00', score: 0.1 },
      { ts: '2025-12-31T09:00:00+00:00', score: 0.12 },
      { ts: '2026-01-01T09:00:00+00:00', score: 0.11 },
    ],
  },
]
