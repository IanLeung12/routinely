import { lazy, Suspense, useEffect, useState } from 'react'
import './App.css'
import { fetchAlerts } from './alert/api.ts'
import { LiveScreen } from './live/LiveScreen.tsx'
import { fetchResidentsWithSource, type ResidentsSource } from './overview/api.ts'
import { UnitOverview } from './overview/UnitOverview.tsx'
import { currentPerson, currentSupervisor, getRole, peopleISupport, resetPeople, setRole as saveRole } from './people/api.ts'
import { MyRoutine } from './people/MyRoutine.tsx'
import { PeopleISupport } from './people/PeopleISupport.tsx'
import { RoleChooser } from './people/RoleChooser.tsx'
import { RoleSwitch } from './people/RoleSwitch.tsx'
import type { RoleId } from './people/types.ts'
import { Button } from './ui/Button.tsx'
import { DemoBanner, resetDemoData } from './ui/DemoBanner.tsx'
import { Loading } from './ui/Loading.tsx'
import { Pill } from './ui/Pill.tsx'
import { useDocumentTitle } from './ui/useDocumentTitle.ts'

/** Off the main demo path (SPEC demo beat is overview → live → alert), so these
 * screens load on demand instead of growing the first-paint bundle. */
const Handoff = lazy(() => import('./handoff/Handoff.tsx').then(m => ({ default: m.Handoff })))
const PatternLibrary = lazy(() =>
  import('./patterns/PatternLibrary.tsx').then(m => ({ default: m.PatternLibrary })),
)
const RoutinesScreen = lazy(() =>
  import('./routines/RoutinesScreen.tsx').then(m => ({ default: m.RoutinesScreen })),
)
const Replays = lazy(() => import('./replays/Replays.tsx').then(m => ({ default: m.Replays })))
const Tour = lazy(() => import('./tour/Tour.tsx').then(m => ({ default: m.Tour })))
const AlarmBanner = lazy(() => import('./checkin/AlarmBanner.tsx').then(m => ({ default: m.AlarmBanner })))
const SafetySettings = lazy(() => import('./checkin/SafetySettings.tsx').then(m => ({ default: m.SafetySettings })))

/** On the demo path but one tap in, never at first paint: the alert screen (with the
 * replay player) and a resident's detail (with its charts and calendar) are the two
 * biggest eager chunks, and the first-load budget had to be raised four times in two
 * days to fit them (`scripts/check-bundle.mjs`, T449). Both are drill-ins from the
 * overview, so the shell can load without them and fetch them on the tap that opens
 * them. Each Suspense fallback reuses the screen's own loading label, so the text
 * doesn't change when the chunk lands and the screen starts fetching. */
const AlertView = lazy(() => import('./alert/AlertView.tsx').then(m => ({ default: m.AlertView })))
const ResidentDetail = lazy(() =>
  import('./resident/ResidentDetail.tsx').then(m => ({ default: m.ResidentDetail })),
)

/** Where an alert was opened from, so its Back button can return there instead of
 * always landing on the overview. */
type AlertOrigin = 'overview' | 'handoff' | 'live' | 'myRoutine'

/** The app shell's three top-level destinations, for the floating nav dock. A
 * resident's detail or an open alert are drill-ins reached from the overview, so
 * they still count as 'overview' for which dock item is current. Supervisor-only:
 * a person has just the one "My routine" screen, and the role chooser has none. */
type MainScreen = 'overview' | 'handoff' | 'patterns'

const MAIN_SCREENS: { id: MainScreen; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'handoff', label: 'Shift handoff' },
  { id: 'patterns', label: 'Pattern library' },
]

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
  /** "New routine" (T438): building or saving one sits off the main demo path, behind
   * one button in the top bar that both roles get. */
  const [openRoutines, setOpenRoutines] = useState(false)
  const [safetyPerson, setSafetyPerson] = useState<string | null>(null)
  /** The replays library (SPEC section 17): whose it is, and which session (if any)
   * it should open straight into, e.g. from an alert's error rows. */
  const [openReplays, setOpenReplays] = useState<{ personId: string; sessionId: string | null } | null>(null)
  const [alerts, setAlerts] = useState<Awaited<ReturnType<typeof fetchAlerts>>>([])
  const [residents, setResidents] = useState<Awaited<ReturnType<typeof fetchResidentsWithSource>>['residents']>([])
  /** Whether the last residents fetch reached the real API or fell back to demo
   * data, for the top bar's compact offline indicator. */
  const [residentsSource, setResidentsSource] = useState<ResidentsSource>('api')
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
    fetchResidentsWithSource().then(result => {
      if (!cancelled) {
        setResidents(result.residents)
        setResidentsSource(result.source)
      }
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

  /** Opens the replays library for one person, straight into a session when one is
   * given (an alert's error rows name the session the error happened in). */
  function openReplaysFor(personId: string, sessionId: string | null = null) {
    setSafetyPerson(null)
    setOpenReplays({ personId, sessionId })
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
    setOpenRoutines(false)
    setSafetyPerson(null)
    setOpenReplays(null)
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
  /** Who the top bar's "Replays" button opens, if anyone: the person themselves, or
   * the resident a supervisor has open (SPEC section 17's entry points). */
  const replaysPersonId = role === 'person' ? currentPerson().id : role === 'supervisor' ? shownResident : null

  /** Back from the detail: the overview when it was opened from a list, otherwise the
   * people list, which is the only other screen a one-person supervisor has. */
  function closeResident() {
    if (openResident !== null) {
      setOpenResident(null)
      return
    }
    setShowingPeople(true)
  }

  /** The dock's current screen: a resident's detail, an open alert or the people
   * list are drill-ins reached from the overview, so they don't get their own
   * dock item. */
  const currentScreen: MainScreen = openHandoff ? 'handoff' : openPatternLibrary ? 'patterns' : 'overview'

  /** Jumps straight to one of the three main screens, closing whatever drill-in
   * (a resident's detail, an open alert, the people list) was on top of it. */
  function goToScreen(screen: MainScreen) {
    setOpenResident(null)
    setOpenAlert(null)
    setShowingPeople(false)
    setOpenHandoff(screen === 'handoff')
    setOpenPatternLibrary(screen === 'patterns')
    setOpenRoutines(false)
    setSafetyPerson(null)
    setOpenReplays(null)
  }

  useDocumentTitle(documentTitle())

  /** So someone with several tabs open (or a screen reader) can tell the overview from
   * Mrs. K's alert. */
  function documentTitle(): string {
    if (role === null) return 'Routine Watch'
    if (safetyPerson !== null) return 'Safety settings — Routine Watch'
    if (openReplays !== null) return 'Replays — Routine Watch'
    if (openAlert !== null) {
      const resident = alerts.find(alert => alert.alert_id === openAlert)?.resident_id
      const name = resident ? residentName(resident) : null
      return name ? `Alert · ${name} — Routine Watch` : 'Alert — Routine Watch'
    }
    if (role === 'person') return 'My routine — Routine Watch'
    if (openRoutines) return 'Routines — Routine Watch'
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
            <UnitOverview
              onSelect={setOpenResident}
              refreshKey={refreshKey}
              personIds={supported.map((person) => person.id)}
            />
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
      <main id="main" className={role === 'supervisor' ? 'app app--with-dock' : 'app'}>
        {showTour && (
          <Suspense fallback={<Loading label="Loading tour…" />}>
            <Tour />
          </Suspense>
        )}
        <DemoBanner onReset={resetDemo} />
        <header className="app-topbar">
          <div className="app-topbar__brand">
            <h1 className="app-topbar__name">Routine Watch</h1>
            <p className="app-topbar__tagline">
              {role === null
                ? 'Watches an everyday routine, like making a cup of tea, and flags a change for review.'
                : TAGLINE[role]}
            </p>
          </div>
          <div className="app-topbar__actions">
            {role === 'supervisor' && (
              <>
                <span className="app-topbar__unit">
                  {residents.length} resident{residents.length === 1 ? '' : 's'}
                </span>
                <Pill tone={residentsSource === 'demo' ? 'watch' : 'positive'} className="app-topbar__status">
                  {residentsSource === 'demo' ? 'Offline — demo data' : 'Live'}
                </Pill>
              </>
            )}
            {role !== null && (
              <Button onClick={() => { setSafetyPerson(null); setOpenRoutines(true) }}>New routine</Button>
            )}
            {role !== null && (role === 'person' || supported.length > 0) && (
              <Button onClick={() => setSafetyPerson(role === 'person' ? currentPerson().id : shownResident ?? supported[0].id)}>Safety settings</Button>
            )}
            {replaysPersonId !== null && (
              <Button onClick={() => openReplaysFor(replaysPersonId)}>Replays</Button>
            )}
            {role !== null && <RoleSwitch role={role} onChange={chooseRole} />}
          </div>
        </header>

        {role === 'supervisor' && (
          <Suspense fallback={<Loading label="Loading safety alarms…" />}>
            <AlarmBanner people={supported} supporter={currentSupervisor().id} />
          </Suspense>
        )}

        {role === null ? (
          <RoleChooser onChoose={chooseRole} />
        ) : safetyPerson !== null ? (
          <Suspense fallback={<Loading label="Loading safety settings…" />}>
            {role === 'supervisor' && supported.length > 1 && (
              <label>Safety settings for
                <select value={safetyPerson} onChange={event => setSafetyPerson(event.target.value)}>
                  {supported.map(person => <option key={person.id} value={person.id}>{person.name}</option>)}
                </select>
              </label>
            )}
            <SafetySettings key={safetyPerson} personId={safetyPerson} onBack={() => setSafetyPerson(null)} />
          </Suspense>
        ) : openReplays !== null ? (
          <Suspense fallback={<Loading label="Loading replays…" />}>
            <Replays
              personId={openReplays.personId}
              role={role}
              initialSessionId={openReplays.sessionId}
              onBack={() => setOpenReplays(null)}
            />
          </Suspense>
        ) : openRoutines ? (
          <Suspense fallback={<Loading label="Loading routines…" />}>
            <RoutinesScreen onBack={() => setOpenRoutines(false)} />
          </Suspense>
        ) : openAlert !== null ? (
          <Suspense fallback={<Loading label="Loading alert…" />}>
            <AlertView
              alertId={openAlert}
              onBack={closeAlert}
              onOpenEvidence={(error) => {
                const resident = alerts.find((alert) => alert.alert_id === openAlert)?.resident_id
                if (resident) openReplaysFor(resident, error.session_id)
              }}
            />
          </Suspense>
        ) : role === 'person' ? (
          <MyRoutine onChange={refreshPeople} onOpenAlert={id => openAlertFrom('myRoutine', id)} />
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
          <Suspense fallback={<Loading label="Loading their routine…" />}>
            <ResidentDetail
              residentId={shownResident}
              onBack={closeResident}
              backLabel={supported.length > 1 ? 'Unit overview' : 'People I support'}
            />
          </Suspense>
        ) : (
          supervisorHome
        )}

        {role === 'supervisor' && (
          <nav className="app-dock" aria-label="Main screens">
            {MAIN_SCREENS.filter(({ id }) => id !== 'handoff' || supported.length > 1).map(({ id, label }) => (
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
        )}
      </main>
    </>
  )
}
