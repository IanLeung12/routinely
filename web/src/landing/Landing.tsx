import './landing.css'

/** The public one-pager behind the demo URL: what Routine Watch is, why it matters,
 * how it works, and a way into the dashboard. Separate Vite entry (`web/landing.html`),
 * so nothing here can break the nurse's screens. Copy stays plain and under ~350
 * words; the wording rules of SPEC §7.5 apply to it like everywhere else. */

/** The pipeline as a strip, one line per stage (SPEC §6). */
const FLOW = [
  { label: 'Camera', body: 'A webcam looks down on the kitchenette.' },
  { label: 'Skeleton only', body: 'Pose points and object boxes; the frame is dropped.' },
  { label: 'Task graph', body: 'Steps checked against the order the task needs.' },
  { label: 'Personal baseline', body: 'Measured against her own two weeks, not an average.' },
  { label: 'Patterns', body: 'Rules rank what the change is consistent with.' },
  { label: 'Nurse', body: 'One flag with its evidence, on the shift dashboard.' },
]

/** Three of the patterns in the library (SPEC §7.5), as examples of the wording. */
const PATTERNS = [
  {
    name: 'Sudden change',
    signals: 'Errors up across types within one to three days.',
    reading: 'Consistent with delirium — rule out infection, dehydration or a new medication, and run a CAM.',
    timing: 'same shift',
  },
  {
    name: 'Slow drift',
    signals: 'Errors and hesitation rising over weeks.',
    reading: 'Consistent with cognitive decline — consider a reassessment.',
    timing: 'routine review',
  },
  {
    name: 'Evening worsening',
    signals: 'Late-day sessions only, mornings normal.',
    reading: 'Consistent with sundowning — check sleep, lighting, pain, evening medication.',
    timing: 'routine review',
  },
]

const PRIVACY = [
  'No video is stored: each frame is dropped once it is processed.',
  'Skeleton points, object boxes and timestamps only. No face recognition.',
  'Monitoring switches off per room, and every pause is logged.',
]

const STACK = [
  { name: 'Gemini', body: 'checks ambiguous moments.' },
  { name: 'Tiger Data', body: 'holds sessions, baselines and drift.' },
  { name: 'Vultr', body: 'runs the pipeline and dashboard.' },
  { name: 'Claude', body: 'writes each summary from the detected evidence only.' },
  { name: 'Roboflow', body: 'trained the object detector.' },
]

export function Landing() {
  return (
    <>
      <main className="landing" id="main">
        <header className="landing__hero">
          <h1 className="landing__title">Routine Watch</h1>
          <p className="landing__lead">
            A privacy-preserving camera system that watches care-home residents do everyday
            tasks — making tea, getting dressed — and flags a change for review when how they do
            them moves away from their own normal.
          </p>
          <p className="landing__actions">
            <a className="btn btn--primary" href="/">
              Open the dashboard
            </a>
            <a className="btn btn--secondary" href="#how-it-works">
              Watch the demo
            </a>
          </p>
        </header>

        <section className="landing-section" aria-labelledby="why">
          <h2 className="landing-section__title" id="why">
            Why it matters
          </h2>
          <ul className="landing-list">
            <li>Delirium is sudden confusion: common in long-term care, dangerous, easy to miss.</li>
            <li>
              Often it is the first visible sign of an infection, dehydration or a drug reaction;
              a day's warning can prevent an ER trip.
            </li>
            <li>
              Nobody can watch every resident do every task, and screens like the CAM happen
              occasionally, not continuously.
            </li>
          </ul>
        </section>

        <section className="landing-section" aria-labelledby="how-it-works">
          <h2 className="landing-section__title" id="how-it-works">
            How it works
          </h2>
          <ol className="landing-flow">
            {FLOW.map((stage, index) => (
              <li className="landing-flow__stage card" key={stage.label}>
                <span className="landing-flow__number" aria-hidden="true">
                  {index + 1}
                </span>
                <strong className="landing-flow__label">{stage.label}</strong>
                <span className="landing-flow__body">{stage.body}</span>
              </li>
            ))}
          </ol>
          <p className="landing-section__note">
            It runs on synthetic residents plus one live session on stage.{' '}
            <a href="/?tour=1">Take the guided tour.</a>
          </p>
        </section>

        <section className="landing-section" aria-labelledby="patterns">
          <h2 className="landing-section__title" id="patterns">
            Consistent with, never a conclusion
          </h2>
          <p className="landing-section__note">
            A flag says something changed. The pattern scorer says what kind, so a nurse knows
            what to rule out first. It is not a medical assessment.
          </p>
          <ul className="landing-patterns">
            {PATTERNS.map((pattern) => (
              <li className="landing-patterns__item card" key={pattern.name}>
                <h3 className="landing-patterns__name">{pattern.name}</h3>
                <p className="landing-patterns__signals">{pattern.signals}</p>
                <p className="landing-patterns__reading">{pattern.reading}</p>
                <p className="landing-patterns__timing">Act: {pattern.timing}</p>
              </li>
            ))}
          </ul>
        </section>

        <section className="landing-section" aria-labelledby="privacy">
          <h2 className="landing-section__title" id="privacy">
            Privacy by design
          </h2>
          <ul className="landing-list">
            {PRIVACY.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </section>

        <section className="landing-section" aria-labelledby="built-with">
          <h2 className="landing-section__title" id="built-with">
            Built with
          </h2>
          <ul className="landing-list landing-list--stack">
            {STACK.map((tool) => (
              <li key={tool.name}>
                <strong>{tool.name}</strong> {tool.body}
              </li>
            ))}
          </ul>
        </section>
      </main>

      <footer className="landing-footer">
        <p className="landing-footer__line">
          Built at Hack the Valley 11.{' '}
          {/* Placeholder until the repository is public. */}
          <a href="https://github.com/IanLeung12/htv-2026">Source on GitHub</a>
        </p>
      </footer>
    </>
  )
}

export default Landing
