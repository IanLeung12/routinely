import { Card } from '../ui/Card.tsx'
import { Pill } from '../ui/Pill.tsx'
import type { PillTone } from '../ui/Pill.tsx'
import { Row } from '../ui/Row.tsx'
import { StatusChip } from '../ui/StatusChip.tsx'
import { LineChart } from '../ui/charts/LineChart.tsx'
import {
  formatDay,
  formatScore,
  HERO_BASELINE,
  HERO_BASELINE_DAYS,
  HERO_FLAG_THRESHOLD,
  HERO_FLAGGED_COUNT,
  HERO_READINGS,
} from './heroChart.ts'
import './landing.css'

/** The public one-pager behind the demo URL: what Routine Watch is, why it matters,
 * how it works, and a way into the dashboard. Separate Vite entry (`web/landing.html`),
 * so nothing here can break the dashboard screens. Copy stays plain and under ~350
 * words; the wording rules of SPEC §7.5 apply to it like everywhere else.
 *
 * On the design system in `docs/DESIGN.md` since T407: the page is the dark instrument
 * panel the dashboard is, the hero carries one real chart from the chart kit instead of
 * a picture of one, and every section is a hairline card of dense rows. */

/** The number under the hero chart: what the chart is measured against, what it found,
 * and what the pipeline kept (SPEC §8). Numbers first, the words under them. */
const HERO_STATS = [
  { value: String(HERO_BASELINE_DAYS), unit: 'days', label: 'Her own baseline' },
  { value: String(HERO_FLAGGED_COUNT), unit: 'sessions', label: 'Above her usual range' },
  { value: '0', unit: 'frames', label: 'Video kept' },
]

/** The pipeline as a strip, one line per stage (SPEC §6). */
const FLOW = [
  { label: 'Camera', body: 'A webcam looks down on the kitchenette.' },
  { label: 'Skeleton only', body: 'Pose points and object boxes; the frame is dropped.' },
  { label: 'Task graph', body: 'Steps checked against the order the task needs.' },
  { label: 'Personal baseline', body: 'Measured against her own two weeks, not an average.' },
  { label: 'Patterns', body: 'Rules rank what the change is consistent with.' },
  { label: 'Your dashboard', body: 'One flag with its evidence, for whoever is watching.' },
]

/** Three of the patterns in the library (SPEC §7.5), as examples of the wording.
 * `tone` follows the alert screen's urgency chips: amber this shift, grey routine. */
const PATTERNS: {
  name: string
  signals: string
  reading: string
  timing: string
  tone: PillTone
}[] = [
  {
    name: 'Sudden change',
    signals: 'Errors up across types within one to three days.',
    reading: 'Consistent with delirium — rule out infection, dehydration or a new medication, and run a CAM.',
    timing: 'same shift',
    tone: 'watch',
  },
  {
    name: 'Slow drift',
    signals: 'Errors and hesitation rising over weeks.',
    reading: 'Consistent with cognitive decline — consider a reassessment.',
    timing: 'routine review',
    tone: 'neutral',
  },
  {
    name: 'Evening worsening',
    signals: 'Late-day sessions only, mornings normal.',
    reading: 'Consistent with sundowning — check sleep, lighting, pain, evening medication.',
    timing: 'routine review',
    tone: 'neutral',
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

const WHY = [
  'Delirium is sudden confusion: common in long-term care, dangerous, easy to miss.',
  "Often it is the first visible sign of an infection, dehydration or a drug reaction; a day's warning can prevent an ER trip.",
  'Nobody can sit and watch every task, and screens like the CAM happen occasionally, not continuously.',
]

/** The hero visual: the demo resident's own fortnight, her usual range behind it, and
 * the latest reading tagged on the line (docs/DESIGN.md, "Charts"). The card's title is
 * not a heading, so the page's outline stays h1 then one h2 per section. */
function HeroChart() {
  return (
    <Card className="landing-chart">
      <div className="landing-chart__header">
        <p className="landing-chart__title">Mrs. K · room 204</p>
        <StatusChip status="flagged" />
        <span className="landing-chart__caption">Error score per tea session, demo data</span>
      </div>
      <p className="landing-chart__headline">
        Two sessions above her own usual range, on the same day.
      </p>
      <LineChart
        label="Mrs. K's tea sessions scored against her own usual range"
        summary="Her fortnight of tea sessions, drawn against the usual range built from her own earlier ones."
        data={HERO_READINGS}
        baseline={HERO_BASELINE}
        flagThreshold={HERO_FLAG_THRESHOLD}
        formatValue={formatScore}
        formatTime={formatDay}
      />
      <dl className="landing-chart__stats">
        {HERO_STATS.map((stat) => (
          <div className="landing-stat" key={stat.label}>
            <dt className="landing-stat__label">{stat.label}</dt>
            <dd className="landing-stat__value">
              <span className="landing-stat__number tabular-nums">{stat.value}</span>
              <span className="landing-stat__unit">{stat.unit}</span>
            </dd>
          </div>
        ))}
      </dl>
    </Card>
  )
}

export function Landing() {
  return (
    <>
      <main className="landing" id="main">
        <header className="landing__hero">
          <h1 className="landing__title">Routine Watch</h1>
          <p className="landing__lead">
            A privacy-preserving camera system that watches everyday tasks — making tea,
            getting dressed — and flags a change for review when how someone does them moves
            away from their own normal.
          </p>
          <p className="landing__audience">
            For anyone who wants it: on your own, or with family, a carer or a care home.
          </p>
          <p className="landing__actions">
            <a className="btn btn--primary" href="/">
              Open the dashboard
            </a>
            <a className="btn btn--secondary" href="#how-it-works">
              Watch the demo
            </a>
          </p>
          <HeroChart />
        </header>

        <section className="landing-section" aria-labelledby="why">
          <h2 className="landing-section__title" id="why">
            Why it matters
          </h2>
          <Card flush>
            <ul className="landing-notes">
              {WHY.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </Card>
        </section>

        <section className="landing-section" aria-labelledby="how-it-works">
          <h2 className="landing-section__title" id="how-it-works">
            How it works
          </h2>
          <Card flush className="landing-flow-card">
            <ol className="landing-flow">
              {FLOW.map((stage, index) => (
                <li className="landing-flow__stage" key={stage.label}>
                  <span className="landing-flow__number tabular-nums" aria-hidden="true">
                    {String(index + 1).padStart(2, '0')}
                  </span>
                  <strong className="landing-flow__label">{stage.label}</strong>
                  <span className="landing-flow__body">{stage.body}</span>
                </li>
              ))}
            </ol>
          </Card>
          <p className="landing-section__note">
            It runs on synthetic data plus one live session on stage.{' '}
            <a href="/?tour=1">Take the guided tour.</a>
          </p>
        </section>

        <section className="landing-section" aria-labelledby="patterns">
          <h2 className="landing-section__title" id="patterns">
            Consistent with, never a conclusion
          </h2>
          <p className="landing-section__note">
            A flag says something changed. The pattern scorer says what kind, so you know what
            to rule out first. It is not a medical assessment.
          </p>
          <ul className="landing-patterns">
            {PATTERNS.map((pattern) => (
              <li key={pattern.name}>
                <Card className="landing-pattern">
                  <h3 className="landing-pattern__name">{pattern.name}</h3>
                  <p className="landing-pattern__signals">{pattern.signals}</p>
                  <p className="landing-pattern__reading">{pattern.reading}</p>
                  <p className="landing-pattern__timing">
                    <Pill tone={pattern.tone}>Act: {pattern.timing}</Pill>
                  </p>
                </Card>
              </li>
            ))}
          </ul>
        </section>

        <section className="landing-section" aria-labelledby="privacy">
          <h2 className="landing-section__title" id="privacy">
            Privacy by design
          </h2>
          <Card flush>
            <ul className="landing-notes">
              {PRIVACY.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </Card>
        </section>

        <section className="landing-section" aria-labelledby="built-with">
          <h2 className="landing-section__title" id="built-with">
            Built with
          </h2>
          <Card flush>
            <ul className="landing-stack">
              {STACK.map((tool) => (
                <li key={tool.name}>
                  <Row title={tool.name} value={tool.body} />
                </li>
              ))}
            </ul>
          </Card>
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
