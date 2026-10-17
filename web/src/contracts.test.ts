import { expect, it } from 'vitest'
import {
  ERROR_TYPE_VALUES,
  OBJECT_LABEL_VALUES,
  SUGGESTED_CHECK_VALUES,
  type Alert,
  type CaptureFrame,
  type Landmark,
  type StepEvent,
} from './contracts.ts'

// Each literal below is checked against the generated type at build time, so the
// dashboard cannot drift from the pipeline's schemas without `tsc -b` failing.

const landmarks = (count: number): Landmark[] =>
  Array.from({ length: count }, (_, i) => ({ x: 0.3 + i / 100, y: 0.2 + i / 100, z: -0.1 }))

const frame: CaptureFrame = {
  schema_version: 1,
  session_id: 'demo-session-1',
  seq: 1,
  t: 0.5,
  source: 'video',
  poses: [{ landmarks: landmarks(33), score: 0.95 }],
  hands: [{ handedness: 'right', score: 0.91, landmarks: landmarks(21) }],
  objects: [
    { label: 'kettle', confidence: 0.93, box: { x1: 0.56, y1: 0.28, x2: 0.74, y2: 0.61 } },
    { label: 'teabag', confidence: 0.71, box: { x1: 0.41, y1: 0.39, x2: 0.46, y2: 0.45 } },
  ],
}

const step: StepEvent = {
  event_id: 'evt-1',
  session_id: 'demo-session-1',
  step_id: 'teabag_in_cup',
  objects: ['teabag', 'cup'],
  t_start: 12,
  t_end: 14.5,
  confidence: 0.82,
  source: 'rule',
}

const alert: Alert = {
  alert_id: 'alert-1',
  resident_id: 'resident-a',
  created_at: '2026-10-17T09:05:00Z',
  kind: 'change_flag',
  session_ids: ['demo-session-1', 'demo-session-2'],
  errors: [
    {
      error_id: 'err-1',
      session_id: 'demo-session-1',
      type: 'omission',
      step_id: 'fill_kettle',
      t_start: 12,
      t_end: 61,
      evidence: [
        { kind: 'skeleton_replay', t_start: 10, t_end: 20 },
        { kind: 'step_event', t_start: 12, t_end: 14.5, event_id: 'evt-1' },
      ],
    },
  ],
  baseline: {
    task_id: 'make_tea',
    metric: 'errors_per_day',
    observed: 3,
    baseline_mean: 0.2,
    baseline_sd: 0.4,
    baseline_days: 14,
    threshold: 1.5,
  },
  summary: 'Three errors making tea this morning, against 0.2 a day for this resident.',
  suggested_checks: ['infection_or_uti', 'hydration'],
}

it('types a capture frame as skeletons, hands and boxes only', () => {
  expect(frame.poses[0].landmarks).toHaveLength(33)
  expect(frame.hands[0].landmarks).toHaveLength(21)
  expect(frame.objects.map((object) => object.label)).toEqual(['kettle', 'teabag'])
})

it('types a step event and the alert it ends up in', () => {
  expect(step.unclear).toBeUndefined()
  expect(alert.errors[0].evidence.map((ref) => ref.kind)).toEqual([
    'skeleton_replay',
    'step_event',
  ])
  expect(alert.feedback).toBeUndefined()
})

it('exports the error types and detector classes from the spec', () => {
  expect([...ERROR_TYPE_VALUES]).toEqual([
    'omission',
    'sequence',
    'perseveration',
    'substitution',
    'hesitation',
    'abandonment',
  ])
  expect(OBJECT_LABEL_VALUES).toContain('teabag')
  expect(SUGGESTED_CHECK_VALUES).toHaveLength(4)
})
