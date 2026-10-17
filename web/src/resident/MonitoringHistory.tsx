import type { MonitoringChange } from '../about/monitoringApi.ts'
import { formatDayTime } from './format.ts'
import './monitoringHistory.css'

/** How many changes sit under the switch: the last few taps a nurse coming on shift
 * needs, not the whole trail (the API keeps up to 20). */
const SHOWN = 5

const TITLE_ID = 'monitoring-history-title'

/** Who paused or resumed monitoring in this room, and when (SPEC §12): the accountable
 * half of a switch that can turn a camera off. Newest first, under the switch itself. */
export function MonitoringHistory({ changes }: { changes: MonitoringChange[] }) {
  const recent = changes.slice(0, SHOWN)

  return (
    <div className="monitoring-history" role="group" aria-labelledby={TITLE_ID}>
      <p className="monitoring-history__title" id={TITLE_ID}>Recent changes</p>
      {recent.length === 0 ? (
        <p className="monitoring-history__empty">No changes this shift</p>
      ) : (
        <ul className="monitoring-history__list">
          {recent.map((change) => (
            <li className="monitoring-history__change" key={`${change.at}-${String(change.on)}`}>
              <span
                className={`monitoring-history__what monitoring-history__what--${change.on ? 'on' : 'paused'}`}
              >
                {change.on ? 'Resumed' : 'Paused'}
              </span>
              {` by ${change.by} · ${formatDayTime(change.at)}`}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
