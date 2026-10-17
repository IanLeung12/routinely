import { formatDayTime } from '../resident/format.ts'
import type { CareRecord } from '../resident/types.ts'
import { EmptyState } from '../ui/EmptyState.tsx'

function describe(record: CareRecord): string {
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

function time(ts: string): number {
  const parsed = Date.parse(ts)
  return Number.isNaN(parsed) ? 0 : parsed
}

/** Care-record context beside an alert (SPEC §5 nice-to-have 5): meds, temperature
 * and fluids from the window before the alert, newest first. Context only. */
export function AlertContext({
  records,
  alertTs,
  windowHours = 72,
}: {
  records: CareRecord[]
  alertTs: string
  windowHours?: number
}) {
  const alertTime = time(alertTs)
  const windowMs = windowHours * 60 * 60 * 1000
  const inWindow = records.filter((record) => {
    const recordTime = time(record.ts)
    return recordTime <= alertTime && recordTime >= alertTime - windowMs
  })

  if (inWindow.length === 0) {
    return <EmptyState message="No care-record changes in the last 3 days" />
  }

  const newestFirst = [...inWindow].sort((a, b) => time(b.ts) - time(a.ts))

  return (
    <ol className="alert-context">
      {newestFirst.map((record) => (
        <li
          key={`${record.ts}-${record.kind}`}
          className={`alert-context__record alert-context__record--${record.kind}`}
        >
          <span className="alert-context__when">{formatDayTime(record.ts)}</span>
          <span className="alert-context__what">{describe(record)}</span>
          {record.note !== '' && <span className="alert-context__note">{record.note}</span>}
        </li>
      ))}
    </ol>
  )
}

export default AlertContext
