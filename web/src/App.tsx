import { lazy, Suspense, useEffect, useState } from 'react'
import './App.css'
import { fetchAlerts } from './alert/api.ts'
import { AlertView } from './alert/AlertView.tsx'
import { LiveScreen } from './live/LiveScreen.tsx'
import { fetchResidentsWithSource, type ResidentsSource } from './overview/api.ts'
import { UnitOverview } from './overview/UnitOverview.tsx'
import { ResidentDetail } from './resident/ResidentDetail.tsx'
import { DemoBanner } from './ui/DemoBanner.tsx'
import { Loading } from './ui/Loading.tsx'
import { Pill } from './ui/Pill.tsx'
import { useDocumentTitle } from './ui/useDocumentTitle.ts'

/** Off the main demo path (SPEC demo beat is overview → live → alert), so these
 * screens load on demand instead of growing the first-paint bundle. */
const Handoff = lazy(() => import('./handoff/Handoff.tsx').then(m => ({ default: m.Handoff })))
const PatternLibrary = lazy(() =>
  import('./patterns/PatternLibrary.tsx').then(m => ({ default: m.PatternLibrary })),
)
const Tour = lazy(() => import('./tour/Tour.tsx').then(m => ({ default: m.Tour })))

/** Where an alert was opened from, so its Back button can return there instead of
 * always landing on the overview. */
type AlertOrigin = 'overview' | 'handoff' | 'live'

/** The app shell's three top-level destinations, for the floating nav dock. A
 * resident's detail or an open alert are drill-ins reached from the overview, so
 * they still count as 'overview' for which dock item is current. */
type MainScreen = 'overview' | 'handoff' | 'patterns'

const MAIN_SCREENS: { id: MainScreen; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'handoff', label: 'Shift handoff' },
  { id: 'patterns', label: 'Pattern library' },
]

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
  const [residents, setResidents] = useState<Awaited<ReturnType<typeof fetchResidentsWithSource>>['residents']>([])
  /** Whether the last residents fetch reached the real API or fell back to demo
   * data, for the top bar's compact offline indicator. */
  const [residentsSource, setResidentsSource] = useState<ResidentsSource>('api')
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
    fetchResidentsWithSource().then(result => {
      if (!cancelled) {
        setResidents(result.residents)
        setResidentsSource(result.source)
      }
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

  /** The dock's current screen: a resident's detail or an open alert are
   * drill-ins reached from the overview, so they don't get their own dock item. */
  const currentScreen: MainScreen = openHandoff ? 'handoff' : openPatternLibrary ? 'patterns' : 'overview'

  /** Jumps straight to one of the three main screens, closing whatever drill-in
   * (a resident's detail, an open alert) was on top of it. */
  function goToScreen(screen: MainScreen) {
    setOpenResident(null)
    setOpenAlert(null)
    setOpenHandoff(screen === 'handoff')
    setOpenPatternLibrary(screen === 'patterns')
  }

  useDocumentTitle(documentTitle())

  /** So a nurse with several tabs open (or a screen reader) can tell the
   * overview from Mrs. K's alert. */
  function documentTitle(): string {
    if (openAlert !== null) {
      const resident = alerts.find(alert => alert.alert_id === openAlert)?.resident_id
      const name = resident ? residentName(resident) : null
      return name ? `Alert · ${name} — Routine Watch` : 'Alert — Routine Watch'
    }
    if (openHandoff) return 'Shift handoff — Routine Watch'
    if (openPatternLibrary) return 'Pattern library — Routine Watch'
    if (openResident !== null) return `${residentName(openResident)} — Routine Watch`
    return 'Unit overview — Routine Watch'
  }

  return (
    <>
      <a href="#main" className="skip-link">Skip to main content</a>
      <main id="main" className="app app--with-dock">
        {showTour && (
          <Suspense fallback={<Loading label="Loading tour…" />}>
            <Tour />
          </Suspense>
        )}
        <DemoBanner />
        <header className="app-topbar">
          <div className="app-topbar__brand">
            <h1 className="app-topbar__name">Routine Watch</h1>
            <span className="app-topbar__unit">
              {residents.length} resident{residents.length === 1 ? '' : 's'}
            </span>
          </div>
          <Pill tone={residentsSource === 'demo' ? 'watch' : 'positive'} className="app-topbar__status">
            {residentsSource === 'demo' ? 'Offline — demo data' : 'Live'}
          </Pill>
        </header>

        {openAlert !== null ? (
          <AlertView alertId={openAlert} onBack={closeAlert} />
        ) : openHandoff ? (
          <Suspense fallback={<Loading label="Loading shift handoff…" />}>
            <Handoff
              onBack={() => setOpenHandoff(false)}
              onOpenAlert={id => openAlertFrom('handoff', id)}
            />
          </Suspense>
        ) : openPatternLibrary ? (
          <Suspense fallback={<Loading label="Loading pattern library…" />}>
            <PatternLibrary onBack={() => setOpenPatternLibrary(false)} />
          </Suspense>
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

        <nav className="app-dock" aria-label="Main screens">
          {MAIN_SCREENS.map(({ id, label }) => (
            <button
              key={id}
              type="button"
              className="app-dock__item"
              aria-current={currentScreen === id ? 'page' : undefined}
              onClick={() => goToScreen(id)}
            >
              {label}
            </button>
          ))}
        </nav>
      </main>
    </>
  )
}
