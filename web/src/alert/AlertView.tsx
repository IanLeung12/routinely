import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
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
import { ErrorList } from './ErrorList.tsx'
import { FeedbackButtons } from './FeedbackButtons.tsx'
import { PatternList } from './PatternList.tsx'
import { SuggestedChecks } from './SuggestedChecks.tsx'
import './alert.css'

function formatBaseline(baseline: BaselineComparison): string {
  return `${baseline.observed.toFixed(1)} vs ${baseline.baseline_mean.toFixed(1)} normal over ${baseline.baseline_days} days`
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
  const [careRecords, setCareRecords] = useState<{ alertId: string; records: CareRecord[] | null } | null>(null)

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
    fetchResident(loaded.alert.resident_id).then((resident) => {
      if (!cancelled) {
        setCareRecords({ alertId, records: resident?.care_records ?? null })
      }
    })
    return () => {
      cancelled = true
    }
  }, [alertId, loaded])

  useEffect(() => {
    let cancelled = false
    fetchReplay(alertId).then((fetched) => {
      if (!cancelled) {
        setReplay({ alertId, replay: fetched })
      }
    })
    return () => {
      cancelled = true
    }
  }, [alertId])

  async function handleFeedback(verdict: FeedbackVerdict) {
    setFeedbackError(null)
    try {
      const updated = await postFeedback(alertId, verdict)
      setLoaded({ alertId, alert: updated })
    } catch {
      setFeedbackError('Feedback could not be saved. Try again.')
    }
  }

  let body: ReactNode
  if (loaded === null || loaded.alertId !== alertId) {
    body = <Loading label="Loading alert…" />
  } else if (loaded.alert === null) {
    body = <EmptyState message={`No alert found for ${alertId}.`} />
  } else {
    const alert = loaded.alert
    body = (
      <>
        <p className="alert-view__summary">{alert.summary}</p>
        <p className="alert-view__baseline">{formatBaseline(alert.baseline)}</p>
        <p className="alert-view__threshold">
          Current threshold: {alert.baseline.threshold.toFixed(1)}
        </p>

        {careRecords !== null && careRecords.alertId === alertId && careRecords.records !== null && (
          <Card>
            <SectionHeader title="Recent care records" />
            <AlertContext records={careRecords.records} alertTs={alert.created_at} />
          </Card>
        )}

        <Card>
          <SectionHeader title="Possible patterns" />
          <PatternList patterns={alert.patterns ?? []} />
        </Card>

        <Card>
          <SectionHeader title="Errors" />
          <ErrorList errors={alert.errors} onOpen={(error) => onOpenEvidence?.(error)} />
        </Card>

        <Card>
          <SectionHeader title="Evidence" />
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
          <SectionHeader title="Suggested checks" />
          <SuggestedChecks checks={alert.suggested_checks} />
        </Card>

        <Card>
          <SectionHeader title="Feedback" />
          <FeedbackButtons value={alert.feedback?.verdict ?? null} onChange={handleFeedback} />
          {feedbackError && <ErrorState message={feedbackError} />}
        </Card>
      </>
    )
  }

  return (
    <section className="alert-view">
      <button type="button" className="back-button" onClick={onBack}>
        ← Back
      </button>
      {body}
    </section>
  )
}

export default AlertView
