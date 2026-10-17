import type { Handoff } from './types.ts'

/** The 12-hour handoff the pipeline serves for the seeded demo residents, so the
 * screen still has something to show when the API is unreachable. Kept next to the
 * screen the way `live/mockLiveStream.ts` is, and mirrors `build_handoff(DEMO_NOW, 12)`:
 * Mrs. K flagged with an alert nobody has reviewed, Mr. Chen and Mr. Nguyen on a slow
 * rise, everyone else unchanged. */
export const mockHandoff: Handoff = {
  window_hours: 12,
  residents: [
    { resident_id: 'mrs-k', name: 'Mrs. K', flags: 1, pending_review: 1, trending: false },
    { resident_id: 'mr-chen', name: 'Mr. Chen', flags: 0, pending_review: 0, trending: true },
    { resident_id: 'mr-nguyen', name: 'Mr. Nguyen', flags: 0, pending_review: 0, trending: true },
    { resident_id: 'mr-silva', name: 'Mr. Silva', flags: 0, pending_review: 0, trending: false },
    { resident_id: 'mrs-ahmed', name: 'Mrs. Ahmed', flags: 0, pending_review: 0, trending: false },
    { resident_id: 'mrs-patel', name: 'Mrs. Patel', flags: 0, pending_review: 0, trending: false },
  ],
  summary:
    'Flagged for review: 2 errors this session (skipped the task at 0:00, repeated the task at 0:10) '
    + 'vs 0.58 normally over 14 days. Context: last 12 h, 6 residents; Mrs. K: 1 session flagged for '
    + 'review, 1 alert pending review; Mr. Chen: error score trending up; Mr. Nguyen: error score '
    + 'trending up; 3 residents with no change flagged for review.',
}
