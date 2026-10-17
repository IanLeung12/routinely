import type { FeedbackVerdict } from '../contracts.ts'
import { Card } from '../ui/Card.tsx'
import { EmptyState } from '../ui/EmptyState.tsx'
import { ErrorState } from '../ui/ErrorState.tsx'
import { Loading } from '../ui/Loading.tsx'
import { formatDayTime } from './format.ts'
import type { FeedbackAnswer, ResidentFeedback } from './types.ts'
import './feedbackHistory.css'

const TITLE = 'What nurses said'

/** How many answers sit on the card: the recent ones a nurse coming on shift needs,
 * not the whole log. */
const SHOWN = 5

const VERDICT_LABEL: Record<FeedbackVerdict, string> = {
  confirmed: 'Confirmed',
  false_alarm: 'False alarm',
}

/** What a nurse picks when the change was something the pattern library has no
 * pattern for (`api_alerts.OTHER_CAUSE`). */
const OTHER_CAUSE = 'other'

/** What the card is showing: its data is fetched on its own, so a feedback the API
 * can't serve leaves the rest of the resident's screen alone. */
export type FeedbackState =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'ok'; feedback: ResidentFeedback }

function patternName(patternId: string, names: Record<string, string>): string {
  return names[patternId] ?? patternId
}

/** The middle of a row: what the nurse said it was.
 *
 * Only a confirmed answer gets one. A cause on a dismissed alert isn't evidence the
 * pattern matched, and the ranking doesn't count it either
 * (`routine_watch.feedback.cause_counts`), so the card doesn't claim it did. */
function causeClause(answer: FeedbackAnswer, names: Record<string, string>): string | null {
  if (answer.verdict !== 'confirmed' || answer.cause === null) {
    return null
  }
  if (answer.cause === OTHER_CAUSE) {
    return 'another cause'
  }
  return `consistent with ${patternName(answer.cause, names)}`
}

/** The pattern a weight moved furthest, and which way: what the answers above changed
 * about this resident's ranking. Everything the library knows sits at 1.0 until her
 * nurses answer, so only a weight off 1.0 is worth a line. */
function ranked(weights: Record<string, number>, direction: 'up' | 'down'): string | null {
  const entries = Object.entries(weights).filter(([, weight]) =>
    direction === 'up' ? weight > 1 : weight < 1,
  )
  if (entries.length === 0) {
    return null
  }
  return entries.reduce((best, entry) =>
    (direction === 'up' ? entry[1] > best[1] : entry[1] < best[1]) ? entry : best,
  )[0]
}

/** Past nurse answers and the pattern ranking they changed (SPEC Nice to have 8).
 *
 * The feedback loop re-weights a resident's patterns from her own nurses' answers;
 * without this it does it silently. Always what a change was "consistent with", never
 * a verdict on the resident. */
export function FeedbackHistory({ state }: { state: FeedbackState }) {
  let body
  if (state.status === 'loading') {
    body = <Loading label="Loading nurse answers…" />
  } else if (state.status === 'error') {
    body = <ErrorState message="Couldn't load feedback" />
  } else if (state.feedback.answers.length === 0) {
    body = <EmptyState message="No nurse answers yet" />
  } else {
    const { answers, pattern_weights: weights, pattern_names: names } = state.feedback
    const favoured = ranked(weights, 'up')
    const lowered = ranked(weights, 'down')
    body = (
      <>
        <ul className="feedback-history__list">
          {answers.slice(0, SHOWN).map((answer) => {
            const detail = [causeClause(answer, names), formatDayTime(answer.at)]
              .filter(Boolean)
              .join(' · ')
            return (
              <li className="feedback-history__answer" key={answer.alert_id}>
                <span
                  className={`feedback-history__verdict feedback-history__verdict--${
                    answer.verdict === 'confirmed' ? 'confirmed' : 'false-alarm'
                  }`}
                >
                  {VERDICT_LABEL[answer.verdict] ?? answer.verdict}
                </span>
                {` · ${detail}`}
              </li>
            )
          })}
        </ul>
        {favoured !== null && (
          <p className="feedback-history__ranking">
            Ranking now favours: {patternName(favoured, names)}
          </p>
        )}
        {lowered !== null && (
          <p className="feedback-history__ranking feedback-history__ranking--lower">
            Ranked lower: {patternName(lowered, names)}
          </p>
        )}
      </>
    )
  }

  return (
    <Card>
      <section className="feedback-history" aria-label={TITLE}>
        <h3>{TITLE}</h3>
        {body}
      </section>
    </Card>
  )
}

export default FeedbackHistory
