import { describeCareRecord, formatDayTime, recordTime } from './format.ts'
import type { CareRecord } from './types.ts'
import './contextTimeline.css'

/** Care records next to the chart, newest first (SPEC section 9, screen 2): meds,
 * temperature and fluids a nurse reads alongside a change. Context only — the
 * pipeline neither detects nor interprets these. */
export function ContextTimeline({ records }: { records: CareRecord[] }) {
  if (records.length === 0) {
    return <p className="muted">No care records for this person.</p>
  }

  const newestFirst = [...records].sort((a, b) => recordTime(b.ts) - recordTime(a.ts))

  return (
    <ol className="context-timeline">
      {newestFirst.map((record) => (
        <li
          key={`${record.ts}-${record.kind}`}
          className={`context-record context-record--${record.kind}${record.kind === 'temperature' && Number(record.value) >= 38 ? ' context-record--fever' : ''}`}
        >
          <time className="context-when" dateTime={record.ts}>{formatDayTime(record.ts)}</time>
          <span className="context-what">{describeCareRecord(record)}</span>
          {record.note !== '' && <span className="context-note">{record.note}</span>}
        </li>
      ))}
    </ol>
  )
}
