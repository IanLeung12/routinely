import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { Button } from '../ui/Button.tsx'
import { Card } from '../ui/Card.tsx'
import { EmptyState } from '../ui/EmptyState.tsx'
import { ErrorState } from '../ui/ErrorState.tsx'
import { Loading } from '../ui/Loading.tsx'
import { SectionHeader } from '../ui/SectionHeader.tsx'
import type { Alert, BaselineComparison, FeedbackVerdict, TaskError } from '../contracts.ts'
import { fetchReplay } from '../evidence/api.ts'
import type { EvidenceReplay } from '../evidence/api.ts'
import GhostReplay from '../evidence/GhostReplay.tsx'
import { ReplayPlayer } from '../evidence/ReplayPlayer.tsx'
import { fetchResident } from '../resident/api.ts'
import type { CareRecord } from '../resident/types.ts'
import { fetchAlert, postFeedback } from './api.ts'
import { AlertContext } from './AlertContext.tsx'
import { alertText } from './alertText.ts'
import { ErrorList } from './ErrorList.tsx'
import { FeedbackButtons } from './FeedbackButtons.tsx'
import { PatternList } from './PatternList.tsx'
import { SuggestedChecks } from './SuggestedChecks.tsx'
import './alert.css'

const HEADING_ID = 'alert-view-heading'

function formatBaseline(baseline: BaselineComparison): string {
  return `${baseline.observed.toFixed(1)} vs ${baseline.baseline_mean.toFixed(1)} normal over ${baseline.baseline_days} days`
}

/** A card section's title, at `h2` so the alert reads as one heading outline (SPEC
 * section 9): `h1` resident + "Flagged for review", then each section in reading order.
 * Same look as the shared `SectionHeader`, which is fixed at `h3` for use inside screens
 * that already have their own `h2`. */
function AlertSectionHeading({ title }: { title: string }) {
  return (
    <div className="section-header">
      <h2 className="section-header__title">{title}</h2>
    </div>
  )
}

/** What "what was it?" offers a nurse: the patterns this change was flagged as being
 * consistent with, each under the id the API counts it by. Undefined when the alert has
 * no patterns, so the picker never asks a question whose only answer is "Other". */
function causeOptions(alert: Alert): { id: string; label: string }[] | undefined {
  const patterns = alert.patterns ?? []
  if (patterns.length === 0) return undefined
  return patterns.map((pattern) => ({ id: pattern.pattern_id, label: pattern.name }))
}

/** Screen 4 (SPEC section 9): the evidence behind a flagged alert, readable in 10
 * seconds. Plain-language summary and baseline comparison first, then the error-by-error
 * detail, suggested checks and the confirm/false-alarm feedback that tunes the threshold. */
export function AlertView({
  alertId,
  onBack,
  onOpenEvidence,
}: {
  alertId: string
  onBack: () => void
  onOpenEvidence?: (error: TaskError) => void
}) {
  /** Tagged with the id it was fetched for, so switching alerts shows the new one
   * loading rather than the last one's summary. */
  const [loaded, setLoaded] = useState<{ alertId: string; alert: Alert | null } | null>(null)
  const [feedbackError, setFeedbackError] = useState<string | null>(null)
  const [replay, setReplay] = useState<{ alertId: string; replay: EvidenceReplay | null } | null>(null)
  /** The alert's resident, fetched once the alert names them: their real name for the
   * heading and the copied summary, and the care records shown beside the evidence. */
  const [resident, setResident] = useState<{ alertId: string; name?: string; records: CareRecord[] | null } | null>(null)
  const [copyStatus, setCopyStatus] = useState('')
  const headingRef = useRef<HTMLHeadingElement>(null)
  /** Which alert focus has already landed on, so re-rendering after feedback is saved
   * (same alert, new data) doesn't steal focus back from whatever the nurse is doing. */
  const focusedAlertIdRef = useRef<string | null>(null)

  /** Moves focus to the `h1` as soon as an alert finishes loading, so a screen reader
   * announces which resident this is for right when the view opens (SPEC section 9). */
  useEffect(() => {
    if (
      loaded !== null &&
      loaded.alertId === alertId &&
      loaded.alert !== null &&
      focusedAlertIdRef.current !== alertId
    ) {
      headingRef.current?.focus()
      focusedAlertIdRef.current = alertId
    }
  }, [alertId, loaded])

  useEffect(() => {
    let cancelled = false
    fetchAlert(alertId).then((fetched) => {
      if (!cancelled) {
        setLoaded({ alertId, alert: fetched })
      }
    })
    return () => {
      cancelled = true
    }
  }, [alertId])

  useEffect(() => {
    let cancelled = false
    if (loaded === null || loaded.alertId !== alertId || loaded.alert === null) {
      return
    }
    fetchResident(loaded.alert.resident_id).then((fetched) => {
      if (!cancelled) {
        setResident({ alertId, name: fetched?.name, records: fetched?.care_records ?? null })
      }
    })
    return () => {
      cancelled = true
    }
  }, [alertId, loaded])

  useEffect(() => {
    let cancelled = false
    if (loaded === null || loaded.alertId !== alertId || loaded.alert === null) {
      return
    }
    fetchReplay(loaded.alert).then((fetched) => {
      if (!cancelled) {
        setReplay({ alertId, replay: fetched })
      }
    })
    return () => {
      cancelled = true
    }
    // Feedback updates the alert object without changing its replay evidence.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [alertId, loaded?.alert?.alert_id])

  useEffect(() => {
    if (copyStatus !== 'Copied') return
    const timeout = window.setTimeout(() => setCopyStatus(''), 2000)
    return () => window.clearTimeout(timeout)
  }, [copyStatus])

  /** The name the API has for this resident, once it has loaded for the alert on screen.
   * Undefined until then, so the screen falls back to the raw id rather than guessing a
   * name from it and disagreeing with the rest of the app (T221). */
  const residentName = resident !== null && resident.alertId === alertId ? resident.name : undefined

  /** One tap to copy the flag into the care record, so it reaches the chart without
   * retyping (SPEC section 9, like the handoff's "Copy summary", T151). */
  async function copySummary(alert: Alert) {
    try {
      if (!navigator.clipboard?.writeText) {
        setCopyStatus('Copy not available')
        return
      }
      await navigator.clipboard.writeText(alertText(alert, residentName))
      setCopyStatus('Copied')
    } catch {
      setCopyStatus('Copy not available')
    }
  }

  /** Posts the verdict and, when the nurse has answered "what was it?", the cause with
   * it (SPEC section 5, MVP 8). The saved alert comes back from the API, so what the
   * buttons show is always what was stored. Answering the verdict again clears the
   * cause: it is a fresh answer, not a correction of the old one. */
  async function saveFeedback(verdict: FeedbackVerdict, cause: string | null) {
    setFeedbackError(null)
    try {
      const updated = await postFeedback(alertId, verdict, undefined, cause)
      setLoaded({ alertId, alert: updated })
    } catch {
      setFeedbackError('Feedback could not be saved. Try again.')
    }
  }

  let heading: ReactNode = null
  let body: ReactNode
  if (loaded === null || loaded.alertId !== alertId) {
    body = <Loading label="Loading alert…" />
  } else if (loaded.alert === null) {
    body = <EmptyState message="No change flagged for review." />
  } else {
    const alert = loaded.alert
    heading = (
      <h1 id={HEADING_ID} ref={headingRef} tabIndex={-1}>
        {residentName ?? alert.resident_id} flagged for review
      </h1>
    )
    body = (
      <>
        <AlertSectionHeading title="What changed" />
        <p className="alert-view__summary">{alert.summary}</p>
        <p className="alert-view__baseline">{formatBaseline(alert.baseline)}</p>
        <p className="alert-view__threshold">
          Current threshold: {alert.baseline.threshold.toFixed(1)}
        </p>
        <Button variant="secondary" onClick={() => { void copySummary(alert) }}>
          Copy summary
        </Button>
        {copyStatus && <p role="status">{copyStatus}</p>}

        {resident !== null && resident.alertId === alertId && resident.records !== null && (
          <Card>
            <SectionHeader title="Recent care records" />
            <AlertContext records={resident.records} alertTs={alert.created_at} />
          </Card>
        )}

        <Card>
          <AlertSectionHeading title="Errors" />
          <ErrorList errors={alert.errors} onOpen={(error) => onOpenEvidence?.(error)} />
        </Card>

        <Card>
          <AlertSectionHeading title="Evidence" />
          {replay === null || replay.alertId !== alertId ? (
            <Loading label="Loading replay…" />
          ) : replay.replay === null ? (
            <EmptyState message="No skeleton replay available for this alert." />
          ) : (
            <div className="alert-view__evidence">
              <ReplayPlayer frames={replay.replay.today} />
              <GhostReplay today={replay.replay.today} normal={replay.replay.normal} t={replay.replay.t_start} />
            </div>
          )}
        </Card>

        <Card>
          <AlertSectionHeading title="Possible patterns" />
          <PatternList patterns={alert.patterns ?? []} />
        </Card>

        <Card>
          <AlertSectionHeading title="Suggested checks" />
          <SuggestedChecks checks={alert.suggested_checks} />
        </Card>

        <Card>
          <AlertSectionHeading title="Feedback" />
          <FeedbackButtons
            value={alert.feedback?.verdict ?? null}
            onChange={(verdict) => saveFeedback(verdict, null)}
            causeOptions={causeOptions(alert)}
            cause={alert.feedback?.cause ?? null}
            onCauseChange={(cause) => saveFeedback('confirmed', cause)}
          />
          {feedbackError && <ErrorState message={feedbackError} />}
        </Card>
      </>
    )
  }

  return (
    <section className="alert-view" aria-labelledby={heading ? HEADING_ID : undefined}>
      <button type="button" className="back-button" onClick={onBack}>
        ← Back
      </button>
      {heading}
      {body}
    </section>
  )
}

export default AlertView
