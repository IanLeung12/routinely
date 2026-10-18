import { useEffect, useId, useState } from 'react'
import type { Replay, ReplayMarker, PersonReplays, ReplaySummary } from '../contracts.ts'
import GhostReplay from '../evidence/GhostReplay.tsx'
import { ReplayPlayer, type ReplayPlayerMarker } from '../evidence/ReplayPlayer.tsx'
import { currentPerson, currentSupervisor } from '../people/api.ts'
import type { RoleId } from '../people/types.ts'
import { fetchResident } from '../resident/api.ts'
import { formatDayTime } from '../resident/format.ts'
import { Button } from '../ui/Button.tsx'
import { Card } from '../ui/Card.tsx'
import { EmptyState } from '../ui/EmptyState.tsx'
import { ErrorState } from '../ui/ErrorState.tsx'
import { Loading } from '../ui/Loading.tsx'
import { SectionHeader } from '../ui/SectionHeader.tsx'
import { describeError } from '../ui/errorTypes.ts'
import { deleteReplay, fetchPersonReplays, fetchReplay } from './api.ts'
import { ReplayList } from './ReplayList.tsx'
import { ReplayNotes, type ReplayNote } from './ReplayNotes.tsx'
import './replays.css'

const HEADING_ID = 'replays-heading'

type Library =
  | { personId: string; status: 'ok'; library: PersonReplays }
  | { personId: string; status: 'error' }

type OpenReplay =
  | { sessionId: string; status: 'ok'; replay: Replay }
  | { sessionId: string; status: 'error' }

/** Whether `startedAt` falls inside `[from, to]` (each 'YYYY-MM-DD' or empty for "no
 * bound"). Compared as calendar days, the same granularity the date inputs collect. */
function withinRange(startedAt: string, from: string, to: string): boolean {
  const day = startedAt.slice(0, 10)
  if (from && day < from) return false
  if (to && day > to) return false
  return true
}

/** Turns a replay's errors into `ReplayPlayer`'s marker shape: the same wording
 * `ErrorList` uses for the same error, so the alert screen and this one agree. */
function toPlayerMarkers(markers: ReplayMarker[]): ReplayPlayerMarker[] {
  return markers.map((marker) => ({
    t: marker.t_start,
    label: describeError(marker.type, marker.step_id ? marker.step_id.replace(/_/g, ' ') : 'this step'),
    kind: marker.type,
  }))
}

/** A person's replay library (SPEC section 17): a supervisor browsing a session that
 * had errors to analyse it, or the person seeing exactly the same thing about their
 * own routine. Opened from a person's detail, an alert's error rows, or "My routine". */
export function Replays({
  personId,
  role,
  initialSessionId = null,
  onBack,
}: {
  personId: string
  role: RoleId
  /** Opens straight into one session, e.g. from an alert's error rows. */
  initialSessionId?: string | null
  onBack: () => void
}) {
  const author = role === 'supervisor' ? currentSupervisor().name : currentPerson().name
  const [personName, setPersonName] = useState(role === 'person' ? currentPerson().name : personId)
  const [loaded, setLoaded] = useState<Library | null>(null)
  const [openSessionId, setOpenSessionId] = useState<string | null>(initialSessionId)
  const [openReplay, setOpenReplay] = useState<OpenReplay | null>(null)
  const [notesBySession, setNotesBySession] = useState<Record<string, ReplayNote[]>>({})
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [deleteError, setDeleteError] = useState(false)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const fromId = useId()
  const toId = useId()

  useEffect(() => {
    if (role !== 'supervisor') return
    let cancelled = false
    fetchResident(personId)
      .then((resident) => {
        if (!cancelled && resident) setPersonName(resident.name)
      })
      .catch(() => { /* Falls back to the id while the name can't be fetched. */ })
    return () => {
      cancelled = true
    }
  }, [personId, role])

  useEffect(() => {
    let cancelled = false
    fetchPersonReplays(personId)
      .then((library) => {
        if (!cancelled) setLoaded({ personId, status: 'ok', library })
      })
      .catch(() => {
        if (!cancelled) setLoaded({ personId, status: 'error' })
      })
    return () => {
      cancelled = true
    }
  }, [personId])

  useEffect(() => {
    if (openSessionId === null) return
    let cancelled = false
    fetchReplay(openSessionId)
      .then((replay) => {
        if (!cancelled) setOpenReplay({ sessionId: openSessionId, status: 'ok', replay })
      })
      .catch(() => {
        if (!cancelled) setOpenReplay({ sessionId: openSessionId, status: 'error' })
      })
    return () => {
      cancelled = true
    }
  }, [openSessionId])

  /** Opens a session from the list, resetting the delete confirmation a previous
   * session may have been left in. */
  function openSession(sessionId: string) {
    setConfirmingDelete(false)
    setDeleteError(false)
    setOpenSessionId(sessionId)
  }

  function addNote(sessionId: string, note: ReplayNote) {
    setNotesBySession((previous) => ({
      ...previous,
      [sessionId]: [...(previous[sessionId] ?? []), note],
    }))
  }

  async function confirmDelete(sessionId: string) {
    try {
      await deleteReplay(sessionId)
    } catch {
      setConfirmingDelete(false)
      setDeleteError(true)
      return
    }
    setLoaded((previous) =>
      previous !== null && previous.status === 'ok'
        ? {
            ...previous,
            library: { ...previous.library, replays: previous.library.replays.filter((r) => r.session_id !== sessionId) },
          }
        : previous,
    )
    setOpenSessionId(null)
  }

  const filtered: ReplaySummary[] =
    loaded !== null && loaded.personId === personId && loaded.status === 'ok'
      ? loaded.library.replays.filter((replay) => withinRange(replay.started_at, dateFrom, dateTo))
      : []
  const normal =
    loaded !== null && loaded.personId === personId && loaded.status === 'ok' ? loaded.library.normal : null

  let body
  if (openSessionId !== null) {
    body = (
      <div className="replays__detail">
        <button type="button" className="back-button" onClick={() => setOpenSessionId(null)}>
          ← Sessions
        </button>
        {openReplay === null || openReplay.sessionId !== openSessionId ? (
          <Loading label="Loading replay…" />
        ) : openReplay.status === 'error' ? (
          <ErrorState message="This replay could not be loaded." />
        ) : (
          <>
            <Card>
              <SectionHeader
                title={openReplay.replay.task_id}
                caption={`${formatDayTime(openReplay.replay.started_at)} · ${Math.floor(openReplay.replay.duration_s)}s`}
              />
              <ReplayPlayer frames={openReplay.replay.frames} markers={toPlayerMarkers(openReplay.replay.markers)} />
              {normal && normal.session_id !== openSessionId && (
                <div className="replays__ghost">
                  <GhostReplayPanel normalSessionId={normal.session_id} today={openReplay.replay} />
                </div>
              )}
            </Card>

            <ReplayNotes
              notes={notesBySession[openSessionId] ?? []}
              canAdd={role === 'supervisor'}
              author={author}
              onAdd={(note) => addNote(openSessionId, note)}
            />

            {role === 'person' && (
              <Card className="replays__delete">
                {confirmingDelete ? (
                  <>
                    <p>Delete this replay? This can't be undone.</p>
                    <div className="replays__delete-actions">
                      <Button variant="danger" onClick={() => { void confirmDelete(openSessionId) }}>
                        Delete
                      </Button>
                      <Button onClick={() => setConfirmingDelete(false)}>Cancel</Button>
                    </div>
                  </>
                ) : (
                  <>
                    {deleteError && <ErrorState message="This replay could not be deleted. It is still stored." />}
                    <Button variant="danger" onClick={() => { setDeleteError(false); setConfirmingDelete(true) }}>
                      Delete this replay
                    </Button>
                  </>
                )}
              </Card>
            )}
          </>
        )}
      </div>
    )
  } else if (loaded === null || loaded.personId !== personId) {
    body = <Loading label="Loading replays…" />
  } else if (loaded.status === 'error') {
    body = <ErrorState message="Replays could not be loaded." />
  } else {
    body = (
      <>
        <fieldset className="replays__range">
          <legend className="replays__range-legend">Filter by date</legend>
          <label htmlFor={fromId}>From</label>
          <input id={fromId} type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
          <label htmlFor={toId}>To</label>
          <input id={toId} type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
        </fieldset>
        {loaded.library.replays.length > 0 && filtered.length === 0 ? (
          <EmptyState message="No sessions with errors in this date range." />
        ) : (
          <ReplayList replays={filtered} normal={normal} onOpen={openSession} />
        )}
      </>
    )
  }

  return (
    <section className="replays" aria-labelledby={HEADING_ID}>
      <button type="button" className="back-button" onClick={onBack}>
        ← Back
      </button>
      <h1 id={HEADING_ID}>{personName}'s replays</h1>
      {body}
    </section>
  )
}

/** Fetches the kept comparison session's own frames once, to draw it under the
 * session on screen (SPEC section 17's "compare with the person's normal"). A
 * second small fetch rather than a prop: `ReplaySummary` carries no frames. */
function GhostReplayPanel({ normalSessionId, today }: { normalSessionId: string; today: Replay }) {
  const [normalReplay, setNormalReplay] = useState<{ sessionId: string; replay: Replay } | null>(null)

  useEffect(() => {
    let cancelled = false
    fetchReplay(normalSessionId)
      .then((replay) => {
        if (!cancelled) setNormalReplay({ sessionId: normalSessionId, replay })
      })
      .catch(() => { /* No comparison to show if it can't be fetched. */ })
    return () => {
      cancelled = true
    }
  }, [normalSessionId])

  if (normalReplay === null || normalReplay.sessionId !== normalSessionId) return null
  const t = today.markers[0]?.t_start ?? 0
  return <GhostReplay today={today.frames} normal={normalReplay.replay.frames} t={t} />
}

export default Replays
