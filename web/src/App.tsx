import { useEffect, useState } from 'react'
import { fetchAlerts } from './alert/api.ts'
import { AlertView } from './alert/AlertView.tsx'
import { Handoff } from './handoff/Handoff.tsx'
import { LiveScreen } from './live/LiveScreen.tsx'
import { fetchResidents } from './overview/api.ts'
import { UnitOverview } from './overview/UnitOverview.tsx'
import { PatternLibrary } from './patterns/PatternLibrary.tsx'
import { ResidentDetail } from './resident/ResidentDetail.tsx'
import { Tour } from './tour/Tour.tsx'
import { Button } from './ui/Button.tsx'
import { DemoBanner } from './ui/DemoBanner.tsx'

/** Where an alert was opened from, so its Back button can return there instead of
 * always landing on the overview. */
type AlertOrigin = 'overview' | 'handoff' | 'live'

export default function App() {
  /** `?tour=1` opts into the presenter cue card; off by default so it never touches
   * the real demo path. */
  const showTour = new URLSearchParams(window.location.search).has('tour')
  /** Which resident's detail is open, if any. Two screens don't need a router. */
  const [openResident, setOpenResident] = useState<string | null>(null)
  const [openAlert, setOpenAlert] = useState<string | null>(null)
  const [alertOrigin, setAlertOrigin] = useState<AlertOrigin>('overview')
  /** The shift handoff sits off the main demo path, behind one button. */
  const [openHandoff, setOpenHandoff] = useState(false)
  /** The pattern library is a read-only reference screen, off the main demo path. */
  const [openPatternLibrary, setOpenPatternLibrary] = useState(false)
  const [alerts, setAlerts] = useState<Awaited<ReturnType<typeof fetchAlerts>>>([])
  const [residents, setResidents] = useState<Awaited<ReturnType<typeof fetchResidents>>>([])
  /** Bumped when a live session ends, so the overview and alerts list refetch
   * without a page reload (SPEC demo beat "alert appears after the second bad session"). */
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    let cancelled = false
    fetchAlerts().then(result => {
      if (!cancelled) setAlerts(result)
    })
    return () => { cancelled = true }
  }, [refreshKey])

  useEffect(() => {
    let cancelled = false
    fetchResidents().then(result => {
      if (!cancelled) setResidents(result)
    })
    return () => { cancelled = true }
  }, [refreshKey])

  function residentName(id: string): string {
    return residents.find(resident => resident.id === id)?.name ?? id
  }

  /** Opens an alert, remembering which screen asked for it. */
  function openAlertFrom(origin: AlertOrigin, id: string) {
    setAlertOrigin(origin)
    setOpenAlert(id)
  }

  /** Returns from the alert to wherever it was opened from. */
  function closeAlert() {
    setOpenAlert(null)
    setOpenHandoff(alertOrigin === 'handoff')
  }

  return (
    <main className="app">
      {showTour && <Tour />}
      <DemoBanner />
      <header>
        <h1>Routine Watch</h1>
        <p className="tagline">
          Watches a resident make a cup of tea and flags a change in their routine for a
          nurse to review.
        </p>
        {!openHandoff && !openPatternLibrary && (
          <>
            <Button onClick={() => setOpenHandoff(true)}>Shift handoff</Button>
            <Button variant="secondary" onClick={() => setOpenPatternLibrary(true)}>
              Pattern library
            </Button>
          </>
        )}
      </header>

      {openAlert !== null ? (
        <AlertView alertId={openAlert} onBack={closeAlert} />
      ) : openHandoff ? (
        <Handoff
          onBack={() => setOpenHandoff(false)}
          onOpenAlert={id => openAlertFrom('handoff', id)}
        />
      ) : openPatternLibrary ? (
        <PatternLibrary onBack={() => setOpenPatternLibrary(false)} />
      ) : openResident === null ? (
        <>
          <section>
            <h2>Unit overview</h2>
            <UnitOverview onSelect={setOpenResident} refreshKey={refreshKey} />
          </section>

          <section>
            <h2>Live session</h2>
            <LiveScreen
              onOpenAlert={id => openAlertFrom('live', id)}
              onSessionEnd={() => setRefreshKey((key) => key + 1)}
            />
          </section>

          <section>
            <h2>Alerts</h2>
            <ul className="resident-list">
              {alerts.map(alert => (
                <li key={alert.alert_id} className="resident-row">
                  <button
                    type="button"
                    className="resident-open"
                    onClick={() => openAlertFrom('overview', alert.alert_id)}
                  >
                    {residentName(alert.resident_id)}: {alert.kind === 'trend' ? 'Slow trend for review' : 'Change flagged for review'}
                  </button>
                </li>
              ))}
            </ul>
          </section>
        </>
      ) : (
        <ResidentDetail residentId={openResident} onBack={() => setOpenResident(null)} />
      )}
    </main>
  )
}
