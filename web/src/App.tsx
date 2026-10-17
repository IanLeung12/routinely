import { useEffect, useState } from 'react'
import { fetchAlerts } from './alert/api.ts'
import { AlertView } from './alert/AlertView.tsx'
import { Handoff } from './handoff/Handoff.tsx'
import { LiveScreen } from './live/LiveScreen.tsx'
import { UnitOverview } from './overview/UnitOverview.tsx'
import { ResidentDetail } from './resident/ResidentDetail.tsx'
import { Button } from './ui/Button.tsx'
import { DemoBanner } from './ui/DemoBanner.tsx'

export default function App() {
  /** Which resident's detail is open, if any. Two screens don't need a router. */
  const [openResident, setOpenResident] = useState<string | null>(null)
  const [openAlert, setOpenAlert] = useState<string | null>(null)
  /** The shift handoff sits off the main demo path, behind one button. */
  const [openHandoff, setOpenHandoff] = useState(false)
  const [alerts, setAlerts] = useState<Awaited<ReturnType<typeof fetchAlerts>>>([])
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

  return (
    <main className="app">
      <DemoBanner />
      <header>
        <h1>Routine Watch</h1>
        <p className="tagline">
          Watches a resident make a cup of tea and flags a change in their routine for a
          nurse to review.
        </p>
        {!openHandoff && (
          <Button onClick={() => setOpenHandoff(true)}>Shift handoff</Button>
        )}
      </header>

      {openHandoff ? (
        <Handoff
          onBack={() => setOpenHandoff(false)}
          onOpenAlert={id => { setOpenHandoff(false); setOpenAlert(id) }}
        />
      ) : openAlert !== null ? (
        <AlertView alertId={openAlert} onBack={() => setOpenAlert(null)} />
      ) : openResident === null ? (
        <>
          <section>
            <h2>Unit overview</h2>
            <UnitOverview onSelect={setOpenResident} refreshKey={refreshKey} />
          </section>

          <section>
            <h2>Live session</h2>
            <LiveScreen
              onOpenAlert={setOpenAlert}
              onSessionEnd={() => setRefreshKey((key) => key + 1)}
            />
          </section>

          <section>
            <h2>Alerts</h2>
            <ul className="resident-list">
              {alerts.map(alert => (
                <li key={alert.alert_id} className="resident-row">
                  <button type="button" className="resident-open" onClick={() => setOpenAlert(alert.alert_id)}>
                    {alert.resident_id}: {alert.kind === 'trend' ? 'Slow trend for review' : 'Change flagged for review'}
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
