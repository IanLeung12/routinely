/** The four screens in SPEC section 9. Each one is a later task. */
const screens = [
  { name: 'Unit overview', detail: 'Residents, status chip, error-score sparkline' },
  { name: 'Resident detail', detail: 'Baseline chart, heat calendar, sessions, context' },
  { name: 'Live session', detail: 'Skeleton view beside the task-graph map' },
  { name: 'Alert evidence', detail: 'Summary, error list, ghost replay, suggested checks' },
]

export default function App() {
  return (
    <main className="app">
      <header>
        <h1>Routine Watch</h1>
        <p className="tagline">
          Watches a resident make a cup of tea and flags a change in their routine for a
          nurse to review.
        </p>
      </header>

      <ul className="screens">
        {screens.map((screen) => (
          <li key={screen.name}>
            <h2>{screen.name}</h2>
            <p>{screen.detail}</p>
            <span className="todo">not built yet</span>
          </li>
        ))}
      </ul>
    </main>
  )
}
