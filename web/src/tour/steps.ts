/** Copy for the guided demo tour (SPEC section 10): one card per demo beat. */
export interface TourStep {
  title: string
  body: string
}

export const TOUR_STEPS: TourStep[] = [
  {
    title: 'Routine Watch',
    body: 'Changes in how someone manages everyday tasks are often the first sign something changed — delirium from an infection, a medication issue, a decline. This tour walks through how the dashboard flags a change for review.',
  },
  {
    title: 'Baseline',
    body: "The overview shows each person's normal routine over the last two weeks, so you can see what's typical for them before anything changes.",
  },
  {
    title: 'Live session',
    body: 'While someone makes tea, the task map updates in real time, highlighting steps that are missing, out of order, or slower than usual.',
  },
  {
    title: 'Alert',
    body: "When at least two sessions within 48 hours cross a person's own threshold, an alert appears here and on your phone. A single off session never alerts on its own.",
  },
  {
    title: 'Why',
    body: "Open an alert to see exactly what changed: the errors with timestamps, a ghost replay against their normal, and the pattern it's consistent with, plus what to rule out first.",
  },
  {
    title: 'Not just delirium',
    body: 'The same kind of signal can point to different patterns. A slow drift over weeks is flagged for routine review, not an urgent call — the dashboard shows which is which.',
  },
  {
    title: 'Privacy and feedback',
    body: "No video is ever stored, only skeletons, boxes, and timestamps. Feedback on each alert tunes that person's threshold going forward.",
  },
]
