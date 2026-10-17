import type { Alert } from '../contracts.ts'

export const mockAlerts: Alert[] = [{
  alert_id: 'mrs-k-change-1',
  resident_id: 'mrs-k',
  created_at: '2026-10-17T09:00:00Z',
  kind: 'change_flag',
  session_ids: ['mrs-k-tea-1', 'mrs-k-tea-2'],
  errors: [
    {
      error_id: 'mrs-k-omission-1', session_id: 'mrs-k-tea-1',
      type: 'omission', step_id: 'teabag_in_cup', t_start: 42, t_end: 42,
      evidence: [{ kind: 'skeleton_replay', t_start: 40, t_end: 44 }],
    },
    {
      error_id: 'mrs-k-perseveration-1', session_id: 'mrs-k-tea-2',
      type: 'perseveration', step_id: 'pour', t_start: 75, t_end: 75,
      evidence: [{ kind: 'skeleton_replay', t_start: 73, t_end: 77 }],
    },
  ],
  baseline: {
    task_id: 'make_tea', metric: 'error_score', observed: 5,
    baseline_mean: 0.2, baseline_sd: 0.4, baseline_days: 14, threshold: 1.2,
  },
  summary: 'Flagged for review: a teabag step was missed and pouring was repeated across two tea sessions, above the resident’s usual error score.',
  suggested_checks: ['infection_or_uti', 'hydration', 'medication_review', 'cam_screen'],
  patterns: [
    {
      pattern_id: 'sudden_change',
      name: 'Sudden change',
      confidence: 0.82,
      urgency: 'same_shift',
      evidence: ['error score 5.0 vs usual 0.2 over 14 days', '2 errors across the last 2 sessions'],
      checks: ['Rule out acute infection before assuming cognitive decline', 'Check fluid intake over the last 24 hours'],
    },
  ],
  feedback: null,
}]
