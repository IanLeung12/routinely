import { lazy, Suspense, useEffect, useState } from 'react'
import { fetchAlerts } from './alert/api.ts'
import { AlertView } from './alert/AlertView.tsx'
import { LiveScreen } from './live/LiveScreen.tsx'
import { fetchResidents } from './overview/api.ts'
import { UnitOverview } from './overview/UnitOverview.tsx'
import { getRole, peopleISupport, resetPeople, setRole as saveRole } from './people/api.ts'
import { MyRoutine } from './people/MyRoutine.tsx'
import { PeopleISupport } from './people/PeopleISupport.tsx'
import { RoleChooser } from './people/RoleChooser.tsx'
import { RoleSwitch } from './people/RoleSwitch.tsx'
import type { RoleId } from './people/types.ts'
import { ResidentDetail } from './resident/ResidentDetail.tsx'
import { Button } from './ui/Button.tsx'
import { DemoBanner, resetDemoData } from './ui/DemoBanner.tsx'
import { Loading } from './ui/Loading.tsx'
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

/** What the app is, in the words of whoever is reading it (SPEC section 17). "Nurse"
 * belongs to the care-home case only, so the shared line never says it. */
const TAGLINE: Record<RoleId, string> = {
  person:
    'Watches an everyday routine, like making a cup of tea, and tells you when something looked different from your usual.',
  supervisor:
    'Watches someone make a cup of tea and flags a change in their routine for you to review.',
}

export default function App() {
  /** `?tour=1` opts into the presenter cue card; off by default so it never touches
   * the real demo path. */
  const showTour = new URLSearchParams(window.location.search).has('tour')
  /** `?invite=CODE` is the link a person sends whoever they want watching over them:
   * the code arrives filled in on "People I support" (SPEC section 17). */
  const inviteCode = new URLSearchParams(window.location.search).get('invite')
  /** Person or supervisor, remembered between visits; null until the chooser is answered. */
  const [role, setRoleState] = useState<RoleId | null>(() => getRole())
  /** The people this supervisor can see. One of them and their detail is the home
   * screen; several and it is the unit overview (SPEC section 17). */
  const [supported, setSupported] = useState(() => peopleISupport())
  /** Set once the one supported person's detail has been left, so Back lands on the
   * list rather than reopening the detail it just came from. */
  const [showingPeople, setShowingPeople] = useState(false)
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
    if (role !== 'supervisor') return
    let cancelled = false
    fetchAlerts().then(result => {
      if (!cancelled) setAlerts(result)
    })
    return () => { cancelled = true }
  }, [refreshKey, role])

  useEffect(() => {
    if (role !== 'supervisor') return
    let cancelled = false
    fetchResidents().then(result => {
      if (!cancelled) setResidents(result)
    })
    return () => { cancelled = true }
  }, [refreshKey, role])

  function residentName(id: string): string {
    return (
      residents.find(resident => resident.id === id)?.name ??
      supported.find(person => person.id === id)?.name ??
      id
    )
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

  /** Answers the role chooser, or switches role later from the shell: the home screen
   * changes, and anything opened under the old role is closed. */
  function chooseRole(next: RoleId) {
    saveRole(next)
    setRoleState(next)
    setSupported(peopleISupport())
    setShowingPeople(false)
    setOpenResident(null)
    setOpenAlert(null)
    setOpenHandoff(false)
    setOpenPatternLibrary(false)
  }

  /** Re-reads who I support after a link is added or removed. */
  function refreshPeople() {
    setSupported(peopleISupport())
  }

  /** "Reset demo" forgets the role and the links as well as the pipeline's demo state,
   * so the next open starts at the chooser with the seeded people (SPEC section 17). */
  async function resetDemo() {
    resetPeople()
    setRoleState(null)
    setSupported(peopleISupport())
    setShowingPeople(false)
    await resetDemoData()
  }

  /** The supervisor who supports exactly one person opens straight into their detail:
   * a daughter watching her father has no unit to look at first (SPEC section 17). */
  const soleSupported = supported.length === 1 ? supported[0] : null
  const shownResident =
    openResident ?? (showingPeople ? null : (soleSupported?.id ?? null))

  /** Back from the detail: the overview when it was opened from a list, otherwise the
   * people list, which is the only other screen a one-person supervisor has. */
  function closeResident() {
    if (openResident !== null) {
      setOpenResident(null)
      return
    }
    setShowingPeople(true)
  }

  useDocumentTitle(documentTitle())

  /** So someone with several tabs open (or a screen reader) can tell the overview from
   * Mrs. K's alert. */
  function documentTitle(): string {
    if (role === null) return 'Routine Watch'
    if (role === 'person') return 'My routine — Routine Watch'
    if (openAlert !== null) {
      const resident = alerts.find(alert => alert.alert_id === openAlert)?.resident_id
      const name = resident ? residentName(resident) : null
      return name ? `Alert · ${name} — Routine Watch` : 'Alert — Routine Watch'
    }
    if (openHandoff) return 'Shift handoff — Routine Watch'
    if (openPatternLibrary) return 'Pattern library — Routine Watch'
    if (shownResident !== null) return `${residentName(shownResident)} — Routine Watch`
    if (supported.length > 1) return 'Unit overview — Routine Watch'
    return 'People I support — Routine Watch'
  }

  /** The supervisor's home: the unit overview with its live session and alerts when
   * there are several people, and "people I support" either way (SPEC section 17). */
  const supervisorHome = (
    <>
      {supported.length > 1 && (
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
      )}

      <section>
        <h2>People I support</h2>
        <PeopleISupport
          people={supported}
          initialCode={inviteCode}
          onOpen={setOpenResident}
          onChange={refreshPeople}
        />
      </section>
    </>
  )

  return (
    <>
      <a href="#main" className="skip-link">Skip to main content</a>
      <main id="main" className="app">
        {showTour && (
          <Suspense fallback={<Loading label="Loading tour…" />}>
            <Tour />
          </Suspense>
        )}
        <DemoBanner onReset={resetDemo} />
        <header>
          <h1>Routine Watch</h1>
          <p className="tagline">
            {role === null
              ? 'Watches an everyday routine, like making a cup of tea, and flags a change for review.'
              : TAGLINE[role]}
          </p>
          {role !== null && <RoleSwitch role={role} onChange={chooseRole} />}
          {role === 'supervisor' && !openHandoff && !openPatternLibrary && (
            <>
              {supported.length > 1 && (
                <Button onClick={() => setOpenHandoff(true)}>Shift handoff</Button>
              )}
              <Button variant="secondary" onClick={() => setOpenPatternLibrary(true)}>
                Pattern library
              </Button>
            </>
          )}
        </header>

        {role === null ? (
          <RoleChooser onChoose={chooseRole} />
        ) : role === 'person' ? (
          <MyRoutine onChange={refreshPeople} />
        ) : openAlert !== null ? (
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
        ) : shownResident !== null ? (
          <ResidentDetail
            residentId={shownResident}
            onBack={closeResident}
            backLabel={supported.length > 1 ? 'Unit overview' : 'People I support'}
          />
        ) : (
          supervisorHome
        )}
      </main>
    </>
  )
}
