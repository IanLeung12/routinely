import { useState } from 'react'
import type { ErrorType, ReplaySummary } from '../contracts'
import { EmptyState } from '../ui/EmptyState'
import { Pill } from '../ui/Pill'
import { Row } from '../ui/Row'
import { SegmentedControl } from '../ui/SegmentedControl'
import { ERROR_TYPE_LABEL, ERROR_TYPE_TONE } from '../ui/errorTypes'
import './replayList.css'

export function ReplayList({ replays, normal, onOpen }: {
  replays: ReplaySummary[]
  normal?: ReplaySummary | null
  onOpen: (sessionId: string) => void
}) {
  const [filter, setFilter] = useState<ErrorType | 'all'>('all')
  const types = (Object.keys(ERROR_TYPE_LABEL) as ErrorType[])
    .filter((type) => replays.some((replay) => replay.error_types.includes(type)))
  const activeFilter = filter === 'all' || types.includes(filter) ? filter : 'all'
  const visible = [...replays]
    .sort((a, b) => Date.parse(b.started_at) - Date.parse(a.started_at))
    .filter((replay) => activeFilter === 'all' || replay.error_types.includes(activeFilter))

  function row(replay: ReplaySummary, comparison = false) {
    const seconds = Math.floor(replay.duration_s)
    return (
      <li key={replay.session_id}>
        <Row
          className="replay-list__row"
          title={<time dateTime={replay.started_at}>{new Date(replay.started_at).toLocaleString()}</time>}
          subtitle={<span className="replay-list__details">
            <span>{replay.task_id}</span>
            {comparison && <span>Most recent normal session (for comparison)</span>}
            <span className="replay-list__pills">
              {replay.error_types.map((type) => (
                <Pill key={type} tone={ERROR_TYPE_TONE[type] === 'red' ? 'negative' : ERROR_TYPE_TONE[type] === 'amber' ? 'watch' : 'neutral'}>
                  {ERROR_TYPE_LABEL[type]}
                </Pill>
              ))}
            </span>
          </span>}
          value={`${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`}
          onSelect={() => onOpen(replay.session_id)}
        />
      </li>
    )
  }

  return (
    <div className="replay-list">
      <SegmentedControl<ErrorType | 'all'>
        className="replay-list__filter"
        label="Filter replays by error type"
        options={[{ value: 'all', label: 'All' }, ...types.map((type) => ({ value: type, label: ERROR_TYPE_LABEL[type] }))]}
        value={activeFilter}
        onChange={setFilter}
      />
      {visible.length === 0 && <EmptyState message="No sessions with errors in the last 30 days" />}
      <ul className="replay-list__rows" aria-label="Replay sessions">
        {visible.map((replay) => row(replay))}
        {normal && row(normal, true)}
      </ul>
    </div>
  )
}
