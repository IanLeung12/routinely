import type { ResidentStatus } from './types.ts'

const LABELS: Record<ResidentStatus, string> = {
  normal: 'Normal',
  watch: 'Watch',
  flagged: 'Flagged',
}

/** Colour-coded status chip (SPEC section 9): a nurse should read it at a glance,
 * no reading required beyond the colour and the word. */
export function StatusChip({ status }: { status: ResidentStatus }) {
  return <span className={`status-chip status-chip--${status}`}>{LABELS[status]}</span>
}
