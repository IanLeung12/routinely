import { Pill } from '../ui/Pill'

/** More, fewer or the same, and the word that says which. Colour is the second
 * signal only: `label` carries the whole meaning, so the indicator reads the same in
 * greyscale, read aloud or pasted into a note. */
type Comparison = {
  tone: 'negative' | 'positive' | 'neutral'
  direction?: 'up' | 'down'
  label: string
}

/** This window's flag count against the one before it, in words.
 *
 * Counts only (SPEC section 7.5): it says how many more or fewer sessions were
 * flagged for review, never why and never what it means for the resident. The
 * sessions counted are the row's own - the chip beside it names them - so the
 * difference and the count are read together. */
function compare(flags: number, previousFlags: number): Comparison {
  if (flags > previousFlags) {
    return { tone: 'negative', direction: 'up', label: `${flags - previousFlags} more than last shift` }
  }
  if (flags < previousFlags) {
    return { tone: 'positive', direction: 'down', label: `${previousFlags - flags} fewer than last shift` }
  }
  // Equal. A quiet shift after a quiet shift is worth saying in its own words: "same
  // as last shift" beside a row with nothing flagged reads as "same amount of
  // something" rather than "nothing either time".
  if (flags === 0) {
    return { tone: 'neutral', label: 'Nothing flagged either shift' }
  }
  return { tone: 'neutral', label: 'Same as last shift' }
}

/** The same phrase the chip shows, in plain text, for a handoff that leaves the
 * screen: the copied and read-aloud line `Handoff.tsx` builds. Null when the payload
 * sent no comparison, so a trimmed `/handoff` leaves the line as it was rather than
 * claiming "same" (T292, T311). One source for the wording, so a row and the note
 * pasted from it can never say different things. */
export function handoffDeltaLabel(flags: number, previousFlags?: number | null): string | null {
  if (previousFlags === null || previousFlags === undefined) return null
  return compare(flags, previousFlags).label
}

/** Is this resident's shift better or worse than the last one? (SPEC section 9.)
 *
 * A nurse coming on shift reads a handoff row's counts and has no way to tell a
 * resident who is settling from one who is getting worse: two flagged sessions is
 * good news after four and bad news after none. This is that one line, from
 * `HandoffResident.flags` and `previous_flags` (`pipeline/src/routine_watch/`
 * `handoff.py`, which counts the window before this one against the same resident's
 * same bar).
 *
 * Nothing is rendered when `previousFlags` is absent: `previous_flags` is optional on
 * the payload, and an older or trimmed `/handoff` sent no comparison at all, which is
 * not the same as no change (T292, T311).
 *
 * The words say "last shift" because the handoff's window is a shift by default
 * (`Handoff.tsx`'s `DEFAULT_WINDOW_H`). A nurse can widen that window on the screen,
 * so whoever wires this into a row decides what to call a longer one.
 */
export function HandoffDelta({
  flags,
  previousFlags,
}: {
  flags: number
  previousFlags?: number | null
}) {
  if (previousFlags === null || previousFlags === undefined) return null

  const { tone, direction, label } = compare(flags, previousFlags)
  return (
    <Pill className="handoff-delta" tone={tone} direction={direction}>
      <span className="handoff-delta__label">{label}</span>
    </Pill>
  )
}

export default HandoffDelta
