import { useState } from 'react'
import { UnitOverview } from './overview/UnitOverview.tsx'
import { ResidentDetail } from './resident/ResidentDetail.tsx'

/** Screens 3-4 of SPEC section 9. Each one is a later task. */
const screens = [
  { name: 'Live session', detail: 'Skeleton view beside the task-graph map' },
  { name: 'Alert evidence', detail: 'Summary, error list, ghost replay, suggested checks' },
]

export default function App() {
  /** Which resident's detail is open, if any. Two screens don't need a router. */
  const [openResident, setOpenResident] = useState<string | null>(null)

  return (
    <main className="app">
      <header>
        <h1>Routine Watch</h1>
        <p className="tagline">
          Watches a resident make a cup of tea and flags a change in their routine for a
          nurse to review.
        </p>
      </header>

      {openResident === null ? (
        <>
          <section>
            <h2>Unit overview</h2>
            <UnitOverview onSelect={setOpenResident} />
          </section>

          <ul className="screens">
            {screens.map((screen) => (
              <li key={screen.name}>
                <h2>{screen.name}</h2>
                <p>{screen.detail}</p>
                <span className="todo">not built yet</span>
              </li>
            ))}
          </ul>
        </>
      ) : (
        <ResidentDetail residentId={openResident} onBack={() => setOpenResident(null)} />
      )}
    </main>
  )
}
