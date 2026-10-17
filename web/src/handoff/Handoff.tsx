import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { fetchAlerts } from '../alert/api.ts'
import { fetchMonitoringHistory } from '../about/monitoringApi.ts'
import type { MonitoringChange } from '../about/monitoringApi.ts'
import type { Alert } from '../contracts.ts'
import { fetchResident } from '../resident/api.ts'
import { formatScore } from '../resident/format.ts'
import { Button } from '../ui/Button.tsx'
import { Card } from '../ui/Card.tsx'
import { EmptyState } from '../ui/EmptyState.tsx'
import { ErrorState } from '../ui/ErrorState.tsx'
import { Loading } from '../ui/Loading.tsx'
import { Pill, type PillTone } from '../ui/Pill.tsx'
import { Row } from '../ui/Row.tsx'
import { SectionHeader } from '../ui/SectionHeader.tsx'
import { SegmentedControl } from '../ui/SegmentedControl.tsx'
import { fetchHandoff } from './api.ts'
import type { HandoffResult } from './api.ts'
import { HandoffDelta, handoffDeltaLabel } from './HandoffDelta.tsx'
import type { Handoff as HandoffData, HandoffResident, PausedRoom } from './types.ts'
import './handoff.css'

/** Windows a nurse picks between: an eight or twelve hour shift, a day, a weekend.
 * Labelled the way a segment can be read at a glance; the group says "Window". */
const WINDOWS = [8, 12, 24, 48].map((hours) => ({ value: String(hours), label: `${hours}h` }))

/** A shift, and what `GET /handoff` defaults to. */
const DEFAULT_WINDOW_H = 12

type Chip = {
  key: string
  /** `handoff__chip--` modifier: picks the `Pill` tone, carries the colour, never
   * the meaning. */
  tone: PillTone
  label: string
  /** Decorative, so the row is scannable without reading; the label says it in words. */
  glyph: string
}

function plural(n: number, noun: string): string {
  return n === 1 ? `${n} ${noun}` : `${n} ${noun}s`
}

/** "2 sessions too unclear to score - check the camera view", or null when the window
 * read every session in that room (and when an older or trimmed `/handoff` sent no
 * count at all, which is not the same as none).
 *
 * The room's camera, never the resident: a session too unclear to score is left out
 * of the resident's history entirely (`pipeline/src/routine_watch/live.py`, SPEC
 * section 12), so without this line a blocked or badly lit camera makes that room
 * read as a quiet one. One source for the wording, so the row and a note pasted from
 * it can't drift apart. Local to this screen: the row's chip and the copied line are
 * both built here. */
function unclearLabel(unclearSessions?: number | null): string | null {
  if (!unclearSessions || unclearSessions <= 0) return null
  return `${plural(unclearSessions, 'session')} too unclear to score — check the camera view`
}

function needsReview(resident: HandoffResident): boolean {
  return resident.flags > 0 || resident.pending_review > 0 || resident.trending
}

/** What this resident did with the window, in words. Never empty: a quiet resident
 * says so, so an untouched row can't be mistaken for a row that failed to load. */
function chipsFor(resident: HandoffResident): Chip[] {
  const chips: Chip[] = []
  if (resident.flags > 0) {
    chips.push({
      key: 'flags',
      label: `${plural(resident.flags, 'session')} above baseline`,
      tone: 'negative',
      glyph: '!',
    })
  }
  if (resident.pending_review > 0) {
    chips.push({
      key: 'pending',
      label: `${plural(resident.pending_review, 'alert')} not reviewed yet`,
      tone: 'watch',
      glyph: '⧗',
    })
  }
  if (resident.trending) {
    chips.push({ key: 'trending', label: 'Error score trending up', tone: 'watch', glyph: '↗' })
  }
  if (resident.monitoring_paused) {
    chips.push({ key: 'paused', label: 'Monitoring paused', tone: 'neutral', glyph: '⏸' })
  }
  // Grey, the way "unclear" reads everywhere else in the dashboard (SPEC section 7:
  // never counted as an error), and before the quiet chip: a room whose camera could
  // not be read is not a room with nothing to say.
  const unclear = unclearLabel(resident.unclear_sessions)
  if (unclear) {
    chips.push({ key: 'unclear', label: unclear, tone: 'neutral', glyph: '◌' })
  }
  if (chips.length === 0) {
    chips.push({ key: 'quiet', label: 'No change flagged', tone: 'positive', glyph: '✓' })
  }
  return chips
}

/** resident_id -> the alert to open from their row.
 *
 * The handoff's rows carry no alert id of their own (`pipeline/src/routine_watch/`
 * `handoff.py` counts alerts, it doesn't name them), so the id comes from the alerts
 * list, which serves one alert per flagged resident. The row's own `pending_review` is
 * what says an alert still needs a nurse, so the first match is the one to open: once
 * someone gives it a verdict the count drops and the row stops offering it. */
function alertByResident(alerts: Alert[]): Record<string, string> {
  const byResident: Record<string, string> = {}
  for (const alert of alerts) {
    byResident[alert.resident_id] ??= alert.alert_id
  }
  return byResident
}

/** "Usually 0.4 errors a session" against a resident's own history, or null for a
 * resident with no sessions yet (so the row says nothing rather than a false "0" or a
 * "NaN" from averaging an empty list). `mean` is `undefined` before the per-row fetch
 * resolves, which also shows nothing until there is a real number to report. */
function baselineLine(mean: number | null | undefined): string | null {
  if (mean === null || mean === undefined) return null
  return `Usually ${formatScore(mean)} errors a session`
}

/** 'HH:MM' in the nurse's own timezone: unlike the resident screens (which read UTC
 * off the pipeline, SPEC section 9), who paused a room and when is written by a nurse
 * on this shift, so the time on screen should match their own clock (T281). */
function formatLocalTime(ts: string): string {
  const date = new Date(ts)
  if (Number.isNaN(date.getTime())) return ts
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${hours}:${minutes}`
}

/** One line naming every paused room, or null when nothing was paused (SPEC section
 * 12): a nurse reads this above the rows, so a quiet paused room reads as "nobody was
 * watching" rather than "all quiet". `pauseDetails` names who paused each room and
 * when, read from the room's own audit trail (T281); a room missing from it (history
 * fetch failed or found no pause entry) just keeps today's plain line. */
function pausedLine(
  paused: PausedRoom[] | undefined,
  pauseDetails: Record<string, MonitoringChange | null> = {},
): string | null {
  if (!paused || paused.length === 0) return null
  return `Monitoring paused: ${paused.map((room) => {
    const change = pauseDetails[room.room]
    const detail = change ? `, paused by ${change.by} at ${formatLocalTime(change.at)}` : ''
    return `${room.name} (room ${room.room})${detail}`
  }).join(', ')}`
}

/** The one line a nurse reads first, before any row. */
function headline(residents: HandoffResident[], hours: number): string {
  if (residents.length === 0) return `Nothing to hand over for the last ${hours} hours`
  const review = residents.filter(needsReview).length
  if (review === 0) return `No change flagged for review in the last ${hours} hours`
  return `${review} of ${plural(residents.length, 'resident')} to review in the last ${hours} hours`
}

/** The handoff as plain text, for pasting into a shift note or a message. One line
 * per resident, each naming the room: the text leaves the screen behind, so a nurse
 * reading it elsewhere still knows which door the row is about. */
export function handoffText(
  h: HandoffData,
  pauseDetails: Record<string, MonitoringChange | null> = {},
): string {
  const paused = pausedLine(h.paused, pauseDetails)
  return [
    h.summary,
    ...(paused ? [paused] : []),
    ...h.residents.map((resident) => {
      // The row's own phrase, last: a nurse reading the line elsewhere needs the same
      // "better or worse than last shift" the screen showed (T324/T350). Nothing is
      // appended when the payload sent no comparison, so the line stays as it was.
      const delta = handoffDeltaLabel(resident.flags, resident.previous_flags)
      // Last, after the counts and the comparison: what the camera could not read is
      // about the room, so it reads as the note on the end of the line rather than
      // as one more thing the resident did.
      const unclear = unclearLabel(resident.unclear_sessions)
      return `${resident.name}, Room ${resident.room}: ${plural(resident.flags, 'flagged session')}, `
        + `${plural(resident.pending_review, 'unreviewed alert')}, `
        + (resident.trending ? 'Error score trending up' : 'No upward trend')
        + (delta ? `, ${delta}` : '')
        + (unclear ? `, ${unclear}` : '')
    }),
  ].join('\n')
}

/** Shift handoff: one view of who changed in the hours this nurse was away, off the
 * main demo path. Rows needing attention come first (the pipeline sorts them), each
 * labelled in words as well as colour, with the plain-language summary above them. */
export function Handoff({
  onBack,
  onOpenAlert,
}: {
  onBack: () => void
  onOpenAlert?: (alertId: string) => void
}) {
  const [copyStatus, setCopyStatus] = useState('')
  const [hours, setHours] = useState(DEFAULT_WINDOW_H)
  /** Tagged with the window it was fetched for, so switching windows shows the new
   * one loading rather than the last one's rows. */
  const [loaded, setLoaded] = useState<{ hours: number; result: HandoffResult } | null>(null)
  /** Which alert each row opens. Fetched once: the alerts a resident has don't depend
   * on the window, only on whether they are still flagged. Empty until it arrives, so
   * a row offers the alert when there is one to offer and never a dead button. */
  const [alertIds, setAlertIds] = useState<Record<string, string>>({})
  /** resident_id -> their own average errors per session, or null once fetched for a
   * resident with no history. The handoff's rows don't carry a baseline
   * (`pipeline/src/routine_watch/handoff.py` counts flags, not means), so this reads
   * it from the resident detail endpoint instead - one fetch per row, fine for the
   * demo's unit size. */
  const [baselines, setBaselines] = useState<Record<string, number | null>>({})
  /** room -> the newest audit entry that paused it, or null once fetched with none
   * found. Keyed by room rather than resident, same as `Handoff.paused` (T281). */
  const [pauseDetails, setPauseDetails] = useState<Record<string, MonitoringChange | null>>({})

  useEffect(() => {
    let cancelled = false
    fetchHandoff(hours).then((result) => {
      if (!cancelled) setLoaded({ hours, result })
    })
    return () => {
      cancelled = true
    }
  }, [hours])

  useEffect(() => {
    let cancelled = false
    fetchAlerts().then((alerts) => {
      if (!cancelled) setAlertIds(alertByResident(alerts))
    })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (loaded === null) return
    let cancelled = false
    const ids = loaded.result.handoff.residents.map((resident) => resident.resident_id)
    Promise.all(ids.map((id) => fetchResident(id).then((resident) => [id, resident] as const)))
      .then((entries) => {
        if (cancelled) return
        setBaselines((previous) => {
          const next = { ...previous }
          for (const [id, resident] of entries) {
            next[id] = resident !== null && resident.sessions.length > 0
              ? resident.baseline.mean
              : null
          }
          return next
        })
      })
    return () => {
      cancelled = true
    }
  }, [loaded])

  useEffect(() => {
    if (loaded === null) return
    const paused = loaded.result.handoff.paused ?? []
    if (paused.length === 0) return
    let cancelled = false
    Promise.all(
      paused.map((room) =>
        fetchMonitoringHistory(room.room)
          .then((history) => [room.room, history.find((change) => !change.on) ?? null] as const)
          .catch(() => [room.room, null] as const),
      ),
    ).then((entries) => {
      if (cancelled) return
      setPauseDetails((previous) => {
        const next = { ...previous }
        for (const [room, change] of entries) {
          next[room] = change
        }
        return next
      })
    })
    return () => {
      cancelled = true
    }
  }, [loaded])

  useEffect(() => {
    if (copyStatus !== 'Copied') return
    const timeout = window.setTimeout(() => setCopyStatus(''), 2000)
    return () => window.clearTimeout(timeout)
  }, [copyStatus])

  async function copySummary(handoff: HandoffData) {
    try {
      if (!navigator.clipboard?.writeText) {
        setCopyStatus('Copy not available')
        return
      }
      await navigator.clipboard.writeText(handoffText(handoff, pauseDetails))
      setCopyStatus('Copied')
    } catch {
      setCopyStatus('Copy not available')
    }
  }

  let body: ReactNode
  if (loaded === null || loaded.hours !== hours) {
    body = <Loading label="Loading handoff…" />
  } else {
    const { handoff, offline } = loaded.result
    body = (
      <>
        {offline && (
          <ErrorState message="Offline: showing demo data, not this unit's last shift." />
        )}
        <p className="handoff__headline" role="status">
          {headline(handoff.residents, handoff.window_hours)}
        </p>
        {/* The recap card: what the window says in one sentence, with the two quiet
            actions in a footer against the card's edge (the shape the alert view's
            recap uses, T405). */}
        <Card className="handoff__recap">
          <SectionHeader
            title={`Last ${handoff.window_hours} hours`}
            caption={`${plural(handoff.residents.length, 'resident')} on this unit`}
          />
          <p className="handoff__summary">{handoff.summary}</p>
          {/* Both actions and the copy's own status in one group: a nurse taps these
              on screen, and none of them say anything on paper, so the whole group is
              `no-print` (print.css hides it, T353). */}
          <div className="handoff__actions no-print">
            <Button variant="secondary" onClick={() => { void copySummary(handoff) }}>
              Copy summary
            </Button>
            {/* Nurses hand off on paper (T203). The browser's own print dialog, so the
                nurse keeps their printer, page size and "save as PDF". */}
            <Button variant="secondary" onClick={() => window.print()}>
              Print handoff
            </Button>
            {copyStatus && <p role="status">{copyStatus}</p>}
          </div>
        </Card>
        {pausedLine(handoff.paused, pauseDetails) && (
          <p className="handoff__paused">{pausedLine(handoff.paused, pauseDetails)}</p>
        )}
        {handoff.residents.length === 0 ? (
          <Card>
            <EmptyState message="No residents on this unit yet." />
          </Card>
        ) : (
          /* One card, not one box per resident: dense hairline-separated rows with
             who and where on the left and what happened on the right, so a unit is
             read down a column (docs/DESIGN.md). */
          <Card className="handoff__rows">
            <ul className="handoff__list">
              {handoff.residents.map((resident) => {
                const baseline = baselineLine(baselines[resident.resident_id])
                return (
                  <li
                    key={resident.resident_id}
                    className={`handoff__row${needsReview(resident) ? ' handoff__row--review' : ''}`}
                  >
                    <Row
                      title={<span className="handoff__name">{resident.name}</span>}
                      subtitle={
                        <>
                          <span className="handoff__room">Room {resident.room}</span>
                          {baseline && <span className="handoff__baseline">{baseline}</span>}
                        </>
                      }
                      trailing={
                        <>
                          <span className="handoff__chips">
                            {chipsFor(resident).map((chip) => (
                              <Pill key={chip.key} className="handoff__chip" tone={chip.tone}>
                                <span aria-hidden="true" className="handoff__glyph">
                                  {chip.glyph}
                                </span>
                                {chip.label}
                              </Pill>
                            ))}
                            {/* Beside the counts, not under them: two flagged sessions
                                is good news after four and bad news after none, so the
                                comparison is read with the chip that names them (T324). */}
                            <HandoffDelta
                              flags={resident.flags}
                              previousFlags={resident.previous_flags}
                            />
                          </span>
                          {onOpenAlert
                            && resident.pending_review > 0
                            && alertIds[resident.resident_id] && (
                            <Button
                              aria-label={`Open ${resident.name}'s alert`}
                              className="no-print"
                              onClick={() => onOpenAlert(alertIds[resident.resident_id])}
                            >
                              Open alert
                            </Button>
                          )}
                        </>
                      }
                    />
                  </li>
                )
              })}
            </ul>
          </Card>
        )}
      </>
    )
  }

  return (
    <section className="handoff" aria-label="Shift handoff">
      <button type="button" className="back-button no-print" onClick={onBack}>
        ← Back
      </button>
      <div className="handoff__head">
        <div className="handoff__headings">
          <h2 className="handoff__title">Shift handoff</h2>
          <p className="handoff__lead">
            Who changed while you were away. Everything here is flagged for a nurse to review.
          </p>
        </div>
        {/* "Pick one view" is a segmented control everywhere in the system
            (docs/DESIGN.md); the group is named Window, so a segment reads as
            "Window, 12h" rather than as a bare number. */}
        <div className="handoff__controls no-print">
          <p className="handoff__label" aria-hidden="true">
            Window
          </p>
          <SegmentedControl
            label="Window"
            options={WINDOWS}
            value={String(hours)}
            onChange={(choice) => setHours(Number(choice))}
          />
        </div>
      </div>
      {body}
    </section>
  )
}

export default Handoff
