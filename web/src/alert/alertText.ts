import type { Alert } from '../contracts.ts'
import { describeError } from '../ui/errorTypes.ts'
import { SUGGESTED_CHECK_LABELS } from './SuggestedChecks.tsx'

function formatTimestamp(t: number): string {
  const minutes = Math.floor(t / 60)
  const seconds = Math.floor(t % 60)
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

function errorLine(error: Alert['errors'][number]): string {
  const step = error.step_id ? error.step_id.replace(/_/g, ' ') : 'this step'
  return `${describeError(error.type, step)} at ${formatTimestamp(error.t_start)}`
}

/** What a nurse's one tap copies into the care record (SPEC section 9, screen 4), so a
 * flagged alert reaches the chart without retyping it (like `handoffText`, T151). Plain
 * text, built from the same evidence the screen shows, always "flagged for review" and
 * "consistent with". */
export function alertText(alert: Alert): string {
  return [
    `Resident: ${alert.resident_id}`,
    'Change flagged for review',
    alert.summary,
    ...alert.errors.map(errorLine),
    ...(alert.patterns ?? []).map((pattern) => `Consistent with: ${pattern.name}`),
    ...alert.suggested_checks.map((check) => SUGGESTED_CHECK_LABELS[check]),
  ].join('\n')
}
