import type { Handoff } from './types.ts'

/** The 12-hour handoff the pipeline serves once the demo's live session has been
 * played (SPEC section 10 beat 4), so the screen still has something to show when the
 * API is unreachable - the same state `mock/alerts.ts` assumes. Kept next to the
 * screen the way `live/mockLiveStream.ts` is. Mrs. K has two sessions above her own
 * baseline and an alert nobody has reviewed; Mr. Chen and Mr. Nguyen are on a slow
 * rise; the rest of the unit has nothing to review. Nobody was flagged the shift
 * before this one, the same `previous_flags` the pipeline serves for this window
 * (T324), so Mrs. K's row reads as two more than last shift offline too. */
export const mockHandoff: Handoff = {
  window_hours: 12,
  residents: [
    { resident_id: 'mrs-k', name: 'Mrs. K', room: '204', flags: 2, previous_flags: 0, pending_review: 1, trending: false },
    { resident_id: 'mr-chen', name: 'Mr. Chen', room: '211', flags: 0, previous_flags: 0, pending_review: 0, trending: true },
    { resident_id: 'mr-nguyen', name: 'Mr. Nguyen', room: '126', flags: 0, previous_flags: 0, pending_review: 0, trending: true },
    { resident_id: 'mr-silva', name: 'Mr. Silva', room: '117', flags: 0, previous_flags: 0, pending_review: 0, trending: false },
    { resident_id: 'mrs-ahmed', name: 'Mrs. Ahmed', room: '108', flags: 0, previous_flags: 0, pending_review: 0, trending: false },
    { resident_id: 'mrs-patel', name: 'Mrs. Patel', room: '132', flags: 0, previous_flags: 0, pending_review: 0, trending: false },
  ],
  paused: [],
  summary:
    'Flagged for review: 2 errors this session (skipped the task at 0:00, repeated the task at 0:10) '
    + 'vs 0.56 normally over 14 days. Context: last 12 h, 6 residents; Mrs. K: 2 sessions above '
    + 'baseline, 1 alert pending review; Mr. Chen: error score trending up; Mr. Nguyen: error score '
    + 'trending up; 3 residents with nothing to review.',
}
