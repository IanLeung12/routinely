import type { ErrorType } from '../contracts.ts'
import { ERROR_TYPE_LABEL } from '../ui/errorTypes.ts'
import type { CareRecord, SessionErrors } from './types.ts'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** The pipeline writes UTC timestamps, so the dashboard reads them back in UTC: the
 * same screen everywhere, and tests that don't depend on the machine's timezone. */
function parse(ts: string): Date | null {
  const date = new Date(ts)
  return Number.isNaN(date.getTime()) ? null : date
}

/** 'YYYY-MM-DD' in UTC, the day key the heat calendar wants. Null if `ts` isn't a date. */
export function utcDate(ts: string): string | null {
  return parse(ts)?.toISOString().slice(0, 10) ?? null
}

/** '1 Jan'. */
export function formatDay(ts: string): string {
  const date = parse(ts)
  if (date === null) {
    return ts
  }
  return `${date.getUTCDate()} ${MONTHS[date.getUTCMonth()]}`
}

/** '1 Jan, 08:12'. */
export function formatDayTime(ts: string): string {
  const date = parse(ts)
  if (date === null) {
    return ts
  }
  const hours = String(date.getUTCHours()).padStart(2, '0')
  const minutes = String(date.getUTCMinutes()).padStart(2, '0')
  return `${formatDay(ts)}, ${hours}:${minutes}`
}

/** '3m 46s'. */
export function formatDuration(seconds: number): string {
  const whole = Math.round(seconds)
  return `${Math.floor(whole / 60)}m ${String(whole % 60).padStart(2, '0')}s`
}

/** One decimal place: scores are small weighted sums, not percentages. */
export function formatScore(score: number): string {
  return score.toFixed(1)
}

/** 'skipped step ×1 · repeated step ×1', in the order the session lists them. */
export function formatErrors(errors: SessionErrors): string {
  const parts = Object.entries(errors)
    .filter(([, count]) => (count ?? 0) > 0)
    .map(([type, count]) => `${ERROR_TYPE_LABEL[type as ErrorType] ?? type} ×${count}`)
  return parts.join(' · ')
}

/** 'Temperature 36.8 °C', used by both the resident timeline and the alert context. */
export function describeCareRecord(record: CareRecord): string {
  switch (record.kind) {
    case 'temperature':
      return `Temperature ${record.value} °C`
    case 'fluid_intake':
      return `Fluid intake ${record.value} ml`
    case 'med_change':
      return `Medication change: ${record.value}`
    default:
      return `${record.kind}: ${record.value}`
  }
}

/** Epoch ms for sorting care records newest first; 0 (not NaN) for an unparseable `ts`. */
export function recordTime(ts: string): number {
  const parsed = Date.parse(ts)
  return Number.isNaN(parsed) ? 0 : parsed
}
