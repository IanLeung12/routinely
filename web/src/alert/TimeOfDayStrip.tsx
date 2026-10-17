import type { CSSProperties } from 'react'
import { TIME_OF_DAY_VALUES } from '../contracts.ts'
import type { TimeOfDay, TimeOfDayErrors } from '../contracts.ts'
import './TimeOfDayStrip.css'

/** The window the API reads the strip over (`api_alerts.TIME_OF_DAY_DAYS`), named in
 * the caption so the numbers are never read as "ever" or "today". */
const WINDOW_DAYS = 14

const BUCKET_LABELS: Record<TimeOfDay, string> = {
  morning: 'Morning',
  afternoon: 'Afternoon',
  evening: 'Evening',
}

/** The hours each part of the day covers (`api_alerts.AFTERNOON_START_HOUR` and
 * `EVENING_START_HOUR`), so "evening" is a time rather than a feeling. */
const BUCKET_HOURS: Record<TimeOfDay, string> = {
  morning: 'before 12:00',
  afternoon: '12:00–17:00',
  evening: 'from 17:00',
}

function plural(count: number, word: string): string {
  return `${count} ${count === 1 ? word : `${word}s`}`
}

/** Errors per part of the day, for the three parts in a fixed order: the payload's
 * own buckets, with a part of the day it does not mention counted as no sessions
 * rather than dropped, so the strip is always the shape of a whole day. */
function orderedBuckets(buckets: TimeOfDayErrors[]): TimeOfDayErrors[] {
  const byBucket = new Map(buckets.map((bucket) => [bucket.bucket, bucket]))
  return TIME_OF_DAY_VALUES.map(
    (bucket) => byBucket.get(bucket) ?? { bucket, sessions: 0, errors: 0 },
  )
}

/** The evidence behind an evening-only worsening (SPEC section 7.5), under the error
 * list on the alert screen: how many errors this resident's morning, afternoon and
 * evening sessions had over the last two weeks, as a bar per part of the day plus the
 * numbers in words - the bar is errors per session, so a part of the day she makes tea
 * in less often is not quietly flattered by a short bar.
 *
 * Hidden when the API sends no strip: a resident with no sessions in the window has no
 * daily shape to show, and three empty bars would read as three good parts of a day. */
export function TimeOfDayStrip({ buckets }: { buckets?: TimeOfDayErrors[] | null }) {
  if (!buckets || buckets.length === 0) return null

  const ordered = orderedBuckets(buckets)
  const rates = ordered.map(({ sessions, errors }) => (sessions > 0 ? errors / sessions : 0))
  const worst = Math.max(...rates)

  return (
    <figure className="time-of-day">
      <figcaption className="time-of-day__caption">
        Errors by time of day, last {WINDOW_DAYS} days
      </figcaption>
      <ul className="time-of-day__list" aria-label="Errors by time of day">
        {ordered.map((bucket, index) => {
          const rate = rates[index]
          const share = worst > 0 ? rate / worst : 0
          return (
            <li
              key={bucket.bucket}
              className="time-of-day__bucket"
              aria-label={`${BUCKET_LABELS[bucket.bucket]}: ${plural(bucket.errors, 'error')}, ${plural(bucket.sessions, 'session')}`}
            >
              <span className="time-of-day__label">
                {BUCKET_LABELS[bucket.bucket]}{' '}
                <span className="time-of-day__hours">{BUCKET_HOURS[bucket.bucket]}</span>
              </span>
              <span className="time-of-day__track" aria-hidden="true">
                <span
                  className="time-of-day__fill"
                  style={{ '--share': share } as CSSProperties}
                />
              </span>
              {/* The leading space keeps the row one readable sentence - "Morning
                  before 12:00 0.1 per session" - however it is read out or copied,
                  rather than two cells run together by the grid that lays them out. */}
              {bucket.sessions === 0 ? (
                <span className="time-of-day__count">{' '}No sessions</span>
              ) : (
                <span className="time-of-day__count">
                  {' '}
                  <strong className="time-of-day__rate">{rate.toFixed(1)} per session</strong>{' '}
                  ({plural(bucket.errors, 'error')} in {plural(bucket.sessions, 'session')})
                </span>
              )}
            </li>
          )
        })}
      </ul>
    </figure>
  )
}

export default TimeOfDayStrip
